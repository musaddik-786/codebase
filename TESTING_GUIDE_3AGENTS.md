# Testing Guide — Claim Classification, Damage Assessment, Evidence Validation

Claim: `CLM-2026-1001` | Policy: `POL-1001` | MCP base: `http://localhost:8900`

Prerequisites: Adjuster MCP server running on port 8900, DB seeded.

---

## 1. Claim Classification Agent

### Architecture

**Port:** 8901 | **MCP:** `/api/v1/claim_classification/mcp`

**Logic and rules:**

| Step | Rule |
|------|------|
| Intake validation | 7 mandatory FNOL fields. completeness = (filled/7)×100. passed = ≥85 AND no blocking failure. Blocking: missing short_description, missing location, coverage=0 |
| Complexity | From `auto_adjudication_threshold_configs`. Simple ≤ $5k, Moderate ≤ $25k, Complex > $25k or severity=Critical/High |
| Fraud gate | Reads `fraud_risk_snapshots`. Missing row → HTTP 422 (fraud_score_unavailable). score ≥ 70 → always Complex + Specialist Review |
| STP score | 8-factor: fnolCompleteness×20% + readiness×15% + coverage×15% + severity×10% + fraudAmbiguity×10% + subrogationRisk×10% + VIS×15% + similarityIndex×5% |
| STP category | ≥85 + Low fraud + Low subrogation → Full STP. ≥70 → Vendor STP. ≥50 → Fast Track. <50 or High/Critical → Manual |
| Routing | Full STP→Fast Track. Vendor/FastTrack STP→Standard. Manual→Specialist Review. High/Critical always→Specialist Review |

**Tables read:** `claims`, `claims_master`, `policy_details`, `auto_adjudication_threshold_configs`, `fraud_risk_snapshots`, `claim_journey_master`

**Tables written:** `intake_validation_result_output`, `claim_triage` (complexity + routing), `claims.complexity` (UPDATE), `stp_score_input_factors`, `stp_calculation_result`, `segmentation_result_output`

---

### Tests

#### T1.1 — Get claim details
```bash
curl http://localhost:8900/api/v1/claim_classification/claim/CLM-2026-1001
```
**Expected:** JSON with claim fields including `loss_type`, `estimated_cost`, `severity`

---

#### T1.2 — Intake validation
```bash
curl -X POST http://localhost:8900/api/v1/claim_classification/intake-validate/CLM-2026-1001
```
**Expected:**
```json
{
  "claim_number": "CLM-2026-1001",
  "completeness_score": 100.0,
  "coverage_status": "Active",
  "fraud_risk": "Low",
  "passed": true,
  "blocking_reason": null
}
```
Row saved to `intake_validation_result_output`.

---

#### T1.3 — Classify claim (requires fraud screening to have run first)
```bash
curl -X POST http://localhost:8900/api/v1/claim_classification/classify/CLM-2026-1001
```
**Expected (if fraud screening done):**
```json
{
  "claim_number": "CLM-2026-1001",
  "complexity": "Simple",
  "routing": "Fast Track",
  "fraud_score": 15,
  "estimated_cost": 4500.0
}
```
**Expected (if fraud screening NOT done):**
```json
HTTP 422
{"error": "fraud_score_unavailable", "message": "...", "action_required": "..."}
```

---

#### T1.4 — Save classification
```bash
curl -X POST "http://localhost:8900/api/v1/claim_classification/save/CLM-2026-1001?complexity=Simple&routing=Fast+Track"
```
**Expected:** `{"saved": true, "claim_number": "CLM-2026-1001"}`

---

#### T1.5 — Compute STP score
```bash
curl -X POST http://localhost:8900/api/v1/claim_classification/stp-score/CLM-2026-1001
```
**Expected:**
```json
{
  "claim_number": "CLM-2026-1001",
  "weighted_score": 78.5,
  "stp_category": "Vendor STP",
  "recommended_path": "Standard",
  "fraud_ambiguity": "Low",
  "subrogation_risk": "Low"
}
```
Rows saved to `stp_score_input_factors`, `stp_calculation_result`, `segmentation_result_output`.

---

#### T1.6 — Read back results
```bash
curl http://localhost:8900/api/v1/claim_classification/result/CLM-2026-1001
curl http://localhost:8900/api/v1/claim_classification/stp-result/CLM-2026-1001
curl http://localhost:8900/api/v1/claim_classification/intake-result/CLM-2026-1001
```
**Expected:** Most recent row from each respective table.

---

#### T1.7 — Agent chat (end-to-end)
```bash
curl -N -X POST http://localhost:8901/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Classify claim CLM-2026-1001"}'
```
**Expected SSE stream:** Agent calls get_claim_details → run_intake_validation → classify_claim → save_classification → compute_stp_score → get_claim_classification → get_stp_result → text summary → "End"

---

#### T1.8 — Fraud score unavailable (negative test)
Use a claim that has no `fraud_risk_snapshots` row:
```bash
curl -X POST http://localhost:8900/api/v1/claim_classification/classify/CLM-NO-FRAUD
```
**Expected:** HTTP 422 with `"error": "fraud_score_unavailable"`

---

## 2. Damage Assessment Agent

### Architecture

**Port:** 8907 | **MCP:** `/api/v1/damage_assessment/mcp`

**Logic and rules:**

| Step | Rule |
|------|------|
| Item categories | Validated per loss_type: Water→Flooring/Drywall/Insulation, Fire→Kitchen Cabinets/Countertops/Appliances, Storm→Roof Shingles/Siding/Gutters |
| Material cost | `avgCost × 0.25 × (1 + i × 0.15)` where i=item index (0-based), avgCost = estimatedCost/numItems |
| Labor hours | `8 + i × 4` |
| Labor rate | $75/hr |
| Diagnostic fee | $150 |
| Urgency factor | 1.15 for Fire, 1.0 otherwise |
| Total repair | `(materialCost + laborHours×75 + 150) × urgencyFactor` |
| Condition assessment | ageYears=random(5-15). wearLevel: >10yr→High, >5yr→Moderate, else→Low. structuralIntegrity=random(50-90). safetyRisk: Fire→Medium, else→Low. environmentalImpact: Fire→Smoke/soot, Water/Flood→Mold risk, else→Minimal |
| Replacement cost | materialCost×1.8 for material. installHours=laborHours×0.7. delivery=$250. disposal=$150. total=(replaceMaterial + installHrs×75) + 250 + 150 |

**Tables read:** `claims`, `damage_items`, `condition_assessments`, `repair_costs`, `replacement_costs`

**Tables written:** `damage_items`, `condition_assessments`, `repair_costs`, `replacement_costs`

---

### Tests

#### T2.1 — Get claim details
```bash
curl http://localhost:8900/api/v1/damage_assessment/claim/CLM-2026-1001
```
**Expected:** Claim record with `loss_type`, `estimated_cost`

---

#### T2.2 — Analyze damage (no items yet)
```bash
curl -X POST http://localhost:8900/api/v1/damage_assessment/analyze/CLM-2026-1001
```
**Expected:**
```json
{
  "claim_number": "CLM-2026-1001",
  "identified_items": [
    {
      "category": "Flooring",
      "severity": "Moderate",
      "estimated_cost": 1250.0,
      "material_cost": 1125.0,
      "labor_hours": 8,
      "urgency_factor": 1.0,
      "total_repair_estimate": 1875.0,
      "adjuster_notes": "..."
    },
    ...
  ]
}
```
Items NOT yet in DB.

---

#### T2.3 — Write damage item
```bash
curl -X POST http://localhost:8900/api/v1/damage_assessment/items/CLM-2026-1001 \
  -H "Content-Type: application/json" \
  -d '{"category": "Flooring", "severity": "Moderate", "estimated_cost": 1250.0, "adjuster_notes": "Water logged hardwood"}'
```
**Expected:** `{"damage_id": "DMG-...", "claim_number": "CLM-2026-1001", "saved": true}`

---

#### T2.4 — Get damage items
```bash
curl http://localhost:8900/api/v1/damage_assessment/items/CLM-2026-1001
```
**Expected:** Array of saved damage items.

---

#### T2.5 — Auto-generate condition assessment
```bash
# Use a real damage_id returned from T2.3/T2.4
curl -X POST http://localhost:8900/api/v1/damage_assessment/auto-conditions/CLM-2026-1001/DMG-XXXXX
```
**Expected:**
```json
{
  "damage_id": "DMG-XXXXX",
  "age_years": 9,
  "wear_level": "Moderate",
  "structural_integrity_score": 67,
  "safety_risk": "Low",
  "environmental_impact": "Mold risk",
  "saved": true
}
```

---

#### T2.6 — Get condition assessments
```bash
curl http://localhost:8900/api/v1/damage_assessment/conditions/CLM-2026-1001
```
**Expected:** Array of condition assessments for the claim.

---

#### T2.7 — Compute and save repair + replacement costs
```bash
curl -X POST http://localhost:8900/api/v1/damage_assessment/compute-costs/CLM-2026-1001
```
**Expected:**
```json
{
  "claim_number": "CLM-2026-1001",
  "items_processed": 3,
  "repair_costs": [...],
  "replacement_costs": [...]
}
```
Rows saved to `repair_costs` and `replacement_costs`. Safe to call again (idempotent).

---

#### T2.8 — Read repair and replacement costs
```bash
curl http://localhost:8900/api/v1/damage_assessment/repair-costs/CLM-2026-1001
curl http://localhost:8900/api/v1/damage_assessment/replacement-costs/CLM-2026-1001
```
**Expected:** Saved cost records with material/labor/total breakdown.

---

#### T2.9 — Analyze when items already exist (idempotency)
```bash
curl -X POST http://localhost:8900/api/v1/damage_assessment/analyze/CLM-2026-1001
```
**Expected:** `{"identified_items": [], "message": "Damage items already exist..."}`

---

#### T2.10 — Agent chat (end-to-end)
```bash
curl -N -X POST http://localhost:8907/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Assess damage for claim CLM-2026-1001"}'
```
**Expected SSE stream:** get_claim_details → analyze_damage_from_description → write_damage_item (×N) → get_damage_items → generate_condition_assessment (×N) → compute_and_save_repair_replacement → get_repair_costs → get_replacement_costs → summary → "End"

---

## 3. Evidence Validation Agent

### Architecture

**Port:** 8905 | **MCP:** `/api/v1/evidence_validation/mcp`

**Logic and rules:**

| Step | Rule |
|------|------|
| Required evidence types | Water Damage→photos/repair_estimate/plumber_report. Fire→photos/fire_report/repair_estimate. Storm→photos/weather_report/repair_estimate. Theft/Other→photos/police_report |
| Completeness | (matched_required / total_required) × 100 |
| DB fraud status | Reads `fraud_risk_snapshots` (score), `fraud_flags` (active count), `ai_fraud_signals`. Suspicious = score≥70 OR ≥2 active flags |
| Drone fraud score | `100 - droneMatchPercent + penalties`. Penalties: +20 tampering, +15/+8 geoMatch=null/Partial, +15/+8 inflation=High/Medium, +10 weatherMatch=No. Clamped 0-100 |
| Drone auto-flags | Red: match<60%, tampering detected, geoMatch=null. Amber: geoMatch=Partial, weatherMismatch |
| Effective fraud score | `max(db_fraud_score, drone_fraud_score)` |
| Overall status | ≥70 → Suspicious. ≥40 → Under Review. else → Verified (complete) or Incomplete |
| Evidence ID safety | save_validation_result cross-checks all flag evidence_ids against real DB IDs — discards hallucinated IDs |

**Tables read:** `evidence_items`, `claim_documents` (documents), `damage_items`, `fraud_risk_snapshots`, `fraud_flags`, `ai_fraud_signals`, `drone_authenticity_data`, `weather_location_alignment`

**Tables written:** `evidence_validation_results`, `evidence_items.status` (UPDATE to Flagged/Verified)

---

### Tests

#### T3.1 — Get evidence items
```bash
curl http://localhost:8900/api/v1/evidence_validation/evidence/CLM-2026-1001
```
**Expected:** Array of evidence items with type, status, file_name.

---

#### T3.2 — Get claim documents
```bash
curl http://localhost:8900/api/v1/evidence_validation/documents/CLM-2026-1001
```
**Expected:** Array of uploaded documents.

---

#### T3.3 — Get damage items (cross-reference)
```bash
curl http://localhost:8900/api/v1/evidence_validation/damage-items/CLM-2026-1001
```
**Expected:** Array of damage items to verify evidence coverage.

---

#### T3.4 — Run evidence validation (no DB write)
```bash
curl -X POST http://localhost:8900/api/v1/evidence_validation/validate/CLM-2026-1001
```
**Expected:**
```json
{
  "claim_id": "CLM-2026-1001",
  "completeness_percent": 66.7,
  "missing_evidence_types": ["plumber_report"],
  "fraud_signals": {
    "fraud_score": 15,
    "active_flags": 0,
    "ai_signals": []
  },
  "drone_data": {...},
  "drone_fraud_score": 12,
  "effective_fraud_score": 15,
  "drone_flags": [],
  "weather_alignment": {...},
  "authenticity_flags": [],
  "overall_status": "Incomplete",
  "recommendation": "Obtain missing evidence types before proceeding."
}
```
Note: Does NOT update the DB.

---

#### T3.5 — Save validation result
```bash
curl -X POST http://localhost:8900/api/v1/evidence_validation/result/CLM-2026-1001 \
  -H "Content-Type: application/json" \
  -d '{
    "overall_status": "Incomplete",
    "authenticity_flags": []
  }'
```
**Expected:** `{"saved": true, "claim_id": "CLM-2026-1001"}`

---

#### T3.6 — Drone fraud score test (high risk scenario)
Manually insert a drone_authenticity_data row with low match and tampering:
```sql
INSERT INTO drone_authenticity_data (claim_id, drone_match_percent, tampering_detected, geo_match, inflation_detected, weather_match)
VALUES ('CLM-2026-1001', 45, 'metadata_strip', 'None', 'High', 'No');
```
Then run:
```bash
curl -X POST http://localhost:8900/api/v1/evidence_validation/validate/CLM-2026-1001
```
**Expected drone_fraud_score:** 100 - 45 + 20 + 15 + 15 + 10 = 115 → clamped to **100**
**Expected overall_status:** `"Suspicious"`
**Expected drone_flags:** 3 red flags (match<60%, tampering, geoMatch=null)

---

#### T3.7 — Evidence ID safety (hallucination guard)
```bash
curl -X POST http://localhost:8900/api/v1/evidence_validation/result/CLM-2026-1001 \
  -H "Content-Type: application/json" \
  -d '{
    "overall_status": "Under Review",
    "authenticity_flags": [
      {"evidence_id": "EVD-FAKE-9999", "flag_type": "suspicious", "notes": "hallucinated id"},
      {"evidence_id": "EVD-REAL-0001", "flag_type": "suspicious", "notes": "real id"}
    ]
  }'
```
**Expected:** EVD-FAKE-9999 discarded silently, only EVD-REAL-0001 processed. No error raised.

---

#### T3.8 — Agent chat (end-to-end)
```bash
curl -N -X POST http://localhost:8905/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Validate evidence for claim CLM-2026-1001"}'
```
**Expected SSE stream:** get_evidence_items → get_claim_documents → get_damage_items → run_evidence_validation → save_validation_result → summary including drone score and weather alignment → "End"

---

## Recommended Test Order (Full Lifecycle for CLM-2026-1001)

```
1. Run Fraud Screening Agent (port 8904)   → seeds fraud_risk_snapshots
2. T1.2  run_intake_validation
3. T1.3  classify_claim
4. T1.4  save_classification
5. T1.5  compute_stp_score
6. T1.6  verify results
7. T2.2  analyze_damage_from_description
8. T2.3  write_damage_item (repeat for each item)
9. T2.5  generate_condition_assessment (per damage_id)
10. T2.7 compute_and_save_repair_replacement
11. T3.4 run_evidence_validation
12. T3.5 save_validation_result
```

---

## DB Verification Queries

```sql
-- Intake validation
SELECT * FROM intake_validation_result_output WHERE claim_id = 'CLM-2026-1001' ORDER BY validated_at DESC LIMIT 1;

-- Classification
SELECT * FROM claim_triage WHERE claim_number = 'CLM-2026-1001' ORDER BY created_at DESC LIMIT 1;
SELECT complexity FROM claims WHERE claim_number = 'CLM-2026-1001';

-- STP
SELECT * FROM stp_calculation_result WHERE claim_id = 'CLM-2026-1001' ORDER BY created_at DESC LIMIT 1;
SELECT * FROM segmentation_result_output WHERE claim_id = 'CLM-2026-1001' ORDER BY created_at DESC LIMIT 1;

-- Damage
SELECT * FROM damage_items WHERE claim_number = 'CLM-2026-1001';
SELECT * FROM condition_assessments WHERE claim_id = 'CLM-2026-1001';
SELECT * FROM repair_costs WHERE claim_id = 'CLM-2026-1001';
SELECT * FROM replacement_costs WHERE claim_id = 'CLM-2026-1001';

-- Evidence
SELECT * FROM evidence_validation_results WHERE claim_id = 'CLM-2026-1001' ORDER BY created_at DESC LIMIT 1;
SELECT evidence_id, status FROM evidence_items WHERE claim_id = 'CLM-2026-1001';
```
