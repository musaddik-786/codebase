"""
voice_handler.py
─────────────────
Structured FNOL field extraction via Azure OpenAI chat.

Field Extraction:
  Uses Azure OpenAI (gpt-5.1) to extract structured FNOL fields from
  plain text (typed input or browser-transcribed voice).
"""

import json
import logging
import os

from dotenv import load_dotenv, find_dotenv
from openai import AzureOpenAI

load_dotenv(find_dotenv())

log = logging.getLogger(__name__)

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5.1")


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Structured Field Extraction via LLM
# ──────────────────────────────────────────────────────────────────────────────

_EXTRACTION_SYSTEM_PROMPT = """
You are an insurance claims intake specialist. Your task is to extract structured
First Notice of Loss (FNOL) information from the policyholder's text or voice transcript.

Extract the following fields (return null if not mentioned):
- loss_type       : Type of loss (e.g. "Water Damage", "Fire", "Wind/Hail", "Tree Damage", "Structural", "Theft", "Other")
- cause_of_loss   : Specific cause (e.g. "burst pipe", "electrical fault", "fallen tree")
- date_of_loss    : Date when loss occurred (ISO format YYYY-MM-DD if determinable)
- time_of_loss    : Time of loss (HH:MM 24h if determinable)
- area_affected   : Room or area affected (e.g. "kitchen", "roof", "living room")
- occupancy_at_loss : Whether home was occupied — true/false/null
- sudden_vs_gradual : "Sudden" or "Gradual" based on description
- emotional_context : Policyholder's emotional state (e.g. "distressed", "calm", "urgent")
- severity         : "Low", "Medium", "High", or "Critical"
- urgency_indicator: "routine", "urgent", "emergency"

For each field also provide:
- confidence (0-100): How confident you are in the extracted value
- source_snippet   : The exact text fragment that led to this value

Return ONLY valid JSON in this exact structure:
{
  "fields": {
    "<field_name>": {
      "value": <extracted value or null>,
      "confidence": <0-100>,
      "source_snippet": "<text fragment or null>"
    }
  },
  "overall_confidence": <0-100>,
  "missing_mandatory_fields": ["<field_name>", ...],
  "additional_notes": "<any other relevant observations>"
}
"""


def extract_fnol_fields(raw_text: str) -> dict:
    """
    Uses Azure OpenAI to extract structured FNOL fields from free text
    (either a browser-transcribed voice recording or typed input).

    Returns a dict with the structure described in _EXTRACTION_SYSTEM_PROMPT,
    including the LLM's self-reported overall_confidence as-is.
    """
    client = _get_openai_client()

    messages = [
        {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Policyholder input:\n\n{raw_text}"},
    ]

    response = client.chat.completions.create(
        model=AZURE_OPENAI_CHAT_DEPLOYMENT,
        messages=messages,
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        log.error("LLM returned non-JSON: %s", content)
        return {"error": "Failed to parse LLM response", "raw": content}

    return result
