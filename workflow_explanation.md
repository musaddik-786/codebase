# Workflow Explanation: Insurance Claims Management Platform

This document walks through the end-to-end workflows of the platform — from a policyholder filing a claim to final resolution — across all four personas.

---

## High-Level Workflow Overview

```
Policyholder files FNOL
        ↓
Claim created in system (status: Open)
        ↓
Adjuster reviews claim
        ↓
   ┌────────────────────────────────────┐
   │         Parallel Tracks           │
   │                                   │
   │  Fraud Detection    Vendor Work   │
   │  ─────────────      ──────────    │
   │  Drone Check        Assign Vendor │
   │  Weather Check      Get Estimate  │
   │  Pattern Check      Work Order    │
   └────────────────────────────────────┘
        ↓
   Suspicious? → Refer to SIU
   Complex?    → Dispatch Expert
        ↓
Adjuster makes Accept / Reject decision
        ↓
Policyholder notified of outcome
```

---

## Workflow 1: Policyholder Files a Claim (FNOL)

This is the entry point of every claim in the system.

### Step 1 — Choose Claim Type
The policyholder logs in and is presented with two FNOL options:
- **Standard FNOL** — for property damage (fire, flood, theft, etc.)
- **Motor FNOL** — specifically for vehicle accidents, with fields for vehicle details, driver info, and accident circumstances

### Step 2 — Fill the FNOL Form
The intelligent FNOL form guides the policyholder through:
- Policy number and personal details
- Date, time, and location of the loss event
- Description of what happened and what was damaged
- Upload of initial supporting photos or documents (goes to Google Cloud Storage)

### Step 3 — Submission & Claim Creation
On submission:
- A new record is inserted into the `claims` table
- A unique claim number is generated and shown to the policyholder
- Claim status is set to `Open`
- The adjuster dashboard is updated with the new incoming claim

### Step 4 — Policyholder Tracks Progress
After filing, the policyholder can use the **Follow My Claim** page to:
- See the current status of their claim (Open → Under Investigation → Approved/Rejected)
- View any notes or requests from the adjuster
- Upload additional documents if requested
- View their Motor Claim Summary if it's a vehicle claim

---

## Workflow 2: Adjuster Reviews and Investigates a Claim

Once a claim lands in the system, the adjuster takes over.

### Step 1 — Adjuster Dashboard
The adjuster sees a queue of all open claims. Each card shows claim number, policyholder name, loss type, date filed, and current status. Claims can be filtered by status, loss type, or date.

### Step 2 — Open Claim Details
Clicking a claim opens the full claim detail view with:
- All FNOL information submitted by the policyholder
- Uploaded documents and photos
- Fraud detection results (automatically triggered on claim creation)
- Vendor assignment status
- Expert dispatch status
- Adjuster findings and notes

### Step 3 — Review Fraud Signals
The adjuster reviews automated fraud detection results (see Workflow 3). Based on the signals, they decide:
- **Green** — No suspicious signals. Proceed normally.
- **Amber** — Some signals. Proceed with caution and gather more evidence.
- **Red** — Strong fraud indicators. Refer to SIU (see Workflow 5).

### Step 4 — Request Additional Information (if needed)
The adjuster can add notes to the claim requesting the policyholder to submit more evidence, clarify details, or provide a recorded statement.

### Step 5 — Assign a Vendor (if repair work is needed)
For property damage claims requiring physical repair work, the adjuster uses **Smart Vendor Match** (see Workflow 4) to assign a vendor and generate a work order.

### Step 6 — Dispatch an Expert (if needed)
For complex claims requiring specialist opinion — structural engineers, forensic accountants, medical examiners — the adjuster uses the **Expert Dispatch** module (see Workflow 6).

### Step 7 — Repair vs. Replacement Decision
Using the **Cost Estimate Analytics** tool, the adjuster compares vendor estimates and decides whether it is more cost-effective to repair or replace the damaged item. The platform presents side-by-side cost comparisons and historical benchmarks.

### Step 8 — Final Decision
Once investigation is complete, the adjuster makes a final call:
- **Accept** — Claim is approved. Settlement amount is determined.
- **Reject** — Claim is denied with documented reasons.
- The decision is recorded in `adjusterFindings` and the claim status is updated accordingly.
- The policyholder is notified of the outcome.

---

## Workflow 3: Automated Fraud Detection

Fraud checks are triggered automatically when a claim is filed and run in parallel. The adjuster sees the aggregated results in the claim detail view.

### Check 1 — Drone Image Authenticity
- Any drone or aerial imagery uploaded as evidence is analyzed for:
  - Image metadata inconsistencies (GPS mismatch, timestamp issues)
  - Signs of digital manipulation or CGI
  - Discrepancies between the claimed damage location and the image location
- Results are stored in `droneAuthenticityData` with an authenticity score and flags
- **Outcome**: Authentic / Suspicious / Manipulated

### Check 2 — Weather-Location Alignment
- The system cross-references the reported loss location and loss date against historical weather event data
- Example: A claim for flood damage in a location that had no rainfall on the reported date is flagged
- Results stored in `weatherLocationAlignment`
- **Outcome**: Aligned / Misaligned / Inconclusive

### Check 3 — Vendor Fraud Pattern Analysis
- If the policyholder has named a preferred vendor or contractor, the system checks:
  - Whether the vendor has a history of inflated estimates
  - Whether the vendor appears in multiple suspicious claims
  - Whether the vendor's estimate is an outlier compared to market rates
- Findings stored in `fraudFlags`
- **Outcome**: No flags / Moderate risk / High risk

### Check 4 — Pre-Loss Alerts
- The system scans the policyholder's policy and claim history for:
  - Multiple claims filed in a short period
  - Claims filed shortly after policy inception or upgrade
  - Prior fraud flag history
- Results stored in `preLossAlerts`
- **Outcome**: Clean / Alert raised

### Aggregated Fraud Score
All four checks feed into a combined fraud risk score visible to the adjuster. High scores trigger a prompt to refer the case to SIU.

---

## Workflow 4: Vendor Assignment and Work Order

When a claim requires physical repair, the adjuster coordinates with a vendor.

### Step 1 — Search Vendor Directory
The adjuster opens the **Vendor Directory** and searches by:
- Specialty (roofing, plumbing, electrical, auto body, etc.)
- Geographic proximity to the loss location
- Availability and current workload
- Performance score and compliance status

### Step 2 — Smart Vendor Match
The **Smart Vendor Match** tool automatically suggests the best-fit vendors based on claim type, location, vendor history, and cost profile. The adjuster can accept a suggestion or manually override.

### Step 3 — Generate Work Order
Once a vendor is selected:
- A work order is created in the `workOrders` table with:
  - Claim reference
  - Scope of work
  - Expected completion date
  - SLA terms
- The vendor receives a notification with work order details

### Step 4 — Vendor Receives and Accepts Work Order
The vendor logs into the **Vendor Portal** and:
- Views the work order details
- Accepts or requests clarification
- Schedules the site visit

### Step 5 — Vendor Submits Estimate
After assessing the damage on-site, the vendor submits a detailed repair estimate:
- Line-item cost breakdown
- Material and labor costs
- Estimated timeline
- Stored in `vendorEstimates`

### Step 6 — Adjuster Reviews Estimate
The adjuster reviews the estimate against:
- Market benchmarks
- Other vendor quotes (if multiple vendors were asked)
- The repair vs. replacement analysis
- Approves or negotiates the estimate

### Step 7 — Work Completed and Closed
After the vendor completes the work:
- Vendor marks the work order as complete
- Adjuster confirms completion
- Work order is closed and feeds into the settlement calculation
- Vendor's performance score is updated based on timeliness and quality

---

## Workflow 5: SIU Investigation

When fraud signals are strong enough, the adjuster refers the claim to a Special Investigation Unit (SIU) investigator.

### Step 1 — Adjuster Refers to SIU
The adjuster clicks "Refer to SIU" from the claim detail view, which:
- Changes the claim status to `Under SIU Investigation`
- Creates an investigation record linked to the claim
- Notifies available SIU investigators

### Step 2 — SIU Investigator Opens Case
The SIU investigator logs in and opens their **SIU Investigation Workbench**, which shows:
- All claims referred to SIU
- Fraud flags and scores from automated checks
- Drone authenticity results
- Weather alignment data
- Vendor risk flags
- Prior claim history of the policyholder

### Step 3 — Deep Investigation
The SIU investigator conducts a thorough investigation:
- Reviews all uploaded evidence and documents
- May request additional evidence from the policyholder
- May request drone re-inspection or independent weather data
- Documents all findings in `adjusterFindings`

### Step 4 — Cross-Reference Data
The investigator cross-checks:
- Claim details vs. policy terms
- Reported loss location vs. actual GPS data from images
- Vendor estimates vs. independent cost assessments
- Policyholder's financial background (if applicable)

### Step 5 — Investigation Outcome
The SIU investigator concludes with one of three outcomes:
- **Fraud Confirmed** — Claim is rejected and potentially escalated for legal action. Fraud is flagged on the policyholder's record.
- **Fraud Cleared** — No fraud found. Claim is returned to the adjuster for normal processing.
- **Inconclusive** — Further investigation needed. Case may be held pending more information.

---

## Workflow 6: Expert Dispatch

For claims requiring specialist expertise beyond what the adjuster or vendor can assess, an independent expert is dispatched.

### Step 1 — Adjuster Identifies Need
The adjuster decides an expert is needed — for example:
- Structural engineer for a major building collapse claim
- Forensic accountant for a large business interruption claim
- Medical examiner for a personal injury claim

### Step 2 — Search Expert Directory
The adjuster searches the **Expert Directory** by:
- Specialty/discipline
- Location
- Availability (checked against `expertSchedules`)
- Prior engagement history

### Step 3 — Book Expert
The adjuster books the expert:
- Selects an available time slot
- Creates a dispatch record in `dispatchLogs`
- Expert receives a notification with claim details and visit information

### Step 4 — Expert Conducts Assessment
The expert visits the loss site or reviews submitted documentation and:
- Prepares an independent assessment report
- Uploads findings to the claim
- The report is stored as an evidence item

### Step 5 — Adjuster Uses Expert Report
The adjuster incorporates the expert's findings into the claim decision:
- The report may support or contradict the vendor's estimate
- May confirm or rule out fraud
- Feeds directly into the final accept/reject decision

---

## Workflow 7: Parametric Claims (Automated Trigger-Based)

Parametric claims bypass the traditional manual investigation process entirely.

### How It Works
- A parametric policy defines a **trigger condition** — e.g., wind speed exceeding 120 km/h at a specific location, or rainfall exceeding a threshold within 48 hours
- The platform monitors external data feeds (weather stations, satellite data)
- When a trigger condition is met, the system **automatically creates a claim** for all policies in the affected area
- The claim is **automatically approved** and a payout is calculated based on pre-agreed parametric terms — no adjuster review needed
- The policyholder is notified of the automatic payout

### Use Cases
- Agricultural insurance (drought, flood, frost triggers)
- Catastrophe/natural disaster coverage (hurricane, earthquake)
- Travel insurance (flight delays exceeding a threshold)

---

## Claim Status Lifecycle

Every claim moves through a defined set of statuses:

```
Open
  ↓
Under Review (adjuster picks it up)
  ↓
Under Investigation (active fraud checks, vendor, expert work)
  ↓
Under SIU Investigation (if referred)
  ↓
Pending Decision (all inputs gathered)
  ↓
Approved  ─┐
            ├── Closed
Rejected  ─┘
```

Each status transition is logged with a timestamp, the acting user, and any associated notes. The policyholder's **Follow My Claim** view reflects the current status in real time.

---

## Summary

The platform supports five distinct workflow types that can run in parallel on a single claim:

| Workflow | Triggered By | Key Output |
|----------|-------------|------------|
| FNOL Intake | Policyholder | New claim created |
| Adjuster Review | Adjuster | Investigation + final decision |
| Fraud Detection | Automatic (on claim creation) | Fraud risk score + flags |
| Vendor Work Order | Adjuster | Repair estimate + work completion |
| SIU Investigation | Adjuster referral | Fraud confirmed / cleared |
| Expert Dispatch | Adjuster | Independent expert report |
| Parametric Trigger | Automated data feed | Auto-approved payout |

Together, these workflows cover the full spectrum of insurance claims — from a simple home repair to a complex fraud investigation — within a single unified platform.
