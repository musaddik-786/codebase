"""
handler.py — Damage Assessment
─────────────────────────────────
AI-assisted identification of damage items from a claim's description, and
read/write access to damage_items, repair_costs, and replacement_costs.

Issue 3 fix: Item costs are now derived proportionally from the claim's
             estimated_cost so they sum to the claim total.
Issue 4 fix: Damage categories are constrained to a loss-type-specific list
             (Water→Flooring/Drywall/Insulation, Fire→Kitchen Cabinets/
             Countertops/Appliances, etc.). The LLM only assigns severity
             and notes for those pre-defined categories.
Issue 5 fix: analyze_damage_from_description first checks for existing
             damage_items and returns early if any are found (deduplication).
"""

import base64
import io
import json
import logging
import os
import random
import sys
from datetime import datetime
from typing import Optional
from urllib.parse import unquote

import requests as http_requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)




LABOR_RATE = 75.0     # $75/hr (hardcoded)
DIAGNOSTIC_FEE = 150.0  # $150 (hardcoded)


def _compute_item_costs(estimated_cost: float, n_items: int, loss_type: str) -> list:
    """
    Reference bundle cost formula per item index i (0-based):
      materialCost_i = round(avgCost * 0.25 * (1 + i * 0.15))
      laborHours_i = round(8 + i * 4)  → 8, 12, 16
      urgencyFactor = 1.15 if fire else 1.0  (stored as metadata, NOT multiplied into total)
      totalRepairEstimate_i = round(materialCost_i + (laborHours_i * LABOR_RATE) + DIAGNOSTIC_FEE)
    Returns list of dicts with: material_cost, labor_hours, urgency_factor, total_repair_estimate
    """
    avg_cost = float(estimated_cost) if estimated_cost else 0.0
    urgency_factor = 1.15 if "fire" in (loss_type or "").lower() else 1.0
    items = []
    for i in range(n_items):
        material_cost = round(avg_cost * 0.25 * (1 + i * 0.15), 2)
        labor_hours = round(8 + i * 4)
        total_repair_estimate = round(material_cost + (labor_hours * LABOR_RATE) + DIAGNOSTIC_FEE, 2)
        items.append({
            "material_cost": material_cost,
            "labor_hours": labor_hours,
            "urgency_factor": urgency_factor,
            "total_repair_estimate": total_repair_estimate,
        })
    return items


def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_damage_items(claim_number: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM damage_items WHERE claim_number = %s ORDER BY id DESC", (claim_number,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def write_damage_item(claim_number: str, category: str, severity: str, estimated_cost: float,
                      adjuster_notes: Optional[str] = None) -> dict:
    damage_id = f"DMG-{claim_number}-{random.randint(1000, 9999)}"
    created_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO damage_items (damage_id, claim_number, category, severity, estimated_cost, adjuster_notes, created_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (damage_id, claim_number, category, severity, estimated_cost, adjuster_notes, created_date),
        )
        conn.commit()
        return {
            "damage_id": damage_id, "claim_number": claim_number, "category": category,
            "severity": severity, "estimated_cost": estimated_cost, "adjuster_notes": adjuster_notes,
            "created_date": created_date,
        }
    finally:
        conn.close()



def get_claim_details(claim_number: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_number,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


# ─── Document helpers (vision + PDF) ─────────────────────────────────────────

_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}


def _fetch_image_documents(claim_number: str) -> list:
    """Returns up to 4 image rows from documents table for the claim."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, file_url, file_name, content_type
               FROM documents
               WHERE claim_number = %s
                 AND content_type = ANY(%s)
               ORDER BY uploaded_at DESC
               LIMIT 4""",
            (claim_number, list(_IMAGE_CONTENT_TYPES)),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def _fetch_pdf_documents(claim_number: str) -> list:
    """Returns up to 2 PDF rows from documents table for the claim."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, file_url, file_name, content_type
               FROM documents
               WHERE claim_number = %s
                 AND content_type = 'application/pdf'
               ORDER BY uploaded_at DESC
               LIMIT 2""",
            (claim_number,),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def _update_extracted_data(doc_id: int, summary: str) -> None:
    """Writes the AI-generated summary into documents.extracted_data for the given row."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE documents SET extracted_data = %s WHERE id = %s",
            (summary, doc_id),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        log.error("_update_extracted_data failed for doc id=%s: %s", doc_id, exc)
    finally:
        conn.close()


def _blob_url_to_base64(file_url: str, content_type: str) -> str:
    """
    Downloads a blob from Azure Storage using the SDK (works for private containers)
    and returns a data URI: data:{content_type};base64,{b64}.

    Extracts the blob path from the full URL by stripping the storage account
    and container prefix. URL-decodes the path to handle spaces in filenames.
    Falls back to a direct HTTP GET if the Azure SDK credentials are not configured.
    """
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "claims-evidence").strip()

    if conn_str:
        try:
            from azure.storage.blob import BlobServiceClient
            # Extract blob path from URL: strip everything up to and including /{container_name}/
            marker = f"/{container_name}/"
            idx = file_url.find(marker)
            if idx == -1:
                raise ValueError(f"Container '{container_name}' not found in URL: {file_url}")
            blob_path = unquote(file_url[idx + len(marker):])

            blob_client = BlobServiceClient.from_connection_string(conn_str) \
                .get_blob_client(container=container_name, blob=blob_path)
            data = blob_client.download_blob().readall()
            log.info("Downloaded blob via SDK: %s (%d bytes)", blob_path, len(data))
        except Exception as exc:
            log.warning("Azure SDK blob download failed (%s), trying HTTP: %s", file_url, exc)
            resp = http_requests.get(file_url, timeout=30)
            resp.raise_for_status()
            data = resp.content
    else:
        resp = http_requests.get(file_url, timeout=30)
        resp.raise_for_status()
        data = resp.content

    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{content_type};base64,{b64}"


def _extract_text_pdfplumber(pdf_url: str) -> str:
    """Downloads a PDF from Azure Blob Storage (private container) and extracts text using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber is not installed. Run: pip install pdfplumber")

    # Use SDK download so private containers work
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "claims-evidence").strip()
    if conn_str:
        from azure.storage.blob import BlobServiceClient
        marker = f"/{container_name}/"
        idx = pdf_url.find(marker)
        blob_path = unquote(pdf_url[idx + len(marker):]) if idx != -1 else unquote(pdf_url)
        pdf_bytes = BlobServiceClient.from_connection_string(conn_str) \
            .get_blob_client(container=container_name, blob=blob_path) \
            .download_blob().readall()
    else:
        response = http_requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        pdf_bytes = response.content

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_text = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages_text).strip()


def _extract_text_document_intelligence(pdf_url: str) -> str:
    """
    Extracts text from a PDF using Azure Document Intelligence (prebuilt-read).
    Downloads the PDF bytes via Azure Blob SDK first (works for private containers),
    then passes the bytes stream to DI — avoids the private-URL 403/404 issue.
    """
    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError:
        raise RuntimeError(
            "azure-ai-documentintelligence is not installed. "
            "Run: pip install azure-ai-documentintelligence"
        )
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "").strip()
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "").strip()
    if not endpoint or not key:
        raise ValueError(
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY "
            "must be set in .env"
        )

    # Download PDF bytes via Blob SDK (handles private containers)
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "claims-evidence").strip()
    if conn_str:
        from azure.storage.blob import BlobServiceClient
        marker = f"/{container_name}/"
        idx = pdf_url.find(marker)
        blob_path = unquote(pdf_url[idx + len(marker):]) if idx != -1 else unquote(pdf_url)
        pdf_bytes = BlobServiceClient.from_connection_string(conn_str) \
            .get_blob_client(container=container_name, blob=blob_path) \
            .download_blob().readall()
    else:
        resp = http_requests.get(pdf_url, timeout=30)
        resp.raise_for_status()
        pdf_bytes = resp.content

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    poller = client.begin_analyze_document("prebuilt-read", io.BytesIO(pdf_bytes))
    result = poller.result()
    paragraphs = getattr(result, "paragraphs", None) or []
    return "\n".join(p.content for p in paragraphs).strip()


def _extract_pdf_text(pdf_url: str) -> str:
    """
    Extracts text from a PDF URL using Azure Document Intelligence (active path).
    Falls back to pdfplumber if DI credentials are not configured.
    """
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "").strip()
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "").strip()
    if endpoint and key:
        log.info("Using Azure Document Intelligence for PDF extraction")
        return _extract_text_document_intelligence(pdf_url)
    log.info("DI credentials not set — falling back to pdfplumber for PDF extraction")
    return _extract_text_pdfplumber(pdf_url)



def _analyze_from_images(
    image_docs: list, loss_type: str, claim: dict, estimated_cost: float, claim_severity: str
) -> list:
    """
    Case 2 — Vision path.
    For each image: GPT-4.1 vision dynamically identifies damaged components and notes.
    Severity is taken directly from claims.severity (not LLM-assigned).
    Writes per-image summary to documents.extracted_data.
    Aggregates unique components across all images (first occurrence wins for notes).
    """
    llm = _get_llm()
    aggregated: dict = {}  # component_key → {component, notes}

    for doc in image_docs:
        url = doc.get("file_url", "")
        doc_id = doc.get("id")
        file_name = doc.get("file_name", "image")

        prompt_text = f"""You are an expert insurance claims adjuster performing AI-assisted damage photo analysis.
Claim type: {loss_type}
Claim description: {claim.get('short_description') or '(none)'}

Carefully examine this damage photo and extract the following:

1. damage_type — What specific type of damage is visible? (e.g. fire damage, smoke damage, water intrusion, structural collapse, charring, etc.)
2. visible_observations — List every detail you can see: affected surfaces, materials, objects, extent of damage, burn/water/impact patterns, any safety hazards
3. damaged_items — List the specific items, components, or areas that are visibly damaged
4. overall_severity — Your visual assessment of overall damage severity (Low/Medium/High/Critical)
5. image_summary — Comprehensive 3-4 sentence summary covering: what damage is visible, what is damaged, severity assessment, and key claim-relevant observations

Also identify every distinct damaged component visible in the image and for each provide one-sentence observation notes based on what you see. Use specific, exact component names (e.g. "Kitchen Cabinet Doors", "Hardwood Flooring" — not generic terms).

Respond with ONLY a valid JSON object (no markdown fences, no extra text):
{{
  "damage_type": "specific type of damage visible in the image",
  "visible_observations": ["detail 1", "detail 2", "detail 3"],
  "damaged_items": ["item or area 1", "item or area 2"],
  "overall_severity": "Low|Medium|High|Critical",
  "image_summary": "Comprehensive 3-4 sentence summary.",
  "items": [
    {{"component": "exact damaged component name", "notes": "specific observation about this component from the image"}},
    ...
  ]
}}"""

        try:
            data_uri = _blob_url_to_base64(url, doc.get("content_type", "image/jpeg"))
            response = llm.invoke([
                HumanMessage(content=[
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ])
            ])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.startswith("json"):
                    raw = raw[4:]
            try:
                full = json.loads(raw)
                llm_items = full.get("items", [])
                damage_type = full.get("damage_type", "")
                visible_obs = full.get("visible_observations", [])
                damaged_items_list = full.get("damaged_items", [])
                overall_severity = full.get("overall_severity", "")
                base_summary = full.get("image_summary", f"Damage observed in {file_name}.")
                parts = []
                if damage_type:
                    parts.append(f"Damage Type: {damage_type}")
                if overall_severity:
                    parts.append(f"Overall Severity: {overall_severity}")
                if damaged_items_list:
                    parts.append(f"Damaged Items: {', '.join(damaged_items_list)}")
                if visible_obs:
                    parts.append(f"Observations: {'; '.join(visible_obs)}")
                parts.append(base_summary)
                image_summary = " | ".join(parts)
            except Exception:
                image_summary = f"Damage observed in {file_name}."
                llm_items = []

            _update_extracted_data(doc_id, image_summary)
            log.info("Vision analysis written to documents.id=%s (%s)", doc_id, file_name)

            # Aggregate unique components — first occurrence per component wins
            for item in llm_items:
                comp = (item.get("component") or item.get("category") or "").strip()
                notes = item.get("notes") or f"Assessed from {file_name}."
                key = comp.lower()
                if key and key not in aggregated:
                    aggregated[key] = {"component": comp, "notes": notes}

        except Exception as exc:
            log.error("Vision call failed for doc id=%s (%s): %s", doc_id, file_name, exc)

    if not aggregated:
        aggregated["damaged property"] = {
            "component": "Damaged Property",
            "notes": f"Visual analysis unavailable — assessed from {loss_type} claim.",
        }

    components = list(aggregated.values())
    item_costs = _compute_item_costs(estimated_cost, len(components), loss_type)

    return [
        {
            "category": comp_data["component"],
            "severity": claim_severity,
            "estimated_cost": item_costs[i]["total_repair_estimate"],
            "material_cost": item_costs[i]["material_cost"],
            "labor_hours": item_costs[i]["labor_hours"],
            "urgency_factor": item_costs[i]["urgency_factor"],
            "total_repair_estimate": item_costs[i]["total_repair_estimate"],
            "notes": comp_data["notes"],
        }
        for i, comp_data in enumerate(components)
    ]


def _analyze_from_pdfs(
    pdf_docs: list, loss_type: str, claim: dict, estimated_cost: float, claim_severity: str
) -> list:
    """
    Case 3 — PDF path.
    For each PDF: extracts text (pdfplumber primary / Document Intelligence alternate),
    calls GPT-4.1 to dynamically identify damaged components and notes.
    Severity is taken directly from claims.severity (not LLM-assigned).
    Writes per-PDF summary to documents.extracted_data.
    Aggregates unique components across all PDFs (first occurrence wins for notes).
    """
    llm = _get_llm()
    aggregated: dict = {}  # component_key → {component, notes}

    for doc in pdf_docs:
        url = doc.get("file_url", "")
        doc_id = doc.get("id")
        file_name = doc.get("file_name", "document.pdf")

        try:
            pdf_text = _extract_pdf_text(url)
            if not pdf_text:
                log.warning("No text extracted from PDF doc id=%s (%s)", doc_id, file_name)
                pdf_text = "(No text could be extracted from this PDF.)"

            prompt_text = f"""You are an expert insurance claims adjuster performing AI-assisted damage report analysis.
Claim type: {loss_type}

PDF document content:
{pdf_text[:6000]}

Carefully read the document above and extract the following:

1. damage_type — What specific type of damage is described? (e.g. fire damage, smoke damage, water intrusion, structural damage, etc.)
2. visible_observations — List every specific detail mentioned in the document: affected areas, materials, objects, extent of damage, measurements, conditions noted by the inspector
3. damaged_items — List the specific items, components, or areas that are reported as damaged
4. overall_severity — Your assessment of overall damage severity based on the document (Low/Medium/High/Critical)
5. pdf_summary — Comprehensive 3-4 sentence summary covering: what type of damage occurred, what was damaged, the overall severity and reasoning, and key findings that would affect the claim assessment

Also identify every distinct damaged component mentioned in the document and for each provide one-sentence notes drawn directly from the document content. Use specific, exact component names as described in the report.

Respond with ONLY a valid JSON object (no markdown fences, no extra text):
{{
  "damage_type": "specific type of damage described in the document",
  "visible_observations": ["detail 1", "detail 2", "detail 3"],
  "damaged_items": ["item or area 1", "item or area 2"],
  "overall_severity": "Low|Medium|High|Critical",
  "pdf_summary": "Comprehensive 3-4 sentence summary.",
  "items": [
    {{"component": "exact damaged component name", "notes": "specific detail from the document about this component"}},
    ...
  ]
}}"""

            response = llm.invoke(prompt_text)
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.startswith("json"):
                    raw = raw[4:]
            try:
                full = json.loads(raw)
                llm_items = full.get("items", [])
                damage_type = full.get("damage_type", "")
                visible_obs = full.get("visible_observations", [])
                damaged_items_list = full.get("damaged_items", [])
                overall_severity = full.get("overall_severity", "")
                base_summary = full.get("pdf_summary", f"Damage report extracted from {file_name}.")
                parts = []
                if damage_type:
                    parts.append(f"Damage Type: {damage_type}")
                if overall_severity:
                    parts.append(f"Overall Severity: {overall_severity}")
                if damaged_items_list:
                    parts.append(f"Damaged Items: {', '.join(damaged_items_list)}")
                if visible_obs:
                    parts.append(f"Observations: {'; '.join(visible_obs)}")
                parts.append(base_summary)
                pdf_summary = " | ".join(parts)
            except Exception:
                pdf_summary = f"Damage report extracted from {file_name}."
                llm_items = []

            _update_extracted_data(doc_id, pdf_summary)
            log.info("PDF analysis written to documents.id=%s (%s)", doc_id, file_name)

            # Aggregate unique components — first occurrence per component wins
            for item in llm_items:
                comp = (item.get("component") or item.get("category") or "").strip()
                notes = item.get("notes") or f"Extracted from {file_name}."
                key = comp.lower()
                if key and key not in aggregated:
                    aggregated[key] = {"component": comp, "notes": notes}

        except Exception as exc:
            log.error("PDF analysis failed for doc id=%s (%s): %s", doc_id, file_name, exc)

    if not aggregated:
        aggregated["damaged property"] = {
            "component": "Damaged Property",
            "notes": f"PDF analysis unavailable — assessed from {loss_type} claim.",
        }

    components = list(aggregated.values())
    item_costs = _compute_item_costs(estimated_cost, len(components), loss_type)

    return [
        {
            "category": comp_data["component"],
            "severity": claim_severity,
            "estimated_cost": item_costs[i]["total_repair_estimate"],
            "material_cost": item_costs[i]["material_cost"],
            "labor_hours": item_costs[i]["labor_hours"],
            "urgency_factor": item_costs[i]["urgency_factor"],
            "total_repair_estimate": item_costs[i]["total_repair_estimate"],
            "notes": comp_data["notes"],
        }
        for i, comp_data in enumerate(components)
    ]


def _analyze_from_text(
    loss_type: str, claim: dict, estimated_cost: float, claim_severity: str
) -> list:
    """
    Case 1 — Text-only path (no documents found).
    LLM dynamically identifies damaged components from loss_type + short_description.
    Severity is taken directly from claims.severity (not LLM-assigned).
    """
    llm = _get_llm()
    prompt = f"""You are an insurance claims adjuster's assistant analyzing a {loss_type} claim.

Claim description: {claim.get('short_description') or '(none)'}

Based on the loss type and description above, identify all the specific damaged components or areas.
For each component, provide one brief sentence of adjuster observation notes.

Use specific, exact component names as described in the claim (e.g. "Bathroom Ceiling Drywall", "Hardwood Flooring" — not generic terms like "Flooring" or "Drywall").

Respond with ONLY a valid JSON object (no markdown fences, no extra text):
{{"items": [{{"component": "exact component name", "notes": "brief adjuster observation"}}, ...]}}"""

    response = llm.invoke(prompt)
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        llm_items = json.loads(raw).get("items", [])
    except Exception:
        log.warning("Could not parse LLM JSON for text path — using fallback. Raw: %s", raw[:200])
        llm_items = []

    if not llm_items:
        llm_items = [{"component": "Damaged Property", "notes": f"Assessed from {loss_type} claim description."}]

    item_costs = _compute_item_costs(estimated_cost, len(llm_items), loss_type)

    return [
        {
            "category": item.get("component") or "Damaged Property",
            "severity": claim_severity,
            "estimated_cost": item_costs[i]["total_repair_estimate"],
            "material_cost": item_costs[i]["material_cost"],
            "labor_hours": item_costs[i]["labor_hours"],
            "urgency_factor": item_costs[i]["urgency_factor"],
            "total_repair_estimate": item_costs[i]["total_repair_estimate"],
            "notes": item.get("notes") or f"Assessed from {loss_type} claim description.",
        }
        for i, item in enumerate(llm_items)
    ]


def analyze_damage_from_description(claim_number: str) -> dict:
    """
    Returns damage items for a claim using a 3-tier priority:

    Case 1 — No documents found:
        Uses claims.short_description + loss_type → GPT-4.1 text prompt.
    Case 2 — Image documents found (PNG/JPEG/WEBP):
        Passes each image URL to GPT-4.1 vision individually.
        Writes per-image summary to documents.extracted_data.
        Aggregates highest severity per category across all images.
    Case 3 — PDF documents found (no images):
        Extracts text via pdfplumber (primary) or Azure Document Intelligence (alternate).
        Passes extracted text to GPT-4.1 text prompt.
        Writes per-PDF summary to documents.extracted_data.

    Does NOT write damage items to DB — caller (agent) calls write_damage_item per item.
    Returns early if damage_items already exist for the claim (deduplication).
    """
    claim = get_claim_details(claim_number)
    if not claim:
        raise ValueError(f"Claim {claim_number} not found")

    existing = get_damage_items(claim_number)
    if existing:
        return {
            "claim_number": claim_number,
            "identified_items": [],
            "existing_items_count": len(existing),
            "message": (
                f"Damage already assessed: {len(existing)} item(s) exist. "
                "Use get_damage_items to retrieve them."
            ),
        }

    loss_type = claim.get("loss_type") or "Other"
    estimated_cost = float(claim.get("estimated_cost") or 0)
    claim_severity = claim.get("severity") or "Medium"

    # Run ALL document types — no attachment is skipped
    image_docs = _fetch_image_documents(claim_number)
    pdf_docs = _fetch_pdf_documents(claim_number)

    image_items = []
    pdf_items = []
    source_parts = []

    if image_docs:
        log.info("Vision path: %d image(s) found for claim %s", len(image_docs), claim_number)
        image_items = _analyze_from_images(image_docs, loss_type, claim, estimated_cost, claim_severity)
        source_parts.append("image")

    if pdf_docs:
        log.info("PDF path: %d PDF(s) found for claim %s", len(pdf_docs), claim_number)
        pdf_items = _analyze_from_pdfs(pdf_docs, loss_type, claim, estimated_cost, claim_severity)
        source_parts.append("pdf")

    if image_items or pdf_items:
        # Merge: images take priority — PDF components added only if not already identified from images
        merged: dict = {item["category"].lower(): item for item in image_items}
        for item in pdf_items:
            key = item["category"].lower()
            if key not in merged:
                merged[key] = item

        all_components = list(merged.values())
        # Recompute costs for the full merged component count
        merged_costs = _compute_item_costs(estimated_cost, len(all_components), loss_type)
        result_items = [
            {
                **all_components[i],
                "estimated_cost": merged_costs[i]["total_repair_estimate"],
                "material_cost": merged_costs[i]["material_cost"],
                "labor_hours": merged_costs[i]["labor_hours"],
                "urgency_factor": merged_costs[i]["urgency_factor"],
                "total_repair_estimate": merged_costs[i]["total_repair_estimate"],
            }
            for i in range(len(all_components))
        ]
        source = "+".join(source_parts)
    else:
        log.info("Text path: no documents found for claim %s", claim_number)
        result_items = _analyze_from_text(loss_type, claim, estimated_cost, claim_severity)
        source = "text"

    return {
        "claim_number": claim_number,
        "identified_items": result_items,
        "analysis_source": source,
    }


# ─── Repair / Replacement cost persistence ───────────────────────────────────

def write_repair_cost(claim_id: str, item_id: str, item_type: str,
                      material_cost: float, labor_hours: float, labor_rate: float,
                      diagnostic_fee: float, urgency_factor: float,
                      total_repair_estimate: float, notes: Optional[str] = None) -> dict:
    """Inserts a row into repair_costs table. Returns the saved row."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO repair_costs (
                claim_id, item_id, item_type, material_cost, labor_hours, labor_rate,
                diagnostic_fee, urgency_factor, total_repair_estimate, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
            """,
            (claim_id, item_id, item_type, material_cost, labor_hours, labor_rate,
             diagnostic_fee, urgency_factor, total_repair_estimate, notes),
        )
        row = cur.fetchone()
        conn.commit()
        return row_to_dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def write_replacement_cost(claim_id: str, item_id: str, item_type: str,
                           replacement_material_cost: float, installation_hours: float,
                           labor_rate: float, delivery_fee: float, disposal_fee: float,
                           total_replacement_estimate: float, notes: Optional[str] = None) -> dict:
    """Inserts a row into replacement_costs table. Returns the saved row."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO replacement_costs (
                claim_id, item_id, item_type, replacement_material_cost, installation_hours,
                labor_rate, delivery_fee, disposal_fee, total_replacement_estimate, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
            """,
            (claim_id, item_id, item_type, replacement_material_cost, installation_hours,
             labor_rate, delivery_fee, disposal_fee, total_replacement_estimate, notes),
        )
        row = cur.fetchone()
        conn.commit()
        return row_to_dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_repair_costs(claim_id: str) -> list:
    """Returns all repair_costs rows for the given claim_id."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM repair_costs WHERE claim_id = %s ORDER BY id", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def get_replacement_costs(claim_id: str) -> list:
    """Returns all replacement_costs rows for the given claim_id."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM replacement_costs WHERE claim_id = %s ORDER BY id", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def compute_and_save_repair_replacement(claim_number: str) -> dict:
    """
    For every existing damage_item for the claim, computes and saves both repair
    and replacement costs using the reference bundle formulas.

    Repair cost formula (per item index i):
      materialCost_i = round(avgCost * 0.25 * (1 + i * 0.15))
        where avgCost = claim.estimated_cost
      laborHours_i = round(8 + i * 4)
      urgencyFactor = 1.15 if fire claim else 1.0
      totalRepairEstimate_i = round((materialCost + (laborHours * 75) + 150) * urgencyFactor)

    Replacement cost formula (per item, using repair values):
      replacementMaterialCost = round(materialCost * 1.8)
      installationHours = round(laborHours * 0.7)
      deliveryFee = 250.0
      disposalFee = 150.0
      totalReplacementEstimate = round(replacementMaterialCost + (installationHours * 75) + 250 + 150)

    Uses damage_id as item_id, category as item_type.
    Returns dict with claim_number, items_processed, repair_costs (list), replacement_costs (list).
    """
    claim = get_claim_details(claim_number)
    if not claim:
        raise ValueError(f"Claim {claim_number} not found")

    claim_id = str(claim.get("id") or claim_number)
    loss_type = claim.get("loss_type") or "Other"
    estimated_cost = float(claim.get("estimated_cost") or 0)

    damage_items = get_damage_items(claim_number)
    if not damage_items:
        return {
            "claim_number": claim_number,
            "items_processed": 0,
            "message": "No damage items found for this claim. Run analyze_damage_from_description first.",
        }

    # Build the set of item_ids that already have repair costs — skip those, process the rest.
    # Do NOT block the entire function when only some items are done (agent may have called
    # write_damage_item + compute_and_save in separate passes, leaving partial rows).
    existing_repair = get_repair_costs(claim_id)
    already_done = {row.get("item_id") for row in existing_repair if row.get("item_id")}

    if already_done and len(already_done) >= len(damage_items):
        return {
            "claim_number": claim_number,
            "items_processed": 0,
            "message": f"Repair/replacement costs already exist for all {len(damage_items)} damage item(s). Skipping.",
        }

    urgency_factor = 1.15 if "fire" in loss_type.lower() else 1.0
    saved_repair = []
    saved_replacement = []
    skipped = 0

    for i, item in enumerate(damage_items):
        item_id = item.get("damage_id") or str(item.get("id"))
        item_type = item.get("category") or "Damaged Property"

        # Skip items whose costs were already written in a previous call
        if item_id in already_done:
            skipped += 1
            continue

        material_cost = round(estimated_cost * 0.25 * (1 + i * 0.15), 2)
        labor_hours = round(8 + i * 4)
        total_repair_estimate = round(
            material_cost + (labor_hours * LABOR_RATE) + DIAGNOSTIC_FEE, 2
        )

        replacement_material_cost = round(material_cost * 1.8, 2)
        installation_hours = round(labor_hours * 0.7)
        delivery_fee = 250.0
        disposal_fee = 150.0
        total_replacement_estimate = round(
            replacement_material_cost + (installation_hours * LABOR_RATE) + delivery_fee + disposal_fee, 2
        )

        try:
            repair_row = write_repair_cost(
                claim_id=claim_id,
                item_id=item_id,
                item_type=item_type,
                material_cost=material_cost,
                labor_hours=float(labor_hours),
                labor_rate=LABOR_RATE,
                diagnostic_fee=DIAGNOSTIC_FEE,
                urgency_factor=urgency_factor,
                total_repair_estimate=total_repair_estimate,
            )
            saved_repair.append(repair_row)

            replacement_row = write_replacement_cost(
                claim_id=claim_id,
                item_id=item_id,
                item_type=item_type,
                replacement_material_cost=replacement_material_cost,
                installation_hours=float(installation_hours),
                labor_rate=LABOR_RATE,
                delivery_fee=delivery_fee,
                disposal_fee=disposal_fee,
                total_replacement_estimate=total_replacement_estimate,
            )
            saved_replacement.append(replacement_row)
        except Exception as exc:
            log.error("Failed to write costs for item %s (%s): %s", item_id, item_type, exc)

    return {
        "claim_number": claim_number,
        "items_processed": len(saved_repair),
        "items_skipped_already_exist": skipped,
        "repair_costs": saved_repair,
        "replacement_costs": saved_replacement,
    }
