# Jarvis Claims Agents — Interactive Test Guide

**47 agents · 4 persona MCP servers · Azure PostgreSQL backend**  
Tests run in lifecycle order. Each section builds on the data seeded by the previous one.  
All tests verified against `gpt-4.1-jarvis` on `agenticinsuranceopenai.openai.azure.com`.

---

## Table of Contents

1. [Pre-flight Checklist](#1-pre-flight-checklist)
2. [Test Data Reference](#2-test-data-reference)
3. [How to Read This Guide](#3-how-to-read-this-guide)
4. [Persona 1 — Policyholder (9 agents, ports 8801–8809)](#4-persona-1--policyholder-9-agents)
5. [Persona 2 — Claims Adjuster (15 agents, ports 8901–8915)](#5-persona-2--claims-adjuster-15-agents)
6. [Persona 3 — SIU Investigator (12 agents, ports 9001–9012)](#6-persona-3--siu-investigator-12-agents)
7. [Persona 4 — Vendor Manager (10 agents, ports 9101–9110)](#7-persona-4--vendor-manager-10-agents)
8. [Persona 5 — Orchestrator (1 agent, port 9201)](#8-persona-5--orchestrator-1-agent)
9. [Quick Smoke Test (15 min)](#9-quick-smoke-test-15-min)
10. [Health Check Reference](#10-health-check-reference)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Pre-flight Checklist

### 1.1 Single `.env` file (root of repo)

There is **one** `.env` at `Jarvis_claims_agents/.env`. All agents find it via `find_dotenv()`.  
Your current working credentials:

```env
AZURE_OPENAI_ENDPOINT="https://agenticinsuranceopenai.openai.azure.com/"
AZURE_OPENAI_API_KEY="<your key>"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4.1-jarvis"
AZURE_OPENAI_CHAT_DEPLOYMENT="gpt-4.1-jarvis"
AZURE_OPENAI_API_VERSION="2025-01-01-preview"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-3-large"

AZURE_WHISPER_ENDPOINT="https://azureclaimsopenai.openai.azure.com/openai/v1/realtime?model=gpt-realtime-whisper-claims"
AZURE_WHISPER_API_KEY="<your whisper key>"
AZURE_WHISPER_DEPLOYMENT="gpt-realtime-whisper-claims"

AZURE_PG_HOST="claimsagenticdb.postgres.database.azure.com"
AZURE_PG_PORT="5432"
AZURE_PG_DATABASE="postgres"
AZURE_PG_USER="PostgresAdmin"
AZURE_PG_PASSWORD="<your password>"
AZURE_PG_SSLMODE="require"

PHOENIX_ENDPOINT=
PHOENIX_API_KEY=
```

### 1.2 Start all four MCP servers

Open **4 terminals** (one per persona), `cd` into the persona folder, and run:

```powershell
# Terminal 1 — Policyholder MCP (port 8800)
cd PolicyholderAgents
py -3 MCP/main.py

# Terminal 2 — Adjuster MCP (port 8900)
cd AdjusterAgents
py -3 MCP/main.py

# Terminal 3 — SIU MCP (port 9000)
cd SIUAgents
py -3 MCP/main.py

# Terminal 4 — Vendor MCP (port 9100)
cd VendorManagerAgents
py -3 MCP/main.py
```

**Verify all four are up:**

```powershell
curl http://localhost:8800/health
curl http://localhost:8900/health
curl http://localhost:9000/health
curl http://localhost:9100/health
```

Each should return `{"status":"healthy", ...}`.

### 1.3 Initialize the database

Run once per persona (safe to re-run — all operations are idempotent):

```powershell
cd PolicyholderAgents;   py -3 MCP/common/init_db.py
cd AdjusterAgents;       py -3 MCP/common/init_db.py
cd SIUAgents;            py -3 MCP/common/init_db.py
cd VendorManagerAgents;  py -3 MCP/common/init_db.py
```

### 1.4 Start agent servers

Each agent has its own `server.py`. Start agents as needed for testing.  
Pattern: `cd <PersonaFolder> && py -3 <AgentFolder>/server.py`

### 1.5 Install dependencies (first time only)

```powershell
cd PolicyholderAgents;   pip install -r requirements.txt
cd AdjusterAgents;       pip install -r requirements.txt
cd SIUAgents;            pip install -r requirements.txt
cd VendorManagerAgents;  pip install -r requirements.txt
cd OrchestratorAgent;    pip install -r requirements.txt
```

---

## 2. Test Data Reference

These seed values are in the DB after `init_db.py` runs:

| Item | Value |
|---|---|
| Claim number | `CLM-2026-1001` |
| Policy number | `POL-1001` |
| Policyholder name | `John Doe` |
| Loss type | `Water Damage` |
| Cause | `Burst pipe in kitchen` |
| Date of loss | `2026-05-20` |
| Severity | `Medium` |
| Claim status | `Open` |
| Location | `123 Main St, Springfield` |
| Vendors seeded | `VEN-001` (Springfield Plumbing Pros), `VEN-002` (Apex Roofing Co) |

---

## 3. How to Read This Guide

Each agent section shows:

- **Start command** — how to launch the agent server
- **Test question** — the exact message to send
- **Expected tools called** — which MCP tools the agent should invoke (watch the SSE stream for `[Tool: xxx] Starting...` / `Done`)
- **Expected response** — what the agent should say
- **curl command** — paste directly into a terminal

```bash
# Generic curl pattern for all agents:
curl -s -N -X POST http://localhost:<PORT>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "<your message here>"}' \
  --max-time 120
```

---

## 4. Persona 1 — Policyholder (9 agents)

**MCP server:** port `8800`  
**Start all Policyholder agents:**
```powershell
cd PolicyholderAgents
foreach ($a in @("VoiceTextIntakeAgent","ClaimStatusAgent","ClaimReadinessAgent","PolicyCoverageVerificationAgent","DocumentSubmissionAgent","DuplicateClaimCheckAgent","ClaimSegmentationAgent","CommunicationAgent","FeedbackAgent")) {
    Start-Process -WindowStyle Hidden py "-3 $a/server.py"
    Start-Sleep 1
}
```

---

### P-1 · VoiceTextIntakeAgent · Port 8801

**Purpose:** Capture a First Notice of Loss (FNOL) from a policyholder via text or voice.

```powershell
cd PolicyholderAgents
py -3 VoiceTextIntakeAgent/server.py
```

**Test 1 — Start a new FNOL**
```bash
curl -s -N -X POST http://localhost:8801/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, my name is John Doe and my policy number is POL-1001. I want to file a claim. There was a burst pipe in my kitchen yesterday June 15th 2026 and I have flooding damage."}' \
  --max-time 120
```

| Expected tools called | What it confirms |
|---|---|
| `get_fnol_by_policy` | Checks for existing open FNOL |
| `create_fnol_submission` | Creates a new FNOL draft record |
| `get_mandatory_fields` | Loads the required field list |
| `extract_fnol_fields_from_text` | Extracts loss_type, cause, date, area from message |
| `update_fnol_submission` | Persists extracted fields to DB |
| `log_question_answer` (×4–5) | Logs each captured field |

**Expected response:** Agent confirms it captured Water Damage / burst pipe / June 15 / kitchen, then asks follow-up questions for missing fields: time of loss, occupancy at time, severity level, property address.

---

**Test 2 — Continue FNOL and answer follow-up questions**
```bash
curl -s -N -X POST http://localhost:8801/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "It happened around 7am. Yes the property was occupied. The damage looks moderate to severe — water is still on the floor. The address is 123 Main St, Springfield IL 62701."}' \
  --max-time 120
```

| Expected tools called | What it confirms |
|---|---|
| `update_fnol_submission` | Updates time_of_loss, occupancy, severity, address |
| `log_question_answer` (×4) | Logs each answer |
| `save_field_attribution` | Records source for each field |

**Expected response:** Agent summarises all captured details and asks the policyholder to confirm before submitting.

---

**Test 3 — Submit the FNOL**
```bash
curl -s -N -X POST http://localhost:8801/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Yes, everything looks correct. Please submit the claim."}' \
  --max-time 120
```

| Expected tools called | What it confirms |
|---|---|
| `submit_fnol` | Creates claim record in DB, returns claim_number |

**Expected response:** "Your claim has been submitted. Your claim number is CLM-2026-XXXX. You will be contacted by an adjuster within 2 business days."

---

### P-2 · ClaimStatusAgent · Port 8803 (actual: 8804)

**Purpose:** Report the current stage, sub-status, and SLA status of a claim.

```powershell
cd PolicyholderAgents
py -3 ClaimStatusAgent/server.py
```

**Test 1 — Check claim status**
```bash
curl -s -N -X POST http://localhost:8804/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current status of my claim CLM-2026-1001?"}' \
  --max-time 60
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_journey` | Fetches stage, sub_status, overall_sla_status |
| `get_claim_details` | Fetches claim metadata |

**Expected response:** "Your claim CLM-2026-1001 is in the **Claim Initiated** stage and is currently **Under Review**. The SLA status is **on track**. No delays have been reported."

---

**Test 2 — Ask for stage history**
```bash
curl -s -N -X POST http://localhost:8804/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Can you show me all the stages my claim CLM-2026-1001 has been through so far?"}' \
  --max-time 60
```

| Expected tools called | What it confirms |
|---|---|
| `get_stage_sla_tracking` | Returns stage timeline with entry/exit times |

**Expected response:** A stage-by-stage breakdown showing when the claim entered each stage and SLA compliance per stage.

---

### P-3 · ClaimReadinessAgent · Port 8802 (actual: 8808)

**Purpose:** Evaluate whether a claim has enough information for adjuster review.

```powershell
cd PolicyholderAgents
py -3 ClaimReadinessAgent/server.py
```

**Test 1 — Check readiness**
```bash
curl -s -N -X POST http://localhost:8808/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Is claim CLM-2026-1001 ready for adjuster review?"}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim data |
| `get_claim_documents` | Checks for uploaded documents |
| `get_intake_validation_result` | Checks completeness score |
| `get_stp_classification` | Checks STP (straight-through processing) score |

**Expected response:** Completeness score (e.g., 72%), list of missing items (e.g., "No supporting documents uploaded"), verdict: "Partially ready — recommend uploading photos of the damage before adjuster assignment."

---

**Test 2 — Ask what is missing**
```bash
curl -s -N -X POST http://localhost:8808/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What documents or information are still missing from claim CLM-2026-1001?"}' \
  --max-time 90
```

**Expected response:** Specific list of missing mandatory fields and recommended document types (photos, repair quotes, police report if applicable).

---

### P-4 · PolicyCoverageVerificationAgent · Port 8806 (actual: 8807)

**Purpose:** Verify that a policy is active and covers the reported loss type.

```powershell
cd PolicyholderAgents
py -3 PolicyCoverageVerificationAgent/server.py
```

**Test 1 — Verify coverage**
```bash
curl -s -N -X POST http://localhost:8807/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Verify that policy POL-1001 covers water damage from a burst pipe for claim CLM-2026-1001."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_policy_details` | Checks policy status, coverage_type, limits |
| `check_coverage` | Evaluates if loss type is covered |
| `get_claim_details` | Cross-references with claim data |

**Expected response:** "Policy POL-1001 is **Active** (Homeowners). Coverage limit: $250,000. Deductible: $1,000. Water damage from burst pipes is **covered** under this policy. Coverage is confirmed for claim CLM-2026-1001."

---

**Test 2 — Ask about deductible**
```bash
curl -s -N -X POST http://localhost:8807/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the deductible for claim CLM-2026-1001 and how does it affect my payout?"}' \
  --max-time 90
```

**Expected response:** Explains the $1,000 deductible will be subtracted from the settlement amount, and gives an example calculation if an estimate is available.

---

### P-5 · DocumentSubmissionAgent · Port 8805

**Purpose:** Accept document uploads (text content), classify them, extract insights, and attach to a claim.

```powershell
cd PolicyholderAgents
py -3 DocumentSubmissionAgent/server.py
```

**Test 1 — Submit a text document**
```bash
curl -s -N -X POST http://localhost:8805/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "For claim CLM-2026-1001: [File: plumber_estimate.txt] Estimate from Springfield Plumbing Pros dated June 16 2026. Work required: Replace 10 feet of copper supply pipe under kitchen sink. Labor: 4 hours at $95/hr = $380. Materials: copper pipe, fittings = $220. Total estimate: $600. Additional drywall repair needed: $350. Grand total: $950."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `classify_document` | Identifies doc type as "Repair Estimate" |
| `upload_document` | Saves to documents table |
| `extract_document_evidence` | Pulls cost figures, vendor name, date |

**Expected response:** "Document 'plumber_estimate.txt' has been classified as a **Repair Estimate** and attached to claim CLM-2026-1001. Extracted: vendor = Springfield Plumbing Pros, total = $950, date = 2026-06-16."

---

**Test 2 — Submit a photo description**
```bash
curl -s -N -X POST http://localhost:8805/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "For claim CLM-2026-1001: [File: damage_photo_description.txt] Photo taken June 15 2026 at 9am. Shows kitchen floor with standing water approximately 1 inch deep. Laminate flooring is visibly buckled and warped near the sink cabinet. Water staining visible on lower cabinet doors. Pipe visible under sink with crack at elbow joint."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `classify_document` | Identifies as "Photo / Visual Evidence" |
| `upload_document` | Saves with document_type = "Photo Evidence" |
| `extract_document_evidence` | Extracts damage description, affected area |

**Expected response:** Document classified as Photo Evidence, damage observations extracted and linked to claim.

---

### P-6 · DuplicateClaimCheckAgent · Port 8806

**Purpose:** Detect if a new FNOL duplicates an existing claim.

```powershell
cd PolicyholderAgents
py -3 DuplicateClaimCheckAgent/server.py
```

**Test 1 — Check for duplicates**
```bash
curl -s -N -X POST http://localhost:8806/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Check if there is already an existing claim for policy POL-1001 for water damage that occurred on 2026-05-20."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claims_by_policy` | Searches for claims under POL-1001 |
| `check_duplicate` | Compares date, loss type, location |

**Expected response:** "A potential duplicate was found: claim **CLM-2026-1001** for Water Damage on 2026-05-20 under policy POL-1001. This appears to be the same incident. No new claim was created."

---

**Test 2 — Check with different date (not a duplicate)**
```bash
curl -s -N -X POST http://localhost:8806/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Check for duplicate claims for policy POL-1001 for roof damage on 2026-03-10."}' \
  --max-time 90
```

**Expected response:** "No duplicate claim was found for roof damage on 2026-03-10 under policy POL-1001. It is safe to proceed with a new FNOL."

---

### P-7 · ClaimSegmentationAgent · Port 8809

**Purpose:** Segment claims by severity, complexity, and recommended processing path (STP vs manual).

```powershell
cd PolicyholderAgents
py -3 ClaimSegmentationAgent/server.py
```

**Test 1 — Segment a claim**
```bash
curl -s -N -X POST http://localhost:8809/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Segment claim CLM-2026-1001 and determine whether it qualifies for straight-through processing."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim severity, complexity, estimated_cost |
| `get_fraud_risk_snapshot` | Gets fraud score |
| `run_segmentation` | Runs STP scoring algorithm |
| `save_segmentation_result` | Writes to segmentation_result_output table |

**Expected response:** "Claim CLM-2026-1001 has been segmented as **Medium severity, Low complexity**. STP score: 72. Recommended path: **Express Review** (eligible for accelerated adjuster assignment). Estimated total: $8,500 which is within the auto-adjudication threshold."

---

**Test 2 — Ask about STP eligibility**
```bash
curl -s -N -X POST http://localhost:8809/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the STP score for claim CLM-2026-1001 and what does it mean?"}' \
  --max-time 60
```

**Expected response:** Explains what the STP score means and what processing path was recommended.

---

### P-8 · CommunicationAgent · Port 8808

**Purpose:** Handle inbound policyholder inquiries and log all communications.

```powershell
cd PolicyholderAgents
py -3 CommunicationAgent/server.py
```

**Test 1 — Policyholder inquiry**
```bash
curl -s -N -X POST http://localhost:8808/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "For claim CLM-2026-1001: I am really frustrated. It has been 3 days and I haven't heard anything from anyone. My kitchen is still flooded. What is going on with my claim?"}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim status |
| `get_communication_history` | Checks prior comms |
| `log_communication` | Saves this interaction |
| `update_sentiment_tracker` | Records frustrated/negative sentiment |

**Expected response:** Empathetic acknowledgement, status update for CLM-2026-1001, escalation flag raised if sentiment is critical, promise of callback or next step.

---

**Test 2 — Check communication history**
```bash
curl -s -N -X POST http://localhost:8808/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me all communications logged for claim CLM-2026-1001."}' \
  --max-time 60
```

| Expected tools called | What it confirms |
|---|---|
| `get_communication_history` | Returns all logged comms for the claim |

**Expected response:** List of logged communications with dates, types, and summaries.

---

### P-9 · FeedbackAgent · Port 8809

**Purpose:** Collect stage-by-stage policyholder feedback and track sentiment over time.

```powershell
cd PolicyholderAgents
py -3 FeedbackAgent/server.py
```

**Test 1 — Submit feedback**
```bash
curl -s -N -X POST http://localhost:8809/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "For claim CLM-2026-1001: I want to give feedback on the intake process. The agent was helpful and asked all the right questions. I feel confident my claim is in good hands. Rating: 4 out of 5."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `write_customer_feedback` | Saves feedback to customer_feedback_per_stage |
| `update_sentiment_tracker` | Updates sentiment to positive |
| `get_claim_sentiment` | Returns current sentiment snapshot |

**Expected response:** "Thank you for your feedback on claim CLM-2026-1001. Your positive rating has been recorded for the Claim Initiated stage. Your satisfaction score has been noted."

---

## 5. Persona 2 — Claims Adjuster (15 agents)

**MCP server:** port `8900`  
**Start all Adjuster agents:**
```powershell
cd AdjusterAgents
foreach ($a in @("TriageAgent","ClaimClassificationAgent","FraudScreeningAgent","DamageAssessmentAgent","EvidenceValidationAgent","ExternalDataAgent","LossAssessmentAgent","RepairVsReplacementAgent","ReserveRecommendationAgent","FinancialLeakageAgent","SettlementRecommendationAgent","PaymentEligibilityAgent","PaymentTriggerAgent","VerificationAgent","RoutingAgent")) {
    Start-Process -WindowStyle Hidden py "-3 $a/server.py"
    Start-Sleep 1
}
```

---

### A-1 · TriageAgent · Port 8901 (actual: 8902)

**Purpose:** Assess claim priority, SLA risk, and initial routing recommendation.

```powershell
cd AdjusterAgents
py -3 TriageAgent/server.py
```

**Test 1 — Run triage**
```bash
curl -s -N -X POST http://localhost:8902/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Run triage for claim CLM-2026-1001. The loss type is water damage from a burst pipe. Estimated cost is $8,500. Severity is Medium."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim data |
| `run_triage` | Computes priority score, SLA risk |
| `save_triage_result` | Saves to claim_triage table |
| `get_adjuster_workload` | Checks adjuster availability |

**Expected response:** "Claim CLM-2026-1001 has been triaged. Priority: **Medium**. SLA risk: **Low**. Estimated resolution: 5–7 business days. Recommended routing: Standard Adjuster. No immediate escalation required."

---

**Test 2 — Check existing triage result**
```bash
curl -s -N -X POST http://localhost:8902/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the triage result for claim CLM-2026-1001?"}' \
  --max-time 60
```

| Expected tools called | What it confirms |
|---|---|
| `get_triage_result` | Returns existing triage from DB |

**Expected response:** The triage result saved in the previous test.

---

### A-2 · ClaimClassificationAgent · Port 8902 (actual varies)

**Purpose:** Classify claim by type, subtype, and coverage category.

```powershell
cd AdjusterAgents
py -3 ClaimClassificationAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Classify claim CLM-2026-1001. Loss type is water damage from a burst pipe in the kitchen."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim |
| `classify_claim` | Assigns type: Plumbing / Water Damage / Property |
| `save_classification` | Writes classification to DB |

**Expected response:** "Claim CLM-2026-1001 classified as: **Type:** Property Damage · **Subtype:** Water Damage (Plumbing) · **Coverage Category:** Homeowners — Section I. AI confidence: 92%."

---

### A-3 · FraudScreeningAgent · Port 8903

**Purpose:** Run AI-assisted fraud indicator analysis on a claim.

```powershell
cd AdjusterAgents
py -3 FraudScreeningAgent/server.py
```

**Test 1 — Run fraud screening**
```bash
curl -s -N -X POST http://localhost:8903/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Run a fraud screening check on claim CLM-2026-1001."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim for LLM analysis |
| `run_fraud_screening` | LLM analyzes 0–3 indicators, writes signals |
| `get_fraud_flags` | Returns any active flags |
| `get_fraud_risk_snapshot` | Returns aggregate fraud score |

**Expected response:** "Fraud screening complete for CLM-2026-1001. **Fraud score: 0**. No red flags identified. No prior claims pattern detected. This claim does not require SIU referral."

---

**Test 2 — Check fraud flags only**
```bash
curl -s -N -X POST http://localhost:8903/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Are there any fraud flags on claim CLM-2026-1001?"}' \
  --max-time 60
```

| Expected tools called | What it confirms |
|---|---|
| `get_fraud_flags` | Returns list of fraud_flags rows |

**Expected response:** "No active fraud flags found for claim CLM-2026-1001."

---

### A-4 · DamageAssessmentAgent · Port 8907

**Purpose:** Assess and itemize physical damage for a claim.

```powershell
cd AdjusterAgents
py -3 DamageAssessmentAgent/server.py
```

**Test 1 — Assess damage**
```bash
curl -s -N -X POST http://localhost:8907/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Assess the damage for claim CLM-2026-1001. Kitchen burst pipe caused flooding. The flooring, lower cabinets, and drywall are damaged. There is also plumbing repair needed."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim |
| `write_damage_item` (×3–4) | Creates damage_items rows per category |
| `get_damage_items` | Retrieves all items for summary |

**Expected response:** Itemized list e.g.:
- Flooring (Laminate) — Medium — $3,500
- Lower Cabinets — Medium — $2,000
- Drywall — Low — $1,000
- Plumbing repair — Medium — $2,000
- **Total: $8,500**

---

**Test 2 — Condition assessment**
```bash
curl -s -N -X POST http://localhost:8907/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Run a condition assessment for the flooring in claim CLM-2026-1001. The laminate is 4 years old and has a remaining useful life of 6 years."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `write_condition_assessment` | Saves structural_integrity_score, age, wear level |

**Expected response:** Condition score with repair vs replacement recommendation based on age and remaining useful life.

---

### A-5 · EvidenceValidationAgent · Port 8904

**Purpose:** Cross-validate evidence items against claim details.

```powershell
cd AdjusterAgents
py -3 EvidenceValidationAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Validate all evidence submitted for claim CLM-2026-1001. Check if the repair estimate is consistent with the reported damage."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_documents` | Loads uploaded evidence |
| `get_damage_items` | Loads damage assessment |
| `run_evidence_validation` | Cross-checks consistency |
| `save_validation_result` | Writes result to DB |

**Expected response:** "Evidence validation complete. 2 documents on file. The repair estimate ($950) is consistent with the plumbing damage item ($2,000) — note estimate is for pipe repair only, not full scope. Validation status: **Partially Complete**. Recommend: obtain full-scope estimate."

---

### A-6 · ExternalDataAgent · Port 8905

**Purpose:** Pull weather data, drone imagery, and third-party verification to corroborate the claim.

```powershell
cd AdjusterAgents
py -3 ExternalDataAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Pull external weather data for Springfield IL on 2026-05-20 to corroborate claim CLM-2026-1001 (water damage from burst pipe)."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_weather_alignment` | Checks weather event data |
| `get_drone_authenticity` | Checks drone imagery if available |
| `run_external_verification` | Runs full external check |
| `save_external_verification` | Writes to external_verifications table |

**Expected response:** Weather corroboration result — temperature, precipitation on date of loss. If no anomalous weather: "No weather event matches burst pipe — consistent with internal plumbing failure. External data supports claim narrative."

---

### A-7 · LossAssessmentAgent · Port 8906

**Purpose:** Compute total loss, depreciation, deductible, and recommended settlement.

```powershell
cd AdjusterAgents
py -3 LossAssessmentAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Run a full loss assessment for claim CLM-2026-1001. Total repair estimate is $8,500."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim and coverage |
| `get_damage_items` | Loads itemized damages |
| `get_policy_details` | Gets deductible, coverage limit |
| `run_loss_assessment` | Computes net_payable after deductible + depreciation |
| `save_loss_assessment` | Saves to loss_assessments table |

**Expected response:** "Loss assessment for CLM-2026-1001: Total repair: $8,500 · Depreciation (10%): -$850 · Deductible: -$1,000 · **Net payable: $6,650** · Recommendation: Repair (not replace) · Confidence: 88%."

---

### A-8 · RepairVsReplacementAgent · Port 8908

**Purpose:** Recommend repair or replacement for each damaged item.

```powershell
cd AdjusterAgents
py -3 RepairVsReplacementAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Should the laminate flooring in claim CLM-2026-1001 be repaired or replaced? It is 4 years old with repair cost $800 and replacement cost $3,500."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_repair_cost` | Gets repair estimate details |
| `get_replacement_cost` | Gets replacement estimate details |
| `run_repair_vs_replacement` | Computes recommendation based on age, cost ratio |
| `save_repair_vs_replacement` | Saves recommendation to DB |

**Expected response:** "Recommendation for laminate flooring (4 years old): **Replace**. Repair-to-replacement cost ratio: 23%. Given the age (4 of 10-year useful life) and extent of saturation, replacement is more cost-effective long-term."

---

### A-9 · ReserveRecommendationAgent · Port 8909

**Purpose:** Set or adjust the financial reserve for a claim.

```powershell
cd AdjusterAgents
py -3 ReserveRecommendationAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Set the initial reserve for claim CLM-2026-1001. The estimated loss is $8,500 with a $1,000 deductible."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim |
| `get_loss_assessment` | Gets net_payable from assessment |
| `run_reserve_recommendation` | Computes reserve = net payable + 15% buffer |
| `save_reserve` | Writes reserve amount to DB |

**Expected response:** "Reserve set for CLM-2026-1001: **$7,650** (net payable $6,650 + 15% buffer for supplements). Reserve is within auto-adjudication threshold ($10,000)."

---

### A-10 · FinancialLeakageAgent · Port 8910

**Purpose:** Detect over-payments, duplicate charges, or inflated vendor costs.

```powershell
cd AdjusterAgents
py -3 FinancialLeakageAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Run a financial leakage check on claim CLM-2026-1001. The submitted repair estimate is $8,500."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_damage_items` | Loads itemized costs |
| `get_vendor_benchmark` | Compares costs to market benchmarks |
| `run_leakage_detection` | Flags items above benchmark |
| `get_cost_variance` | Returns variance analysis |

**Expected response:** "Financial leakage analysis for CLM-2026-1001: No significant variances detected. All line items are within ±15% of benchmark costs. Leakage risk: **Low**."

---

### A-11 · SettlementRecommendationAgent · Port 8911

**Purpose:** Generate a final settlement recommendation for adjuster sign-off.

```powershell
cd AdjusterAgents
py -3 SettlementRecommendationAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Generate a settlement recommendation for claim CLM-2026-1001."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_loss_assessment` | Gets net payable |
| `get_fraud_risk_snapshot` | Gets fraud score |
| `get_adjuster_findings` | Gets adjuster notes |
| `run_settlement_recommendation` | Generates final amount + rationale |
| `save_settlement_recommendation` | Saves to DB |

**Expected response:** "Settlement recommendation for CLM-2026-1001: **Approve — $6,650**. Coverage confirmed. Fraud risk: Low (score 0). Damage verified via documents. Deductible applied: $1,000. No leakage detected. Ready for payment approval."

---

### A-12 · PaymentEligibilityAgent · Port 8912

**Purpose:** Confirm whether a claim is eligible for payment disbursement.

```powershell
cd AdjusterAgents
py -3 PaymentEligibilityAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Is claim CLM-2026-1001 eligible for payment disbursement?"}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Checks claim status |
| `get_settlement_recommendation` | Gets approved amount |
| `check_payment_eligibility` | Verifies all approval gates are cleared |

**Expected response:** "Claim CLM-2026-1001 is **eligible for payment**. Settlement: $6,650. All gates cleared: coverage confirmed ✓, fraud risk low ✓, reserve set ✓, adjuster approval pending."

---

### A-13 · PaymentTriggerAgent · Port 8913

**Purpose:** Initiate the payment disbursement once all approvals are in place.

```powershell
cd AdjusterAgents
py -3 PaymentTriggerAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Trigger payment for claim CLM-2026-1001. Settlement amount is $6,650. Payment method is bank transfer."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_payment_eligibility` | Confirms eligibility before triggering |
| `trigger_payment` | Creates payment_disbursements record |
| `update_claim_status` | Updates claim status to Payment Initiated |

**Expected response:** "Payment triggered for CLM-2026-1001. **Amount: $6,650** via bank transfer. Payment ID: PAY-2026-XXXXX. Estimated processing: 2–3 business days. Claim status updated to: Payment Initiated."

---

### A-14 · VerificationAgent · Port 8914

**Purpose:** Run external data verification checks (identity, address, prior claims).

```powershell
cd AdjusterAgents
py -3 VerificationAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Run identity and address verification for claim CLM-2026-1001. Policyholder: John Doe, 123 Main St Springfield IL 62701."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `run_external_verification` | Triggers verification workflow |
| `save_verification_result` | Writes to external_verifications |
| `get_verification_details` | Returns field-by-field verification |

**Expected response:** "Verification complete for CLM-2026-1001: Name ✓ · Address ✓ · Policy active ✓ · No prior claims mismatch. Verification status: **Passed**."

---

### A-15 · RoutingAgent · Port 8915

**Purpose:** Route a claim to the appropriate adjuster or processing path.

```powershell
cd AdjusterAgents
py -3 RoutingAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:<port>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Route claim CLM-2026-1001 to the appropriate adjuster. It is a Medium severity water damage claim with estimated cost of $8,500."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_triage_result` | Gets priority and complexity |
| `get_adjuster_workload` | Finds available adjuster |
| `run_routing` | Assigns to adjuster |
| `log_auto_assignment` | Saves routing decision |
| `update_claim_assigned_adjuster` | Updates claims table |

**Expected response:** "Claim CLM-2026-1001 routed to **Jane Smith (Adjuster ID: ADJ-003)**. Routing rationale: Medium complexity water damage, adjuster specialised in property claims, current workload: 4 active claims (within capacity). Auto-assignment logged."

---

## 6. Persona 3 — SIU Investigator (12 agents)

**MCP server:** port `9000`  
**Start all SIU agents:**
```powershell
cd SIUAgents
foreach ($a in @("FraudRiskScoringAgent","CaseAssignmentAgent","BehavioralAnalyticsAgent","EntityRelationshipAgent","FraudPatternAgent","NetworkAnalysisAgent","EvidenceCorrelationAgent","FraudEscalationAgent","FraudResolutionAgent","LegalEscalationAgent","WatchlistUpdateAgent","SIUClosureAgent")) {
    Start-Process -WindowStyle Hidden py "-3 $a/server.py"
    Start-Sleep 1
}
```

---

### S-1 · FraudRiskScoringAgent · Port 9001

**Purpose:** Compute and recompute the aggregate fraud risk score from all signals and flags.

```powershell
cd SIUAgents
py -3 FraudRiskScoringAgent/server.py
```

**Test 1 — Get fraud risk score**
```bash
curl -s -N -X POST http://localhost:9001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Compute the fraud risk score for claim CLM-2026-1001 and tell me if it warrants SIU investigation."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_fraud_risk_snapshot` | Gets current aggregate score |
| `get_ai_fraud_signals` | Gets individual AI signals |
| `get_fraud_flags` | Gets active flags |
| `recompute_fraud_risk_score` | Recalculates and updates snapshot |

**Expected response:** "Fraud risk score for CLM-2026-1001: **0 / 100**. No AI signals, no active flags. Prior claims risk: Low. Vendor risk: Low. **SIU investigation not warranted** at this time."

---

**Test 2 — Simulate elevated risk**
```bash
curl -s -N -X POST http://localhost:9001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What would trigger an SIU referral for this type of water damage claim?"}' \
  --max-time 60
```

**Expected response:** Explains triggers: fraud score ≥ 50, multiple prior claims, timeline inconsistencies, inflated vendor estimates, contractor relationship flags.

---

### S-2 · CaseAssignmentAgent · Port 9002

**Purpose:** Assign a SIU investigator to a fraud case.

```powershell
cd SIUAgents
py -3 CaseAssignmentAgent/server.py
```

**Test 1 — Assign investigator**
```bash
curl -s -N -X POST http://localhost:9002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Assign the best available SIU investigator to claim CLM-2026-1001. The loss type is water damage with medium fraud risk."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_siu_case_master` | Checks for existing SIU case |
| `get_investigator_list` | Lists available investigators |
| `assign_investigator` | Creates/updates assignment |

**Expected response:** "SIU case created for CLM-2026-1001. Assigned investigator: **Agent R. Torres** (speciality: Property / Water Damage). Assignment logged. Case status: Active."

---

**Test 2 — Check case status**
```bash
curl -s -N -X POST http://localhost:9002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current SIU case status for claim CLM-2026-1001?"}' \
  --max-time 60
```

| Expected tools called | What it confirms |
|---|---|
| `get_siu_case_master` | Returns case record |

---

### S-3 · BehavioralAnalyticsAgent · Port 9003

**Purpose:** Detect anomalous policyholder behaviour patterns.

```powershell
cd SIUAgents
py -3 BehavioralAnalyticsAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9003/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Run behavioral analytics on policyholder John Doe (policy POL-1001) for claim CLM-2026-1001. Check for any unusual claim filing patterns."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claims_by_policy` | Gets claim history |
| `run_behavioral_analysis` | Checks frequency, timing, amounts |
| `save_behavioral_result` | Writes findings to DB |

**Expected response:** "Behavioral analysis for John Doe (POL-1001): **1 prior claim** in the past 3 years. Claim frequency: Normal. Time since last claim: >12 months. No anomalous filing patterns detected. Risk level: **Low**."

---

### S-4 · EntityRelationshipAgent · Port 9004

**Purpose:** Map relationships between claimant, vendors, witnesses, and third parties.

```powershell
cd SIUAgents
py -3 EntityRelationshipAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9003/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Build an entity relationship graph for claim CLM-2026-1001. Identify all parties involved including the vendor Springfield Plumbing Pros."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Loads claim parties |
| `get_vendor_info` | Gets vendor data |
| `build_entity_graph` | Creates entity-relationship map |
| `save_entity_graph` | Saves to SIU DB |

**Expected response:** Entity graph showing: Policyholder (John Doe) → Claim (CLM-2026-1001) → Vendor (VEN-001, Springfield Plumbing Pros) → License (LIC-PL-1001). No known shared-entity fraud patterns detected.

---

### S-5 · FraudPatternAgent · Port 9005

**Purpose:** Match claim details against known fraud patterns in the database.

```powershell
cd SIUAgents
py -3 FraudPatternAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9005/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Check claim CLM-2026-1001 against known fraud patterns. Loss type: water damage, kitchen, burst pipe."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_fraud_patterns` | Loads known fraud patterns |
| `match_claim_to_patterns` | Runs pattern matching |
| `save_pattern_match_result` | Records matched/unmatched patterns |

**Expected response:** "Pattern match for CLM-2026-1001: No matches against the 12 known fraud patterns on file. Burst pipe / kitchen water damage is the most commonly legitimate claim type. Pattern risk: **Low**."

---

### S-6 · NetworkAnalysisAgent · Port 9006

**Purpose:** Detect fraud rings by analysing shared addresses, phones, or vendors across claims.

```powershell
cd SIUAgents
py -3 NetworkAnalysisAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9006/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Run network analysis for claim CLM-2026-1001. Check if the policyholder, vendor, or address appears in any other suspicious claims."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `run_network_analysis` | Scans for shared nodes across claims |
| `get_linked_claims` | Returns any connected claim IDs |

**Expected response:** "Network analysis for CLM-2026-1001: No network links found. John Doe, 123 Main St, and VEN-001 do not appear in any other active claims. **No fraud ring detected.**"

---

### S-7 · EvidenceCorrelationAgent · Port 9007

**Purpose:** Cross-correlate evidence items to verify they are internally consistent.

```powershell
cd SIUAgents
py -3 EvidenceCorrelationAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9007/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Correlate all evidence for claim CLM-2026-1001. Check if the repair estimate, photo descriptions, and FNOL timeline are consistent."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_investigation_notes` | Gets SIU notes |
| `correlate_evidence` | Cross-checks all evidence |
| `save_investigation_notes` | Writes correlation findings |

**Expected response:** "Evidence correlation for CLM-2026-1001: All items are internally consistent. Date of loss (2026-05-20) matches photo metadata. Repair estimate scope matches FNOL damage description. Timeline is plausible. **No inconsistencies detected.**"

---

### S-8 · FraudEscalationAgent · Port 9008

**Purpose:** Escalate a high-risk claim to senior SIU management.

```powershell
cd SIUAgents
py -3 FraudEscalationAgent/server.py
```

**Test question (simulate high risk):**
```bash
curl -s -N -X POST http://localhost:9008/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Escalate claim CLM-2026-1001 to senior SIU for review. The fraud score has been elevated to 75 due to inflated vendor estimates and a suspicious timeline."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_siu_case_master` | Gets case details |
| `create_siu_escalation` | Creates escalation record |
| `log_siu_timeline_event` | Logs escalation as case event |
| `forward_to_siu` | Forwards to senior investigator queue |

**Expected response:** "Claim CLM-2026-1001 has been escalated to **Senior SIU Manager**. Escalation ID: ESC-2026-XXX. Reason: elevated fraud score (75). Case flagged for priority review within 24 hours."

---

### S-9 · FraudResolutionAgent · Port 9009

**Purpose:** Record the outcome of a fraud investigation (cleared, confirmed, partial).

```powershell
cd SIUAgents
py -3 FraudResolutionAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9009/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Resolve the fraud investigation for claim CLM-2026-1001. After full review, no fraud was found. The claim is legitimate."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_siu_case_master` | Gets case |
| `resolve_fraud_case` | Sets resolution = Cleared |
| `update_claim_status` | Updates claim back to Active processing |
| `log_siu_timeline_event` | Logs closure event |

**Expected response:** "Fraud investigation for CLM-2026-1001 resolved: **Cleared — No Fraud**. Claim returned to standard processing queue. SIU case closed. Adjuster notified."

---

### S-10 · LegalEscalationAgent · Port 9010

**Purpose:** Escalate confirmed fraud to the legal team for prosecution referral.

```powershell
cd SIUAgents
py -3 LegalEscalationAgent/server.py
```

**Test question (hypothetical high-fraud scenario):**
```bash
curl -s -N -X POST http://localhost:9010/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Escalate claim CLM-2026-1001 to the legal team. Fraud has been confirmed — the policyholder staged the water damage event and submitted fabricated repair estimates totaling $45,000."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_siu_case_master` | Gets case and evidence |
| `create_legal_escalation` | Creates legal referral record |
| `update_fraud_case_status` | Sets status = Legal Referral |
| `log_siu_timeline_event` | Logs legal escalation |

**Expected response:** "Legal escalation filed for CLM-2026-1001. Referral ID: LEG-2026-XXX. Case documentation package sent to Legal Department. Claim denied and flagged for prosecution. Policyholder notified per regulatory requirements."

---

### S-11 · WatchlistUpdateAgent · Port 9011

**Purpose:** Add confirmed fraudsters to the watchlist to prevent future claims.

```powershell
cd SIUAgents
py -3 WatchlistUpdateAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9011/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Add policyholder from claim CLM-2026-1001 to the fraud watchlist. The case was confirmed fraud with fabricated estimates."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_claim_details` | Gets policyholder info |
| `add_to_watchlist` | Creates watchlist entry |
| `get_watchlist_entry` | Confirms entry was created |

**Expected response:** "Watchlist updated. John Doe (policy POL-1001, DOB if available) added to the Confirmed Fraud Watchlist. Entry ID: WL-2026-XXX. Future claims under this identity will trigger automatic SIU review."

---

### S-12 · SIUClosureAgent · Port 9012

**Purpose:** Formally close a SIU case with a disposition code.

```powershell
cd SIUAgents
py -3 SIUClosureAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9012/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Close the SIU case for claim CLM-2026-1001. Disposition: Claim Cleared — No Fraud. Investigation duration was 5 days."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_siu_case_master` | Gets open case |
| `close_siu_case` | Sets case status to Closed |
| `log_siu_timeline_event` | Logs closure with disposition |
| `update_fraud_case_status` | Final status update |

**Expected response:** "SIU case for CLM-2026-1001 formally closed. Disposition: **Cleared — No Fraud**. Investigation duration: 5 days. Case archived. Claim returned to adjuster for standard settlement."

---

## 7. Persona 4 — Vendor Manager (10 agents)

**MCP server:** port `9100`  
**Start all Vendor agents:**
```powershell
cd VendorManagerAgents
foreach ($a in @("VendorMatchingAgent","VendorQualificationAgent","VendorOnboardingAgent","VendorPerformanceAgent","VendorCapacityManagementAgent","VendorCostBenchmarkAgent","DispatchAgent","SLAComplianceAgent","ETAPredictionAgent","EscalationAgent")) {
    Start-Process -WindowStyle Hidden py "-3 $a/server.py"
    Start-Sleep 1
}
```

---

### V-1 · VendorMatchingAgent · Port 9101 (actual: 9102)

**Purpose:** Find the best-matched vendor for a claim based on specialty, location, rating, and availability.

```powershell
cd VendorManagerAgents
py -3 VendorMatchingAgent/server.py
```

**Test 1 — Find best vendor**
```bash
curl -s -N -X POST http://localhost:9102/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find the best vendor for claim CLM-2026-1001. The claim requires plumbing repair in Springfield IL. Specialty needed: Plumbing."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_vendors_by_specialty` | Filters vendors by Plumbing |
| `get_vendor_benchmark` | Gets performance data |
| `match_vendor_to_claim` | Scores and ranks vendors |

**Expected response:** "Best match for CLM-2026-1001 (Plumbing, Springfield IL): **VEN-001 — Springfield Plumbing Pros** · Rating: 4.6★ · Avg turnaround: 3 days · Avg cost: $850 · License: Valid. Would you like to proceed with this assignment?"

---

**Test 2 — Find vendor for different specialty**
```bash
curl -s -N -X POST http://localhost:9102/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find a vendor for drywall repair in Springfield IL."}' \
  --max-time 60
```

**Expected response:** Best available vendor for general contracting / drywall from the seeded vendor list.

---

### V-2 · VendorQualificationAgent · Port 9103

**Purpose:** Verify vendor license, insurance, and qualification status.

```powershell
cd VendorManagerAgents
py -3 VendorQualificationAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9103/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Verify the qualification and license status of vendor VEN-001 (Springfield Plumbing Pros) before assigning them to claim CLM-2026-1001."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_vendor_master` | Loads vendor record |
| `check_vendor_qualification` | Checks license validity, expiry |
| `get_vendor_benchmark` | Gets quality scores |

**Expected response:** "VEN-001 Springfield Plumbing Pros: License LIC-PL-1001 — **Valid**, expires 2027-12-31. Insurance: Active. Quality rating: 4.6/5. Fraud score: 0.05 (clean). **Qualification status: Approved.** Safe to assign to CLM-2026-1001."

---

### V-3 · VendorOnboardingAgent · Port 9104

**Purpose:** Process new vendor applications and onboard approved vendors.

```powershell
cd VendorManagerAgents
py -3 VendorOnboardingAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9104/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Process the pending vendor application for Hometown Water Mitigation. They specialize in water mitigation and have submitted license LIC-WM-6006."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_vendor_application` | Loads the pending application |
| `verify_vendor_license` | Validates license number |
| `approve_vendor_application` | Creates vendor record |
| `onboard_vendor` | Adds to vendor_master_input |

**Expected response:** "Vendor application for Hometown Water Mitigation reviewed. License LIC-WM-6006 verified. **Application: Approved.** Vendor ID assigned: VEN-006. Added to the active vendor pool for Water Mitigation assignments."

---

### V-4 · VendorPerformanceAgent · Port 9105

**Purpose:** Analyse vendor performance metrics across all assigned jobs.

```powershell
cd VendorManagerAgents
py -3 VendorPerformanceAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9105/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyse the performance of vendor VEN-001 (Springfield Plumbing Pros) across all claims they have handled."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_vendor_jobs` | Gets all jobs for VEN-001 |
| `get_vendor_benchmark` | Gets benchmark data |
| `run_performance_analysis` | Computes on-time rate, cost variance |
| `save_performance_result` | Writes analysis to DB |

**Expected response:** "VEN-001 Performance Report: 124 completed jobs · Avg turnaround: 3.0 days (benchmark: 3) ✓ · On-time rate: 96% · Avg cost: $850 (within benchmark) ✓ · Rating: 4.6/5. **Performance grade: A (Excellent)**."

---

### V-5 · VendorCapacityManagementAgent · Port 9106

**Purpose:** Check vendor availability and capacity before assignment.

```powershell
cd VendorManagerAgents
py -3 VendorCapacityManagementAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9106/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Check the current capacity of vendor VEN-001 (Springfield Plumbing Pros). Can they take on a new job for claim CLM-2026-1001 starting next week?"}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_vendor_active_jobs` | Checks current job count |
| `check_vendor_capacity` | Verifies capacity vs max threshold |

**Expected response:** "VEN-001 currently has 2 active jobs. Capacity threshold: 5 concurrent jobs. **Available to take on new assignment.** Earliest availability: 2026-06-18."

---

### V-6 · VendorCostBenchmarkAgent · Port 9107

**Purpose:** Compare vendor quotes to market benchmarks and flag overpriced estimates.

```powershell
cd VendorManagerAgents
py -3 VendorCostBenchmarkAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9107/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Benchmark the repair estimate of $950 submitted by VEN-001 for claim CLM-2026-1001 (plumbing repair). Is this in line with market rates?"}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_vendor_benchmark` | Gets VEN-001 avg cost = $850 |
| `compute_cost_variance` | $950 vs $850 = +11.8% variance |
| `record_vendor_cost` | Logs actual cost submitted |

**Expected response:** "VEN-001 estimate for CLM-2026-1001: $950. Market benchmark for plumbing repair: $850. Variance: **+11.8%** (within the 15% acceptable threshold). **No overpricing detected.** Estimate approved."

---

### V-7 · DispatchAgent · Port 9101 (actual: 9106)

**Purpose:** Create and manage work orders to dispatch vendors to the loss location.

```powershell
cd VendorManagerAgents
py -3 DispatchAgent/server.py
```

**Test 1 — Create a work order**
```bash
curl -s -N -X POST http://localhost:9106/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Dispatch vendor VEN-001 (Springfield Plumbing Pros) to claim CLM-2026-1001 at 123 Main St, Springfield IL 62701. Schedule for 2026-06-18 at 9:00am. Assigned by: Claims Manager."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_vendor_info` | Confirms VEN-001 details |
| `create_work_order` | Creates work order record |
| `update_claim_assigned_vendor` | Links vendor to claim |

**Expected response:** "Work order created. **WO-2026-XXX**: VEN-001 Springfield Plumbing Pros dispatched to 123 Main St, Springfield IL 62701 on 2026-06-18 at 9:00am. Estimated arrival window: 9:00–11:00am. Customer notification sent."

---

**Test 2 — Update work order status**
```bash
curl -s -N -X POST http://localhost:9106/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Update work order WO-2026-001 status to In Progress. The vendor arrived on site at 9:15am."}' \
  --max-time 60
```

| Expected tools called | What it confirms |
|---|---|
| `update_work_order_status` | Changes status to In Progress |

---

### V-8 · SLAComplianceAgent · Port 9108

**Purpose:** Monitor whether vendors are meeting their SLA deadlines.

```powershell
cd VendorManagerAgents
py -3 SLAComplianceAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9108/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Check SLA compliance for vendor VEN-001 on claim CLM-2026-1001. The work was assigned on 2026-05-01 and completed on 2026-05-04. The SLA is 3 business days."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_vendor_jobs` | Gets job record with dates |
| `check_sla_compliance` | Calculates days taken vs SLA |
| `update_vendor_sla_status` | Sets sla_status = On Track / Breached |

**Expected response:** "SLA check for VEN-001 on CLM-2026-1001: Assignment date: 2026-05-01 · Completion: 2026-05-04 · Duration: 3 days · SLA: 3 days. **Status: On Track (met SLA).** No breach logged."

---

### V-9 · ETAPredictionAgent · Port 9109

**Purpose:** Predict the estimated time to completion for a vendor job.

```powershell
cd VendorManagerAgents
py -3 ETAPredictionAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9109/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Predict the ETA for VEN-001 to complete the plumbing repair for claim CLM-2026-1001. The job started 2026-06-18."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_vendor_benchmark` | Gets avg_turnaround_days = 3 |
| `get_vendor_jobs` | Gets historical completion data |
| `predict_eta` | Calculates predicted completion date |

**Expected response:** "ETA prediction for VEN-001 on CLM-2026-1001: Based on historical average of 3 days and current job complexity (plumbing pipe replacement), **predicted completion: 2026-06-21**. Confidence: 85%."

---

### V-10 · EscalationAgent · Port 9110

**Purpose:** Escalate overdue or non-compliant vendor jobs to management.

```powershell
cd VendorManagerAgents
py -3 EscalationAgent/server.py
```

**Test question:**
```bash
curl -s -N -X POST http://localhost:9110/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Escalate vendor VEN-002 (Apex Roofing Co) for claim CLM-2026-1001. They are 2 days overdue on the inspection SLA. No contact has been made."}' \
  --max-time 90
```

| Expected tools called | What it confirms |
|---|---|
| `get_overdue_jobs` | Confirms job is overdue |
| `create_vendor_escalation` | Creates escalation record |
| `escalate_overdue_jobs` | Triggers escalation workflow |
| `update_vendor_sla_status` | Sets sla_status = Breached |

**Expected response:** "Vendor escalation raised for VEN-002 on CLM-2026-1001. **SLA breached by 2 days.** Escalation ID: VES-2026-XXX. Vendor account flagged. Vendor Manager notified. Alternative vendor (VEN-001) identified as backup."

---

## 8. Persona 5 — Orchestrator (1 agent)

**MCP:** Uses all four persona MCP servers simultaneously.

```powershell
cd OrchestratorAgent
py -3 server.py
```

**Health check:** `curl http://localhost:9201/health`

**Test 1 — Full claim lifecycle orchestration**
```bash
curl -s -N -X POST http://localhost:9201/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Orchestrate the full processing of claim CLM-2026-1001. Run fraud screening, damage assessment, vendor matching, and generate a settlement recommendation."}' \
  --max-time 180
```

| Expected tools called | What it confirms |
|---|---|
| Tools from all 4 MCP servers | Cross-persona orchestration working |
| `run_fraud_screening` | Adjuster MCP |
| `get_damage_items` | Adjuster MCP |
| `match_vendor_to_claim` | Vendor MCP |
| `run_settlement_recommendation` | Adjuster MCP |

**Expected response:** A consolidated summary covering fraud status, damage total, recommended vendor, and settlement amount — pulling data from all personas in one response.

---

**Test 2 — Status summary across personas**
```bash
curl -s -N -X POST http://localhost:9201/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Give me a complete status summary for claim CLM-2026-1001 across all departments — policyholder, adjuster, SIU, and vendor."}' \
  --max-time 180
```

**Expected response:** Cross-persona summary table: FNOL status, adjuster assignment, fraud risk, vendor dispatched, SLA status, estimated settlement.

---

## 9. Quick Smoke Test (15 min)

Run these 10 tests in sequence to verify the core claim lifecycle works end-to-end:

```bash
# 1. FNOL intake (Policyholder)
curl -s -N -X POST http://localhost:8801/chat -H "Content-Type: application/json" \
  -d '{"message":"My policy is POL-1001. I am John Doe. I had water damage from a burst pipe in my kitchen on June 15 2026."}' --max-time 60 | grep "^data:" | grep -v "\[Tool:" | sed 's/^data: //' | tr -d '\n'

echo ""

# 2. Claim status (Policyholder)
curl -s -N -X POST http://localhost:8804/chat -H "Content-Type: application/json" \
  -d '{"message":"What is the status of claim CLM-2026-1001?"}' --max-time 30 | grep "^data:" | grep -v "\[Tool:" | sed 's/^data: //' | tr -d '\n'

echo ""

# 3. Fraud screening (Adjuster)
curl -s -N -X POST http://localhost:8903/chat -H "Content-Type: application/json" \
  -d '{"message":"Run fraud screening on claim CLM-2026-1001."}' --max-time 60 | grep "^data:" | grep -v "\[Tool:" | sed 's/^data: //' | tr -d '\n'

echo ""

# 4. Damage assessment (Adjuster)
curl -s -N -X POST http://localhost:8907/chat -H "Content-Type: application/json" \
  -d '{"message":"Assess damage for claim CLM-2026-1001. Kitchen flooding: flooring, cabinets, drywall, pipe repair needed."}' --max-time 60 | grep "^data:" | grep -v "\[Tool:" | sed 's/^data: //' | tr -d '\n'

echo ""

# 5. Fraud risk score (SIU)
curl -s -N -X POST http://localhost:9001/chat -H "Content-Type: application/json" \
  -d '{"message":"Compute fraud risk score for claim CLM-2026-1001."}' --max-time 30 | grep "^data:" | grep -v "\[Tool:" | sed 's/^data: //' | tr -d '\n'

echo ""

# 6. Vendor matching (Vendor)
curl -s -N -X POST http://localhost:9102/chat -H "Content-Type: application/json" \
  -d '{"message":"Find the best plumbing vendor for claim CLM-2026-1001 in Springfield IL."}' --max-time 30 | grep "^data:" | grep -v "\[Tool:" | sed 's/^data: //' | tr -d '\n'
```

**All 6 should respond without `[AGENT_ERROR]` in the output.**

---

## 10. Health Check Reference

| Component | URL | Expected |
|---|---|---|
| Policyholder MCP | `http://localhost:8800/health` | `{"status":"healthy"}` |
| VoiceTextIntakeAgent | `http://localhost:8801/health` | `{"agent":"voice_text_intake_agent_policyholder"}` |
| ClaimStatusAgent | `http://localhost:8804/health` | `{"agent":"claim_status_agent"}` |
| PolicyCoverageAgent | `http://localhost:8807/health` | `{"agent":"policy_coverage_agent"}` |
| ClaimReadinessAgent | `http://localhost:8808/health` | `{"agent":"claim_readiness_agent"}` |
| Adjuster MCP | `http://localhost:8900/health` | `{"status":"healthy"}` |
| TriageAgent | `http://localhost:8902/health` | `{"agent":"triage_agent"}` |
| FraudScreeningAgent | `http://localhost:8903/health` | `{"agent":"fraud_screening_agent"}` |
| DamageAssessmentAgent | `http://localhost:8907/health` | `{"agent":"damage_assessment_agent"}` |
| SIU MCP | `http://localhost:9000/health` | `{"status":"healthy"}` |
| FraudRiskScoringAgent | `http://localhost:9001/health` | `{"agent":"fraud_risk_scoring_agent"}` |
| CaseAssignmentAgent | `http://localhost:9002/health` | `{"agent":"case_assignment_agent"}` |
| Vendor MCP | `http://localhost:9100/health` | `{"status":"healthy"}` |
| VendorMatchingAgent | `http://localhost:9102/health` | `{"agent":"vendor_matching_agent"}` |
| DispatchAgent | `http://localhost:9106/health` | `{"agent":"dispatch_agent"}` |

**Bulk health check (PowerShell):**
```powershell
@(8800,8801,8804,8807,8808,8900,8902,8903,8907,9000,9001,9002,9100,9102,9106) | ForEach-Object {
    $r = try { (Invoke-RestMethod "http://localhost:$_/health" -TimeoutSec 3).status } catch { "DOWN" }
    Write-Host "Port $_`: $r"
}
```

---

## 11. Troubleshooting

### Agent returns `[AGENT_ERROR]` with `ConnectError`
- **Cause:** Agent is trying to reach MCP at `http://0.0.0.0:` (old default)
- **Fix:** All `server.py` files have been updated to use `http://localhost:` — restart the agent

### Agent returns `[AGENT_ERROR]` with `NotFoundError 404` from Azure OpenAI
- **Cause:** Wrong deployment name or endpoint in `.env`
- **Fix:** Verify `AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4.1-jarvis` and `AZURE_OPENAI_ENDPOINT=https://agenticinsuranceopenai.openai.azure.com/`

### Agent returns `[AGENT_ERROR]` with `BadRequestError` — `non-unique elements`
- **Cause:** Duplicate `claim_id` in MCP tool schema (path param + body param)
- **Fix:** Already patched in `fraud_screening_mcp/models.py` and `damage_assessment_mcp/models.py` — restart MCP server

### MCP server crashes on startup with `UndefinedColumn`
- **Cause:** PostgreSQL table exists with old schema, missing new columns
- **Fix:** The `init_db.py` files now include `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` migrations — re-run `py -3 MCP/common/init_db.py`

### MCP server crashes with `DatatypeMismatch: column "coverage" is of type boolean but expression is of type integer`
- **Cause:** Seed data uses `1` for BOOLEAN columns
- **Fix:** Already patched — seed data now uses `TRUE` for all boolean fields. Re-run `py -3 MCP/common/init_db.py`

### `find_dotenv()` raises `AssertionError`
- **Cause:** Called from stdin/heredoc context with no stack frame
- **Fix:** Run scripts as files (`py -3 script.py`), not piped from stdin

### Port already in use (10048)
```powershell
# Find and kill process on a port
netstat -ano | findstr :<PORT>
Stop-Process -Id <PID> -Force
```

### Check what's running on all agent ports
```powershell
8800..8815 + 8900..8915 + 9000..9012 + 9100..9110 + @(9201) | ForEach-Object {
    $conn = netstat -an | Select-String ":$_ " | Select-String "LISTENING"
    if ($conn) { Write-Host "Port $_`: LISTENING" }
}
```
