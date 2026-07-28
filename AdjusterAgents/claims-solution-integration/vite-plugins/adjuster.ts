// Adjuster persona API endpoints. All data comes from the external Azure
// PostgreSQL database (AZURE_DATABASE_URL). Routes are mounted under
// /api/adjuster/* :
//   /dashboard              — KPIs, STP readiness, priority claims, activity, alerts
//   /investigation-queue    — full claims queue with triage + STP info
//   /loss-assessment        — ?claimNumber= assessment detail for one claim
//   /repair-vs-replacement  — ?claimNumber= repair/replacement comparison
//   /vendor-match           — ?claimNumber= ranked vendors + recommendation
//   /verification           — ?claimNumber= imagery + drone verification data
//   /expert-dispatch        — dispatch queue, work orders, experts
import type { Plugin } from "vite";
import type { IncomingMessage, ServerResponse } from "http";
import { getPool, sendJson, formatDate, formatDateTime } from "./db";
import type pg from "pg";

type Row = Record<string, unknown>;

function str(v: unknown, fallback = "—"): string {
  if (v === null || v === undefined || v === "") return fallback;
  return String(v);
}

function num(v: unknown): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

// Normalizes to exactly "Repair" or "Replace" (case-insensitive), or null for
// anything else (long system-recommendation sentences, "Cash Settlement",
// "Deny", etc.) — matches the validation the RepairVsReplacementAgent's own
// record_adjuster_decision tool enforces, so repair_vs_replacement_decisions
// never ends up holding a value that column was never meant to carry.
function normalizeRepairReplace(value: string): "Repair" | "Replace" | null {
  const v = value.trim().toLowerCase();
  if (v === "repair") return "Repair";
  if (v === "replace" || v === "replacement") return "Replace";
  return null;
}

// The system's original recommendation (recommended_action) never changes
// after the RepairVsReplacementAgent first writes it — the adjuster's actual
// call lives in `decision`, seeded to the placeholder "Adjuster review" until
// someone saves a real override. Every UI display of "the repair vs replace
// recommendation" should show the adjuster's decision once one exists, not
// silently keep showing the original AI recommendation forever.

const LEAKAGE_RISK_LEVELS = new Set(["Low", "Medium", "High", "Critical"]);

function normalizeLeakageRisk(value: string): string | null {
  const v = value.trim();
  const match = [...LEAKAGE_RISK_LEVELS].find((level) => level.toLowerCase() === v.toLowerCase());
  return match ?? null;
}

function parseManipulationFlags(v: unknown): string[] {
  if (v === null || v === undefined) return [];
  const raw = String(v).trim();
  if (raw === "" || /^none\b/i.test(raw) || raw === "[]") return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed.map((x) => String(x)).filter(Boolean);
  } catch {
    /* not JSON — fall through */
  }
  return raw
    .split(/[;,]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function firstLine(v: unknown): string {
  return str(v).split("\n")[0].trim();
}

function daysBetween(a: Date, b: Date): number {
  return Math.max(0, Math.round((b.getTime() - a.getTime()) / 86400000));
}

// Map a loss type to the vendor specialty we should dispatch.
function specialtyForLossType(lossType: string): string {
  const lt = lossType.toLowerCase();
  if (lt.includes("water")) return "Plumbing";
  if (lt.includes("wind") || lt.includes("hail") || lt.includes("roof")) return "Roofing";
  if (lt.includes("fire")) return "Contractor";
  if (lt.includes("collision") || lt.includes("auto")) return "Auto Body";
  if (lt.includes("electric")) return "Electrical";
  return "Contractor";
}

async function handleDashboard(db: pg.Pool, res: ServerResponse) {
  const [claimsR, stpR, alertsR, journeyR] = await Promise.all([
    db.query(
      `SELECT claim_number, policyholder_name, loss_type, short_description,
              severity, status, location, filed_at, detected_cause
       FROM claims ORDER BY filed_at DESC`
    ),
    db.query(
      `SELECT DISTINCT ON (claim_number) claim_number, readiness, stp_category
       FROM stp_classification ORDER BY claim_number, created_at DESC`
    ),
    db.query(
      `SELECT alert_type, severity, title, description, location, alert_date
       FROM pre_loss_alerts WHERE resolved IS NOT TRUE
       ORDER BY alert_date DESC NULLS LAST LIMIT 6`
    ),
    db.query(
      `SELECT claim_number, current_stage_name, overall_sla_status,
              total_days_in_journey, last_stage_change_date
       FROM claim_journey_master`
    ),
  ]);

  const claims = claimsR.rows as Row[];
  const stpRows = stpR.rows as Row[];
  const journeys = journeyR.rows as Row[];
  const journeyByClaim = new Map(journeys.map((j) => [String(j.claim_number), j]));

  const now = new Date();
  const assigned = claims.length;
  const atRisk = claims.filter((c) =>
    ["high", "critical"].includes(String(c.severity ?? "").toLowerCase())
  ).length;
  const approvedToday = claims.filter((c) => {
    const s = String(c.status ?? "").toLowerCase();
    if (!(s.includes("approved") || s.includes("payment"))) return false;
    const d = c.filed_at ? new Date(String(c.filed_at)) : null;
    return d !== null && daysBetween(d, now) <= 1;
  }).length;
  const journeyDays = journeys
    .map((j) => num(j.total_days_in_journey))
    .filter((d) => d > 0);
  const avgResolutionDays = journeyDays.length
    ? Math.round((journeyDays.reduce((a, b) => a + b, 0) / journeyDays.length) * 10) / 10
    : null;

  const catCounts: Record<string, number> = { "Full STP": 0, "Vendor-STP": 0, "Fast Track": 0, Manual: 0 };
  let readinessSum = 0;
  let readinessEligible = 0;
  for (const r of stpRows) {
    const cat = String(r.stp_category ?? "").toLowerCase();
    if (cat.includes("full")) catCounts["Full STP"] += 1;
    else if (cat.includes("vendor")) catCounts["Vendor-STP"] += 1;
    else if (cat.includes("fast")) catCounts["Fast Track"] += 1;
    else catCounts["Manual"] += 1;
    readinessSum += num(r.readiness);
    if (cat.includes("full") || cat.includes("vendor")) readinessEligible += 1;
  }
  const stpReadinessPct = stpRows.length
    ? Math.round((readinessEligible / stpRows.length) * 100)
    : 0;
  const avgReadiness = stpRows.length ? Math.round(readinessSum / stpRows.length) : 0;

  const priorityClaims = claims
    .filter((c) => ["high", "critical"].includes(String(c.severity ?? "").toLowerCase()))
    .slice(0, 6)
    .map((c) => ({
      claimNumber: str(c.claim_number),
      description: str(c.short_description, str(c.detected_cause)),
      lossType: str(c.loss_type),
      location: firstLine(c.location),
      severity: str(c.severity),
      status: str(c.status),
    }));

  const recentActivity = claims.slice(0, 8).map((c) => {
    const journey = journeyByClaim.get(String(c.claim_number));
    const stage = journey ? str(journey.current_stage_name, str(c.status)) : str(c.status);
    return {
      claimNumber: str(c.claim_number),
      policyholder: str(c.policyholder_name),
      description: str(c.short_description),
      stage,
      status: str(c.status),
      filedAt: formatDateTime(c.filed_at) ?? "—",
    };
  });

  const alerts = (alertsR.rows as Row[]).map((a) => ({
    type: str(a.alert_type),
    severity: str(a.severity),
    title: str(a.title),
    description: str(a.description),
    location: firstLine(a.location),
    date: formatDate(a.alert_date) ?? "—",
  }));

  sendJson(res, 200, {
    kpis: { assigned, avgResolutionDays, atRisk, approvedToday },
    stp: { readinessPct: stpReadinessPct, avgReadiness, breakdown: catCounts, classified: stpRows.length },
    priorityClaims,
    recentActivity,
    preLossAlerts: alerts,
  });
}

async function handleInvestigationQueue(db: pg.Pool, res: ServerResponse) {
  const [claimsR, triageR, stpR] = await Promise.all([
    db.query(
      `SELECT claim_number, policyholder_name, loss_type, severity, complexity,
              status, filed_at, estimated_cost, location, short_description
       FROM claims ORDER BY filed_at DESC`
    ),
    db.query(
      `SELECT DISTINCT ON (claim_id) claim_id, damage_severity, complexity, routing, fraud_risk_score
       FROM claim_triage ORDER BY claim_id, created_at DESC`
    ),
    db.query(
      `SELECT DISTINCT ON (claim_number) claim_number, stp_category
       FROM stp_classification ORDER BY claim_number, created_at DESC`
    ),
  ]);

  const triageBy = new Map((triageR.rows as Row[]).map((t) => [String(t.claim_id), t]));
  const stpBy = new Map((stpR.rows as Row[]).map((s) => [String(s.claim_number), s]));

  const rows = (claimsR.rows as Row[]).map((c) => {
    const key = String(c.claim_number);
    const triage = triageBy.get(key);
    const stp = stpBy.get(key);
    return {
      claimNumber: key,
      policyholder: str(c.policyholder_name),
      lossType: str(c.loss_type),
      severity: str(c.severity, triage ? str(triage.damage_severity) : "—"),
      complexity: str(c.complexity, triage ? str(triage.complexity, "Simple") : "Simple"),
      status: str(c.status),
      approvalMode: stp ? str(stp.stp_category, "—") : "—",
      routing: triage ? str(triage.routing, "Standard") : "Standard",
      filed: formatDate(c.filed_at) ?? "—",
      description: str(c.short_description),
      location: firstLine(c.location),
    };
  });

  const pendingDocsR = await db.query(
    `SELECT count(*) AS c FROM documents WHERE COALESCE(flagged, 0) <> 0`
  );
  const siuCount = rows.filter((r) => r.routing.toLowerCase().includes("siu")).length;

  sendJson(res, 200, {
    stats: {
      activeCases: rows.length,
      pendingDocs: num((pendingDocsR.rows[0] as Row).c),
      siuReviews: siuCount,
    },
    claims: rows,
  });
}

async function handleLossAssessment(db: pg.Pool, res: ServerResponse, claimNumber: string) {
  const claimR = await db.query(
    `SELECT claim_number, policyholder_name, policy_number, loss_type, status,
            severity, complexity, estimated_cost, filed_at, date_of_loss, location, short_description
     FROM claims WHERE claim_number = $1 LIMIT 1`,
    [claimNumber]
  );
  if (claimR.rows.length === 0) {
    sendJson(res, 404, { error: "Claim not found" });
    return;
  }
  const claim = claimR.rows[0] as Row;

  const [policyR, damagesR, assessR, recR, lossR, findingsR, stpR2, triageR, segR, fraudSnapR, rvrR, leakageR] = await Promise.all([
    db.query(
      `SELECT coverage_type, coverage_limit, remaining_coverage_limit, deductible, status
       FROM policy_details WHERE policy_number = $1 LIMIT 1`,
      [str(claim.policy_number, "")]
    ),
    db.query(
      `SELECT damage_id, category, severity, estimated_cost, adjuster_notes, created_date
       FROM damage_items WHERE claim_number = $1 ORDER BY id`,
      [claimNumber]
    ),
    db.query(
      `SELECT assessment_id, total_parts_cost, total_labor_cost, depreciation_percent,
              deductible, subrogation_likelihood, system_recommendation,
              adjuster_override, final_recommendation, confidence_score, notes, assessment_date
       FROM loss_assessments WHERE claim_number = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT recommended_action, confidence, stp_score, settlement_amount, net_payable,
              deductible, remaining_coverage_limit, final_settlement_amount, generated_on
       FROM ai_decision_recommendations WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT ai_estimated_loss, deductible, net_payable, repair_recommended, confidence
       FROM loss_estimation_outputs WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT coverage_confirmed, fraud_risk, fraud_risk_score, repair_vs_replace,
              system_recommended_reserve, adjusted_reserve, final_settlement
       FROM adjuster_findings WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT readiness, stp_category, subrogation, fraud_ambiguity
       FROM stp_classification WHERE claim_number = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT complexity, routing FROM claim_triage WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT stp_score, recommended_path FROM segmentation_result_output
       WHERE claim_number = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT fraud_score FROM fraud_risk_snapshots
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT recommended_action, decision FROM repair_vs_replacement_decisions
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT total_estimated_cost, total_actual_cost, overall_variance_percent,
              leakage_score, leakage_risk, risk_flags, recommendation,
              adjuster_override_risk_level, adjuster_notes
       FROM financial_leakage_score WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
  ]);

  const policy = policyR.rows[0] as Row | undefined;
  const assess = assessR.rows[0] as Row | undefined;
  const rec = recR.rows[0] as Row | undefined;
  const findings = findingsR.rows[0] as Row | undefined;
  const stp = stpR2.rows[0] as Row | undefined;
  const triage = triageR.rows[0] as Row | undefined;
  const loss = lossR.rows[0] as Row | undefined;
  const seg = segR.rows[0] as Row | undefined;
  const fraudSnap = fraudSnapR.rows[0] as Row | undefined;
  const rvr = rvrR.rows[0] as Row | undefined;
  const leakage = leakageR.rows[0] as Row | undefined;

  const damages = (damagesR.rows as Row[]).map((d) => ({
    damageId: str(d.damage_id),
    category: str(d.category),
    severity: str(d.severity),
    estimatedCost: num(d.estimated_cost),
    notes: str(d.adjuster_notes, ""),
  }));

  const damageTotal = damages.reduce((a, d) => a + d.estimatedCost, 0);
  const estSettlement =
    rec && rec.settlement_amount !== null && rec.settlement_amount !== undefined
      ? num(rec.settlement_amount)
      : loss && num(loss.net_payable) > 0
        ? num(loss.net_payable)
        : damageTotal;

  const statusLower = str(claim.status).toLowerCase();
  const reviewComplete =
    statusLower.includes("approved") ||
    statusLower.includes("payment") ||
    statusLower.includes("closed") ||
    Boolean(assess?.final_recommendation);

  // Eligibility rules + AI analysis summary. Field-to-source mapping (per spec):
  //   STP Readiness      → segmentation_result_output.stp_score
  //   Fraud Risk Level   → fraud_risk_snapshots.fraud_score (>40 = High, else Low)
  //   Subrogation Risk   → loss_assessments.subrogation_likelihood
  //   Complexity Level   → claims.complexity
  //   Severity Level     → claims.severity
  // STP Readiness Score → ai_decision_recommendations.stp_score (per spec),
  // falling back to segmentation_result_output.stp_score when absent.
  const readiness =
    rec && rec.stp_score != null
      ? num(rec.stp_score)
      : seg && seg.stp_score != null
        ? num(seg.stp_score)
        : null;
  const stpCategory = stp ? str(stp.stp_category, "") : "";
  const fraudScore = fraudSnap && fraudSnap.fraud_score != null ? num(fraudSnap.fraud_score) : null;
  const fraudLevel = fraudScore == null ? "" : fraudScore > 40 ? "High" : "Low";
  const subrogationRisk = assess ? str(assess.subrogation_likelihood, "") : "";
  const complexity = str(claim.complexity, "");
  const severityLevel = str(claim.severity, "");
  const coverageConfirmed = findings
    ? str(findings.coverage_confirmed, "").toLowerCase().startsWith("y")
    : !statusLower.includes("reject");

  const lc = (v: string) => v.toLowerCase();
  const eligibilityRules =
    loss || rec || stp || findings
      ? [
          { label: "STP_Score \u2265 85", pass: readiness !== null && readiness >= 85 },
          { label: "Fraud Low", pass: lc(fraudLevel) === "low" },
          { label: "Coverage Confirmed", pass: coverageConfirmed },
          { label: "Subrogation \u2260 High", pass: subrogationRisk !== "" && lc(subrogationRisk) !== "high" },
          {
            label: "Severity \u2264 Medium",
            pass: ["low", "minor", "medium", "moderate"].includes(lc(severityLevel)),
          },
          {
            label: "Complexity \u2264 Moderate",
            pass: ["simple", "low", "medium", "moderate"].includes(lc(complexity)),
          },
        ]
      : [];

  const analysis =
    loss || rec
      ? {
          estimatedLoss: loss ? num(loss.ai_estimated_loss) : null,
          // Deductible Applied → loss_assessments.deductible
          deductibleApplied: assess && assess.deductible != null ? num(assess.deductible) : null,
          // Net Payable Amount → loss_estimation_outputs.net_payable
          netPayable: loss && loss.net_payable != null ? num(loss.net_payable) : null,
          // Reserve Recommendation → adjuster_findings.system_recommended_reserve
          reserveRecommendation:
            findings && findings.system_recommended_reserve != null
              ? num(findings.system_recommended_reserve)
              : null,
          // Repair vs Replace → repair_vs_replacement_decisions.recommended_action
          repairRecommended: rvr ? str(rvr.recommended_action, "") : "",
          stpReadiness: readiness,
          stpCategory,
          fraudRiskLevel: fraudLevel,
          fraudRiskScore: fraudScore,
          subrogationRisk,
          complexity,
          severity: severityLevel,
          eligibilityRules,
          recommendation: rec ? str(rec.recommended_action, "") : "",
          confidence: rec
            ? Math.round(num(rec.confidence) * 100)
            : loss
              ? Math.round(num(loss.confidence) * 100)
              : null,
        }
      : null;

  // System Recommendation → repair_vs_replacement_decisions.recommended_action
  // (per spec), falling back to loss_assessments.system_recommendation only
  // when the claim has no repair-vs-replacement row. The adjuster's saved
  // decision is exposed separately as finalDecision for the Final
  // Recommendation field.
  const rvrRecommended = rvr ? str(rvr.recommended_action, "") : "";
  const systemRecommendation =
    rvrRecommended || (assess ? str(assess.system_recommendation, "") : "");
  const finalDecision = rvr ? str(rvr.decision, "") : "";

  sendJson(res, 200, {
    analysis,
    systemRecommendation,
    finalDecision,
    reserve: findings
      ? {
          systemRecommendedReserve:
            findings.system_recommended_reserve != null
              ? num(findings.system_recommended_reserve)
              : null,
          adjustedReserve:
            findings.adjusted_reserve != null ? num(findings.adjusted_reserve) : null,
        }
      : null,
    // Settlement Recommendation → ai_decision_recommendations
    // (settlement_amount, net_payable, remaining_coverage_limit,
    // final_settlement_amount) + loss_assessments.deductible.
    settlement:
      rec || assess
        ? {
            recommendedSettlement:
              rec && rec.settlement_amount != null ? num(rec.settlement_amount) : null,
            netPayable: rec && rec.net_payable != null ? num(rec.net_payable) : null,
            // Deductible Applied → loss_assessments.deductible
            deductible: assess && assess.deductible != null ? num(assess.deductible) : null,
            remainingCoverageLimit:
              rec && rec.remaining_coverage_limit != null
                ? num(rec.remaining_coverage_limit)
                : null,
            // Final Settlement (Adjuster) → ai_decision_recommendations.final_settlement_amount
            finalSettlement:
              rec && rec.final_settlement_amount != null && str(rec.final_settlement_amount, "") !== ""
                ? num(rec.final_settlement_amount)
                : null,
          }
        : null,
    // Financial Leakage → financial_leakage_score (per spec 2026-07-22):
    // leakage_risk, leakage_score, overall_variance_percent,
    // total_estimated_cost, total_actual_cost, recommendation.
    leakage: leakage
      ? {
          totalEstimatedCost: leakage.total_estimated_cost != null ? num(leakage.total_estimated_cost) : null,
          totalActualCost: leakage.total_actual_cost != null ? num(leakage.total_actual_cost) : null,
          overallVariancePercent:
            leakage.overall_variance_percent != null ? num(leakage.overall_variance_percent) : null,
          leakageScore: leakage.leakage_score != null ? num(leakage.leakage_score) : null,
          leakageRisk: str(leakage.leakage_risk, ""),
          riskFlags: Array.isArray(leakage.risk_flags) ? leakage.risk_flags : [],
          recommendation: str(leakage.recommendation, ""),
          adjusterRiskOverride: str(leakage.adjuster_override_risk_level, ""),
          adjusterNotes: str(leakage.adjuster_notes, ""),
        }
      : null,
    claim: {
      claimNumber: str(claim.claim_number),
      customerName: str(claim.policyholder_name),
      policyNumber: str(claim.policy_number),
      policyType: policy ? str(policy.coverage_type, "Home") : "Home",
      status: str(claim.status),
      severity: str(claim.severity),
      lossType: str(claim.loss_type),
      lossDate: str(claim.date_of_loss, formatDate(claim.filed_at) ?? "—"),
      description: str(claim.short_description),
      coverageLimit: policy ? num(policy.coverage_limit) : null,
      remainingCoverageLimit: policy ? num(policy.remaining_coverage_limit) : null,
      deductible: policy
        ? num(policy.deductible)
        : assess
          ? num(assess.deductible)
          : null,
    },
    damages,
    damageTotal,
    assessment: assess
      ? {
          assessmentId: str(assess.assessment_id),
          partsCost: num(assess.total_parts_cost),
          laborCost: num(assess.total_labor_cost),
          depreciationPercent: num(assess.depreciation_percent),
          deductible: num(assess.deductible),
          subrogationLikelihood: str(assess.subrogation_likelihood),
          // Same sourcing as the top-level systemRecommendation above.
          systemRecommendation: rvrRecommended || str(assess.system_recommendation, ""),
          adjusterOverride: str(assess.adjuster_override, ""),
          finalRecommendation: str(assess.final_recommendation, ""),
          notes: str(assess.notes, ""),
          confidence: Math.round(num(assess.confidence_score) * 100),
          date: str(assess.assessment_date),
        }
      : null,
    decision: {
      reviewComplete,
      coverageStatus: str(claim.status).toLowerCase().includes("reject") ? "Denied" : "Confirmed",
      fraudIndicator: null as string | null,
      stpClassification: null as string | null,
      estSettlement,
      recommendedAction: rec ? str(rec.recommended_action, "") : "",
      confidence: rec ? Math.round(num(rec.confidence) * 100) : loss ? Math.round(num(loss.confidence) * 100) : null,
      repairRecommended: loss ? str(loss.repair_recommended, "") : "",
    },
  });
}

async function handleRepairVsReplacement(db: pg.Pool, res: ServerResponse, claimNumber: string) {
  const claimR = await db.query(
    `SELECT claim_number, policyholder_name, loss_type, status, severity, short_description
     FROM claims WHERE claim_number = $1 LIMIT 1`,
    [claimNumber]
  );
  if (claimR.rows.length === 0) {
    sendJson(res, 404, { error: "Claim not found" });
    return;
  }
  const claim = claimR.rows[0] as Row;
  const like = `DMG-${claimNumber}-%`;

  const [repairR, replaceR, lossR, fraudR, benchR] = await Promise.all([
    db.query(
      `SELECT item_id, item_type, material_cost, labor_hours, labor_rate, diagnostic_fee,
              urgency_factor, total_repair_estimate
       FROM repair_costs WHERE item_id LIKE $1 ORDER BY id`,
      [like]
    ),
    db.query(
      `SELECT item_id, item_type, replacement_material_cost, installation_hours, labor_rate,
              delivery_fee, disposal_fee, total_replacement_estimate
       FROM replacement_costs WHERE item_id LIKE $1 ORDER BY id`,
      [like]
    ),
    db.query(
      `SELECT ai_estimated_loss, deductible, net_payable, repair_recommended, confidence
       FROM loss_estimation_outputs WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT fraud_score, red_flag_count FROM fraud_risk_snapshots
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT vendor_name, specialty, avg_repair_cost, avg_replacement_cost, eta_days
       FROM vendor_benchmarks ORDER BY id`
    ),
  ]);

  const repairItems = (repairR.rows as Row[]).map((r) => ({
    itemId: str(r.item_id),
    itemType: str(r.item_type),
    materialCost: num(r.material_cost),
    laborHours: num(r.labor_hours),
    laborRate: num(r.labor_rate),
    diagnosticFee: num(r.diagnostic_fee),
    total: num(r.total_repair_estimate),
  }));
  const replaceItems = (replaceR.rows as Row[]).map((r) => ({
    itemId: str(r.item_id),
    itemType: str(r.item_type),
    materialCost: num(r.replacement_material_cost),
    installHours: num(r.installation_hours),
    laborRate: num(r.labor_rate),
    deliveryFee: num(r.delivery_fee),
    disposalFee: num(r.disposal_fee),
    total: num(r.total_replacement_estimate),
  }));

  const repairTotal = repairItems.reduce((a, r) => a + r.total, 0);
  const replaceTotal = replaceItems.reduce((a, r) => a + r.total, 0);
  const repairMaterial = repairItems.reduce((a, r) => a + r.materialCost, 0);
  const repairLabor = repairItems.reduce((a, r) => a + r.laborHours * r.laborRate, 0);
  const replaceMaterial = replaceItems.reduce((a, r) => a + r.materialCost, 0);
  const replaceInstall = replaceItems.reduce((a, r) => a + r.installHours * r.laborRate, 0);
  const repairDays = Math.max(1, Math.round(repairItems.reduce((a, r) => a + r.laborHours, 0) / 8));
  const replaceDays = Math.max(
    repairDays,
    Math.round(replaceItems.reduce((a, r) => a + r.installHours, 0) / 8) + 2
  );

  const loss = lossR.rows[0] as Row | undefined;
  const fraud = fraudR.rows[0] as Row | undefined;
  const specialty = specialtyForLossType(str(claim.loss_type, ""));
  const bench = (benchR.rows as Row[]).find((b) => str(b.specialty) === specialty) ??
    (benchR.rows[0] as Row | undefined);

  const recommendation =
    loss && str(loss.repair_recommended).toLowerCase() === "no" ? "Replacement" : "Repair";
  const confidence = loss ? Math.round(num(loss.confidence) * 100) : null;
  const fraudScore = fraud ? num(fraud.fraud_score) : 0;
  const fraudLevel = fraudScore >= 70 ? "High" : fraudScore >= 40 ? "Medium" : "Low";
  const costRatio = replaceTotal > 0 ? Math.round((repairTotal / replaceTotal) * 100) : null;

  const hasData = repairItems.length > 0 || replaceItems.length > 0;

  sendJson(res, 200, {
    claim: {
      claimNumber: str(claim.claim_number),
      policyholder: str(claim.policyholder_name),
      lossType: str(claim.loss_type),
      status: str(claim.status),
      severity: str(claim.severity),
      fraudLevel,
    },
    hasData,
    comparison: {
      repair: { total: repairTotal, material: repairMaterial, labor: repairLabor, days: repairDays, items: repairItems },
      replacement: { total: replaceTotal, material: replaceMaterial, install: replaceInstall, days: replaceDays, items: replaceItems },
    },
    recommendation: { action: recommendation, confidence },
    explainability: {
      costRatio,
      benchmark: bench
        ? {
            vendorName: str(bench.vendor_name),
            avgRepair: num(bench.avg_repair_cost),
            avgReplacement: num(bench.avg_replacement_cost),
            etaDays: num(bench.eta_days),
          }
        : null,
      fraudScore,
      fraudLevel,
      netPayable: loss ? num(loss.net_payable) : null,
      deductible: loss ? Math.round(num(loss.deductible)) : null,
    },
  });
}

async function handleVendorMatch(db: pg.Pool, res: ServerResponse, claimNumber: string) {
  const [vendorsR, benchR, claimR, fraudR] = await Promise.all([
    db.query(
      `SELECT name, specialty, license_number, license_valid, rating, completed_jobs,
              avg_turnaround_days, avg_cost, city, state, phone, verified
       FROM vendors ORDER BY rating DESC`
    ),
    db.query(`SELECT vendor_name, fraud_score, eta_days FROM vendor_benchmarks`),
    claimNumber
      ? db.query(
          `SELECT claim_number, policyholder_name, loss_type, severity, status
           FROM claims WHERE claim_number = $1 LIMIT 1`,
          [claimNumber]
        )
      : Promise.resolve({ rows: [] as Row[] }),
    claimNumber
      ? db.query(
          `SELECT fraud_score FROM fraud_risk_snapshots WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
          [claimNumber]
        )
      : Promise.resolve({ rows: [] as Row[] }),
  ]);

  const benchBy = new Map(
    (benchR.rows as Row[]).map((b) => [str(b.vendor_name), b])
  );
  const claim = (claimR.rows[0] as Row) || null;
  const requiredSpecialty = claim ? specialtyForLossType(str(claim.loss_type, "")) : null;

  const vendors = (vendorsR.rows as Row[]).map((v) => {
    const bench = benchBy.get(str(v.name));
    const rating = num(v.rating);
    const jobs = num(v.completed_jobs);
    const turnaround = num(v.avg_turnaround_days);
    const fraudScore = bench ? num(bench.fraud_score) : 0.05;
    // 9-factor style VIS score (0-100): specialty match, license, rating,
    // capacity (jobs), SLA (turnaround), fraud/subrogation risk.
    let score = 0;
    score += rating * 12; // up to 60
    score += v.license_valid === true ? 12 : 0;
    score += Math.min(10, jobs / 25);
    score += Math.max(0, 10 - turnaround); // faster is better
    score -= fraudScore * 40;
    if (requiredSpecialty && str(v.specialty) === requiredSpecialty) score += 12;
    const vis = Math.max(40, Math.min(99, Math.round(score)));
    return {
      name: str(v.name),
      specialty: str(v.specialty),
      licenseNumber: str(v.license_number),
      licenseValid: v.license_valid === true,
      rating,
      completedJobs: jobs,
      avgTurnaroundDays: turnaround,
      avgCost: num(v.avg_cost),
      city: str(v.city),
      state: str(v.state),
      phone: str(v.phone),
      verified: v.verified === true,
      fraudScore,
      visScore: vis,
      specialtyMatch: requiredSpecialty ? str(v.specialty) === requiredSpecialty : false,
    };
  });

  vendors.sort((a, b) => b.visScore - a.visScore);
  const recommended =
    vendors.find((v) => v.specialtyMatch) ?? vendors[0] ?? null;

  const claimFraud = (fraudR.rows[0] as Row | undefined)
    ? num((fraudR.rows[0] as Row).fraud_score)
    : 0;

  sendJson(res, 200, {
    claim: claim
      ? {
          claimNumber: str(claim.claim_number),
          policyholder: str(claim.policyholder_name),
          lossType: str(claim.loss_type),
          severity: str(claim.severity),
          requiredSpecialty,
          subrogationPotential: claimFraud >= 40 ? "High" : claimFraud >= 20 ? "Medium" : "Low",
        }
      : null,
    stats: {
      totalVendors: vendors.length,
      licenseVerified: vendors.filter((v) => v.licenseValid).length,
      avgRating:
        vendors.length > 0
          ? Math.round((vendors.reduce((a, v) => a + v.rating, 0) / vendors.length) * 10) / 10
          : 0,
      avgTurnaroundDays:
        vendors.length > 0
          ? Math.round(vendors.reduce((a, v) => a + v.avgTurnaroundDays, 0) / vendors.length)
          : 0,
      totalJobs: vendors.reduce((a, v) => a + v.completedJobs, 0),
      stpReady: vendors.filter((v) => v.licenseValid && v.verified).length,
    },
    recommended,
    vendors,
  });
}

async function handleVerification(db: pg.Pool, res: ServerResponse, claimNumber: string) {
  const claimR = await db.query(
    `SELECT claim_number, policyholder_name, loss_type, location, severity, status
     FROM claims WHERE claim_number = $1 LIMIT 1`,
    [claimNumber]
  );
  if (claimR.rows.length === 0) {
    sendJson(res, 404, { error: "Claim not found" });
    return;
  }
  const claim = claimR.rows[0] as Row;

  const [photosR, droneR, weatherR, fraudR, authenticityR] = await Promise.all([
    db.query(
      `SELECT document_id, file_name, uploaded_at, uploaded_by_role, content_type
       FROM documents
       WHERE claim_number = $1 AND content_type LIKE 'image/%'
       ORDER BY uploaded_at DESC LIMIT 12`,
      [claimNumber]
    ),
    db.query(
      `SELECT drone_capture_time, roof_condition_rating, weather_event_alignment,
              damage_match_percent, manipulation_flags, drone_notes
       FROM drone_evidence_summary WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT storm_event, event_time, zip_code_severity_index, drone_weather_alignment
       FROM weather_location_alignment WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT fraud_score, red_flag_count FROM fraud_risk_snapshots
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
    db.query(
      `SELECT roof_condition FROM drone_authenticity_data
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimNumber]
    ),
  ]);

  const drone = droneR.rows[0] as Row | undefined;
  const authenticity = authenticityR.rows[0] as Row | undefined;
  const weather = weatherR.rows[0] as Row | undefined;
  const fraud = fraudR.rows[0] as Row | undefined;
  const fraudScore = fraud ? num(fraud.fraud_score) : 0;

  sendJson(res, 200, {
    claim: {
      claimNumber: str(claim.claim_number),
      insuredName: str(claim.policyholder_name),
      lossType: str(claim.loss_type),
      location: str(claim.location).replace(/\n/g, ", "),
      severity: str(claim.severity),
      fraudRisk: fraudScore >= 70 ? "High" : fraudScore >= 40 ? "Medium" : "Low",
      fraudScore,
      redFlags: fraud ? num(fraud.red_flag_count) : 0,
    },
    customerImages: (photosR.rows as Row[]).map((p) => ({
      documentId: str(p.document_id),
      fileName: str(p.file_name),
      uploadedAt: formatDateTime(p.uploaded_at) ?? "—",
      uploadedByRole: str(p.uploaded_by_role),
      url: `/api/document-file?id=${encodeURIComponent(str(p.document_id, ""))}`,
    })),
    drone: drone
      ? {
          captureTime: formatDateTime(drone.drone_capture_time) ?? "—",
          roofCondition: str(drone.roof_condition_rating),
          weatherAlignment: str(drone.weather_event_alignment),
          damageMatchPercent: num(drone.damage_match_percent),
          siteCondition: authenticity ? str(authenticity.roof_condition) : "—",
          manipulationFlags: parseManipulationFlags(drone.manipulation_flags),
          notes: str(drone.drone_notes),
        }
      : null,
    weather: weather
      ? {
          stormEvent: str(weather.storm_event),
          eventTime: str(weather.event_time),
          severityIndex: str(weather.zip_code_severity_index),
          droneAlignment: str(weather.drone_weather_alignment),
        }
      : null,
  });
}

async function handleExpertDispatch(db: pg.Pool, res: ServerResponse) {
  const [claimsR, journeyR, workOrdersR, droneR, expertsR] = await Promise.all([
    db.query(
      `SELECT claim_number, policyholder_name, loss_type, severity, status, location, filed_at
       FROM claims ORDER BY filed_at DESC`
    ),
    db.query(
      `SELECT claim_number, overall_sla_status, expected_completion_date, current_stage_name
       FROM claim_journey_master`
    ),
    db.query(
      `SELECT work_order_id, claim_number, expert_name, expert_type, scheduled_date,
              status, priority, drone_required
       FROM work_orders ORDER BY created_at DESC LIMIT 25`
    ),
    db.query(`SELECT DISTINCT claim_id FROM drone_evidence_summary`),
    db.query(
      `SELECT name, expert_type, rating, completed_jobs, city, state, active
       FROM experts WHERE active IS TRUE ORDER BY rating DESC LIMIT 10`
    ),
  ]);

  const journeyBy = new Map(
    (journeyR.rows as Row[]).map((j) => [String(j.claim_number), j])
  );
  const droneClaims = new Set((droneR.rows as Row[]).map((d) => String(d.claim_id)));
  const now = new Date();

  const queue = (claimsR.rows as Row[]).map((c) => {
    const key = String(c.claim_number);
    const journey = journeyBy.get(key);
    const slaStatus = journey ? str(journey.overall_sla_status, "") : "";
    const filed = c.filed_at ? new Date(String(c.filed_at)) : null;
    const ageDays = filed ? daysBetween(filed, now) : 0;
    const slaBreached = slaStatus.toLowerCase().includes("breach") || ageDays > 7;
    return {
      claimNumber: key,
      policyholder: str(c.policyholder_name),
      lossType: str(c.loss_type),
      severity: str(c.severity),
      status: str(c.status),
      location: str(c.location).replace(/\n/g, ", "),
      recommendedSpecialty: specialtyForLossType(str(c.loss_type, "")),
      slaBreached,
      ageDays,
      droneAvailable: droneClaims.has(key),
      stage: journey ? str(journey.current_stage_name, "") : "",
    };
  });

  const workOrders = (workOrdersR.rows as Row[]).map((w) => ({
    workOrderId: str(w.work_order_id),
    claimNumber: str(w.claim_number),
    expertName: str(w.expert_name),
    expertType: str(w.expert_type),
    scheduledDate: formatDate(w.scheduled_date) ?? "—",
    status: str(w.status),
    priority: str(w.priority),
    droneRequired: w.drone_required === true,
  }));

  sendJson(res, 200, {
    stats: {
      pendingDispatches: workOrders.filter((w) =>
        ["pending", "scheduled"].includes(w.status.toLowerCase())
      ).length,
      overdueVisits: queue.filter((q) => q.slaBreached).length,
      droneComboRequests: queue.filter((q) => q.droneAvailable).length,
    },
    queue,
    workOrders,
    experts: (expertsR.rows as Row[]).map((e) => ({
      name: str(e.name),
      expertType: str(e.expert_type),
      rating: num(e.rating),
      completedJobs: num(e.completed_jobs),
      city: str(e.city),
      state: str(e.state),
    })),
  });
}

async function handleCaseInvestigation(db: pg.Pool, res: ServerResponse, claimNumber: string) {
  const claimR = await db.query(
    `SELECT id, claim_number, policyholder_name, loss_type, severity, status, location,
            estimated_cost, filed_at, date_of_loss, short_description
     FROM claims WHERE claim_number = $1 LIMIT 1`,
    [claimNumber]
  );
  if (claimR.rows.length === 0) {
    sendJson(res, 404, { error: "Claim not found" });
    return;
  }
  const claim = claimR.rows[0] as Row;
  // Canonical claim key resolved from the claims row. Child tables reference the
  // claim by its business number: their `claim_id` / `claim_number` columns and
  // the `VER-<claimNumber>-...` verification_id prefix all hold this value.
  const claimId = str(claim.claim_number);
  // Exception: `estimates.claim_id` (written by RepairVsReplacementAgent's
  // compare_repair_vs_replace via get_claim_id()) stores the internal numeric
  // claims.id PK, not the business claim_number text every other table here
  // uses — confirmed against live data (e.g. claim_number "CLM-2026-7002" →
  // claims.id 79 → estimates rows with claim_id=79, not "CLM-2026-7002").
  const numericClaimId = claim.id as number;

  const [
    photosR, recAllR, journeyAllR, fraudAllR, claimsAllR,
    aiFraudR, damageItemR, weatherR, triageR, verifCriticalR,
    evidenceStatusR, lossEstimationR, estimateR, intakeValidationR,
    investigationCompletionR,
  ] = await Promise.all([
    db.query(
      `SELECT document_id, file_name, uploaded_at
       FROM documents
       WHERE claim_number = $1 AND content_type LIKE 'image/%'
       ORDER BY uploaded_at ASC LIMIT 12`,
      [claimNumber]
    ),
    db.query(
      `SELECT DISTINCT ON (claim_id) claim_id, settlement_amount, net_payable
       FROM ai_decision_recommendations ORDER BY claim_id, id DESC`
    ),
    db.query(
      `SELECT claim_number, total_days_in_journey FROM claim_journey_master`
    ),
    db.query(
      `SELECT DISTINCT ON (claim_id) claim_id, fraud_score
       FROM fraud_risk_snapshots ORDER BY claim_id, id DESC`
    ),
    db.query(
      `SELECT claim_number, loss_type, severity, status, estimated_cost, filed_at
       FROM claims WHERE claim_number <> $1 ORDER BY filed_at DESC`,
      [claimNumber]
    ),
    // AI Investigation Tool sources, keyed by the resolved claim key.
    db.query(
      `SELECT fraud_score FROM ai_fraud_signals
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimId]
    ),
    db.query(
      `SELECT severity FROM damage_items
       WHERE claim_number = $1 ORDER BY id DESC LIMIT 1`,
      [claimId]
    ),
    db.query(
      `SELECT storm_event FROM weather_location_alignment
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimId]
    ),
    db.query(
      `SELECT complexity, routing, fraud_risk_score FROM claim_triage
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimId]
    ),
    // Critical-severity checks (policy_exists, policy_status, date_of_loss_in_policy_window)
    // from the MOST RECENT verification run only — mirrors run_verification()'s own
    // coverage_verdict logic (any non-Match Critical check => "Flagged").
    db.query(
      `SELECT flag FROM verification_details
       WHERE verification_id = (
         SELECT verification_id FROM external_verifications
         WHERE claim_id = $1 ORDER BY id DESC LIMIT 1
       )
       AND severity = 'Critical'`,
      [claimId]
    ),
    // Evidence validation now reads from `documents` (evidence_items is seed-data-only
    // and never populated by real claims — see evidence_validation_mcp/handler.py's
    // get_evidence_items docstring). flagged/investigation_notes are the same columns
    // AdjusterAgents' evidence-validation pipeline writes to via save_validation_result.
    db.query(
      `SELECT
         COUNT(*)::int AS total,
         COUNT(*) FILTER (WHERE flagged = 1)::int AS flagged_count,
         COUNT(*) FILTER (WHERE COALESCE(flagged, 0) = 0 AND investigation_notes IS NOT NULL)::int AS verified_count
       FROM documents
       WHERE claim_number = $1`,
      [claimId]
    ),
    db.query(
      `SELECT ai_estimated_loss, net_payable FROM loss_estimation_outputs
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [claimId]
    ),
    db.query(
      `SELECT recommendation, repair_cost, replacement_cost, confidence_score FROM estimates
       WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
      [numericClaimId]
    ),
    // Complete Claim Intake Validation button — EvidenceValidationAgent's
    // 7-mandatory-field completeness check (_check_claim_data_completeness),
    // persisted automatically by run_evidence_validation via
    // _persist_intake_validation. Deliberately NOT PolicyholderAgents' own
    // intake_validation_result_output (that's the policyholder's FNOL-time
    // check, a different signal) — see claim_intake_validation_check memory.
    db.query(
      `SELECT data_completeness_score, validation_passed, blocking_failure,
              failure_reasons, overridden, overridden_by, overridden_notes
       FROM claim_intake_validation WHERE claim_id = $1`,
      [claimId]
    ),
    // Complete Investigation button — plain manual sign-off, gated on
    // Complete Claim Intake Validation being done first (see
    // /complete-investigation below for the server-side enforcement).
    db.query(
      `SELECT completed_by, completed_at FROM claim_investigation_completion WHERE claim_id = $1`,
      [claimId]
    ),
  ]);

  const aiFraud = aiFraudR.rows[0] as Row | undefined;
  const damageItem = damageItemR.rows[0] as Row | undefined;
  const weather = weatherR.rows[0] as Row | undefined;
  const triage = triageR.rows[0] as Row | undefined;
  const evidenceStatusRow = evidenceStatusR.rows[0] as Row | undefined;
  const lossEstimation = lossEstimationR.rows[0] as Row | undefined;
  const estimate = estimateR.rows[0] as Row | undefined;
  const intakeValidationRow = intakeValidationR.rows[0] as Row | undefined;

  // "Complete Claim Intake Validation" button state. "NotRun" means
  // run_evidence_validation hasn't executed for this claim yet — the button
  // should stay disabled rather than offering an override with nothing to
  // override. "Complete" covers both a genuine pass (validation_passed) and
  // an adjuster override; failureReasons/score reflect the last real check
  // either way, since overriding doesn't erase what the check found.
  const intakeValidationPassed = intakeValidationRow ? Boolean(intakeValidationRow.validation_passed) : false;
  const intakeValidationOverridden = intakeValidationRow ? Boolean(intakeValidationRow.overridden) : false;
  const intakeValidation = {
    status: !intakeValidationRow ? "NotRun" : intakeValidationPassed || intakeValidationOverridden ? "Complete" : "Incomplete",
    completenessScore: intakeValidationRow ? num(intakeValidationRow.data_completeness_score) : null,
    blockingFailure: intakeValidationRow ? Boolean(intakeValidationRow.blocking_failure) : false,
    failureReasons: intakeValidationRow?.failure_reasons
      ? (typeof intakeValidationRow.failure_reasons === "string"
          ? JSON.parse(intakeValidationRow.failure_reasons)
          : intakeValidationRow.failure_reasons)
      : [],
    overridden: intakeValidationOverridden,
    overriddenBy: intakeValidationRow ? str(intakeValidationRow.overridden_by, "") : "",
    overriddenNotes: intakeValidationRow ? str(intakeValidationRow.overridden_notes, "") : "",
  };

  // "Complete Investigation" — presence of a row IS the completed flag.
  const investigationCompletionRow = investigationCompletionR.rows[0] as Row | undefined;
  const investigationCompletion = {
    completed: Boolean(investigationCompletionRow),
    completedBy: investigationCompletionRow ? str(investigationCompletionRow.completed_by, "") : "",
    completedAt: investigationCompletionRow ? str(investigationCompletionRow.completed_at, "") : "",
  };

  // Coverage verdict, derived the same way run_verification() computes it:
  // any Critical check not a clean "Match" => Flagged. No rows at all means
  // VerificationAgent hasn't run yet for this claim.
  const criticalFlags = (verifCriticalR.rows as Row[]).map((r) => str(r.flag));
  const coverageVerdict =
    criticalFlags.length === 0 ? "" : criticalFlags.every((f) => f === "Match") ? "Confirmed" : "Flagged";

  // Evidence validation summary from documents.flagged/investigation_notes
  // (save_validation_result updates these directly; it doesn't persist its own
  // overall_status anywhere). A document with investigation_notes still NULL
  // hasn't been through run_evidence_validation/save_validation_result yet —
  // "not flagged" is NOT the same as "verified", so this must be checked
  // explicitly rather than assumed as the fallback case.
  const flaggedCount = num(evidenceStatusRow?.flagged_count ?? 0);
  const verifiedCount = num(evidenceStatusRow?.verified_count ?? 0);
  const totalEvidenceItems = num(evidenceStatusRow?.total ?? 0);
  const evidenceSummary =
    totalEvidenceItems === 0
      ? ""
      : flaggedCount > 0
        ? `${flaggedCount} of ${totalEvidenceItems} item(s) flagged`
        : verifiedCount === totalEvidenceItems
          ? `All ${totalEvidenceItems} item(s) verified`
          : `${totalEvidenceItems} item(s) uploaded — validation not yet run`;

  // --- AI Investigation Tool outputs (sourced directly from claim tables) ---
  const sevLower = str(claim.severity).toLowerCase();
  const filedAt = claim.filed_at ? new Date(String(claim.filed_at)) : null;

  // --- Smart Comparison: similar historical claims ---
  const recBy = new Map((recAllR.rows as Row[]).map((r) => [String(r.claim_id), r]));
  const journeyBy = new Map((journeyAllR.rows as Row[]).map((j) => [String(j.claim_number), j]));
  const fraudBy = new Map((fraudAllR.rows as Row[]).map((f) => [String(f.claim_id), f]));

  const myCost = num(claim.estimated_cost);
  const myMonth = filedAt ? filedAt.getMonth() : -1;

  const scored = (claimsAllR.rows as Row[]).map((c) => {
    const key = String(c.claim_number);
    const rec = recBy.get(key);
    const journey = journeyBy.get(key);
    const cf = fraudBy.get(key);
    const cost = num(c.estimated_cost);
    const statusLower = str(c.status).toLowerCase();
    const approved = statusLower.includes("approved") || statusLower.includes("payment") ||
      statusLower.includes("closed") || statusLower.includes("settled");
    const denied = statusLower.includes("reject") || statusLower.includes("denied");
    const days = journey ? num(journey.total_days_in_journey) : 0;
    const cFiled = c.filed_at ? new Date(String(c.filed_at)) : null;

    const sameLossType = str(c.loss_type) === str(claim.loss_type);
    const sameSeverity = str(c.severity).toLowerCase() === sevLower;
    const amountClose = myCost > 0 && cost > 0 && Math.abs(cost - myCost) / myCost <= 0.35;
    const quickSettlement = approved && days > 0 && days <= 14;
    const seasonal = myMonth >= 0 && cFiled !== null && cFiled.getMonth() === myMonth;

    let score = 52;
    if (sameLossType) score += 28;
    if (sameSeverity) score += 8;
    if (amountClose) score += 7;
    if (quickSettlement) score += 2;
    if (seasonal) score += 2;
    score = Math.max(50, Math.min(97, score));

    const factors: string[] = [];
    if (sameLossType) factors.push("Loss Type");
    if (amountClose) factors.push("Claim Amount Range");
    if (sameSeverity) factors.push("Damage Pattern");
    if (seasonal) factors.push("Seasonal Pattern");
    if (quickSettlement) factors.push("Quick Settlement Pattern");
    if (factors.length === 0) factors.push("Historical Profile");

    const rawSettlement = rec ? num(rec.settlement_amount) : 0;
    const settlement = denied ? 0 : rawSettlement > 0 ? rawSettlement : approved && cost > 0 ? cost : 0;
    const cFraud = cf ? num(cf.fraud_score) : 0;

    return {
      claimNumber: key,
      matchScore: score,
      claimAmount: cost,
      settlement,
      outcome: denied ? "Denied - Policy Exclusion" : approved
        ? (quickSettlement ? "Approved - Fast Track" : settlement > 0 && cost > 0 && settlement < cost * 0.85 ? "Approved - Negotiated" : "Approved - Full Payment")
        : "Partial Approval",
      outcomeTone: denied ? "red" : approved ? "green" : "orange",
      days,
      fraudRisk: cFraud >= 70 ? "High" : cFraud >= 40 ? "Medium" : "Low",
      matchingFactors: factors,
      approved,
      denied,
    };
  });

  scored.sort((a, b) => b.matchScore - a.matchScore);
  const similar = scored.slice(0, 5);

  const settled = similar.filter((s) => s.settlement > 0);
  const avgSettlement = settled.length
    ? Math.round(settled.reduce((a, s) => a + s.settlement, 0) / settled.length)
    : 0;
  const resolved = similar.filter((s) => s.days > 0);
  const avgResolutionDays = resolved.length
    ? Math.round(resolved.reduce((a, s) => a + s.days, 0) / resolved.length)
    : 0;
  const approvalRate = similar.length
    ? Math.round((similar.filter((s) => s.approved).length / similar.length) * 100)
    : 0;

  sendJson(res, 200, {
    claim: {
      claimNumber: str(claim.claim_number),
      policyholder: str(claim.policyholder_name),
      lossType: str(claim.loss_type),
      severity: str(claim.severity),
      status: str(claim.status),
      location: str(claim.location).replace(/\n/g, ", "),
    },
    evidencePhotos: (photosR.rows as Row[]).map((p) => ({
      documentId: str(p.document_id),
      fileName: str(p.file_name),
      url: `/api/document-file?id=${encodeURIComponent(str(p.document_id, ""))}`,
    })),
    intakeValidation,
    investigationCompletion,
    tools: {
      fraudScore: aiFraud ? num(aiFraud.fraud_score) : null,
      damageSeverity: damageItem ? str(damageItem.severity) : "",
      stormEvent: weather ? str(weather.storm_event) : "",
      coverageVerdict,
      claimComplexity: triage ? str(triage.complexity) : "",
      evidenceSummary,
      triageFraudRiskScore: triage && triage.fraud_risk_score !== null ? num(triage.fraud_risk_score) : null,
      routing: triage ? str(triage.routing) : "",
      lossNetPayable: lossEstimation ? num(lossEstimation.net_payable) : null,
      lossEstimatedTotal: lossEstimation ? num(lossEstimation.ai_estimated_loss) : null,
      repairVsReplaceRecommendation: estimate ? str(estimate.recommendation) : "",
      repairCost: estimate ? num(estimate.repair_cost) : null,
      replacementCost: estimate ? num(estimate.replacement_cost) : null,
    },
    comparison: {
      similarClaims: similar.map(({ approved, denied, ...rest }) => rest),
      stats: {
        similarCount: similar.length,
        avgApprovalRate: approvalRate,
        avgSettlement,
        avgResolutionDays,
      },
      insights: {
        settlementLow: avgSettlement > 0 ? Math.round(avgSettlement * 0.85) : 0,
        settlementHigh: avgSettlement > 0 ? Math.round(avgSettlement * 1.15) : 0,
        resolutionDays: avgResolutionDays,
        approvalRate,
      },
    },
  });
}

function readBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > 1_000_000) reject(new Error("Body too large"));
    });
    req.on("end", () => {
      try {
        resolve(raw ? (JSON.parse(raw) as Record<string, unknown>) : {});
      } catch {
        reject(new Error("Invalid JSON body"));
      }
    });
    req.on("error", reject);
  });
}

// Write the final recommendation into repair_vs_replacement_decisions.decision
// for the claim's latest row (claim_id holds the claim NUMBER). Returns whether
// a row was updated.
interface RepairDecisionResult {
  updated: boolean;
  reason?: string;
}

async function updateRepairDecision(
  db: pg.Pool,
  claimNumber: string,
  finalRec: string
): Promise<RepairDecisionResult> {
  if (!finalRec) return { updated: false };

  // Per spec, the adjuster's Final Recommendation is persisted verbatim into
  // repair_vs_replacement_decisions.decision (normalizing plain
  // repair/replace variants to their canonical casing).
  const value = normalizeRepairReplace(finalRec) ?? finalRec.trim();

  const r = await db.query(
    `UPDATE repair_vs_replacement_decisions SET decision = $2
     WHERE id = (SELECT id FROM repair_vs_replacement_decisions
                 WHERE claim_id = $1 ORDER BY id DESC LIMIT 1)`,
    [claimNumber, value]
  );
  if ((r.rowCount ?? 0) === 0) {
    return {
      updated: false,
      reason: "not recorded on the Repair vs Replace decision — no repair-vs-replace analysis has been run for this claim yet",
    };
  }
  return { updated: true };
}

async function handleSaveLossAssessment(
  db: pg.Pool,
  req: IncomingMessage,
  res: ServerResponse,
  claimNumber: string
) {
  const body = await readBody(req);
  const override = typeof body.adjusterOverride === "string" ? body.adjusterOverride.trim() : "";
  const notes = typeof body.notes === "string" ? body.notes.trim() : "";
  if (!override && !notes) {
    sendJson(res, 400, { error: "Nothing to save" });
    return;
  }

  const existing = await db.query(
    `SELECT id, system_recommendation FROM loss_assessments
     WHERE claim_number = $1 ORDER BY id DESC LIMIT 1`,
    [claimNumber]
  );
  if (existing.rows.length === 0) {
    const finalRec = override && !/^accept/i.test(override) ? override : "Pending AI analysis";
    await db.query(
      `INSERT INTO loss_assessments
         (assessment_id, claim_number, total_parts_cost, total_labor_cost,
          depreciation_percent, deductible, subrogation_likelihood,
          system_recommendation, adjuster_override, final_recommendation,
          confidence_score, notes, assessment_date)
       VALUES ($1, $2, 0, 0, 0, 0, 'Unknown', '', $3, $4, 0, $5, $6)`,
      [
        `LA-${claimNumber}-${Date.now()}`,
        claimNumber,
        override || "Accept System Recommendation",
        finalRec,
        notes,
        new Date().toISOString().slice(0, 10),
      ]
    );
    const repairDecision = await updateRepairDecision(db, claimNumber, finalRec);
    sendJson(res, 200, {
      saved: true,
      finalRecommendation: finalRec,
      decisionUpdated: repairDecision.updated,
      decisionNote: repairDecision.reason,
    });
    return;
  }
  const row = existing.rows[0] as Row;
  // System Recommendation is sourced from repair_vs_replacement_decisions
  // (recommended_action), falling back to loss_assessments.system_recommendation,
  // matching what the UI displays.
  const rvrR = await db.query(
    `SELECT recommended_action FROM repair_vs_replacement_decisions
     WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
    [claimNumber]
  );
  const rvrRec = rvrR.rows.length > 0 ? str((rvrR.rows[0] as Row).recommended_action, "") : "";
  const systemRec = rvrRec || str(row.system_recommendation, "");
  const finalRec =
    override && !/^accept/i.test(override) ? override : systemRec;

  await db.query(
    `UPDATE loss_assessments
     SET adjuster_override = $2, final_recommendation = $3, notes = $4
     WHERE id = $1`,
    [row.id, override || "Accept System Recommendation", finalRec, notes]
  );

  const repairDecision = await updateRepairDecision(db, claimNumber, finalRec);
  sendJson(res, 200, {
    saved: true,
    finalRecommendation: finalRec,
    decisionUpdated: repairDecision.updated,
    decisionNote: repairDecision.reason,
  });
}

// Writes an outbound, action-pending entry into communication_history so it
// surfaces in the policyholder's Follow My Claims "Latest Actions" box —
// same table/shape the PolicyholderAgents CommunicationAgent writes to, just
// invoked directly (no agent hop) the same way /save-reserve does above.
async function handleRequestAdditionalProof(
  db: pg.Pool,
  req: IncomingMessage,
  res: ServerResponse,
  claimNumber: string
) {
  const body = await readBody(req);
  const message = String(body.message ?? "").trim();
  if (!message) {
    sendJson(res, 400, { error: "A message describing the requested proof is required" });
    return;
  }

  const claimR = await db.query(
    `SELECT id, policyholder_name FROM claims WHERE claim_number = $1`,
    [claimNumber]
  );
  if (claimR.rows.length === 0) {
    sendJson(res, 404, { error: `Claim ${claimNumber} not found` });
    return;
  }
  const claimRow = claimR.rows[0] as Row;

  const communicationId = `COMM-PROOF-${claimNumber}-${Date.now()}`;
  await db.query(
    `INSERT INTO communication_history (
       communication_id, claim_row_id, claim_number, policyholder_name,
       communication_type, direction, subject, summary,
       handled_by, resolution_status, follow_up_required
     ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)`,
    [
      communicationId,
      claimRow.id,
      claimNumber,
      claimRow.policyholder_name,
      "Portal",
      "Outbound",
      "Additional Documentation Requested",
      message,
      "Adjuster",
      "Pending",
      true,
    ]
  );

  sendJson(res, 200, { sent: true, communicationId });
}

const INTERVIEW_MODES = new Set(["Video Call", "Phone Call"]);

// Same communication_history notification pattern as
// handleRequestAdditionalProof above, for the "Schedule Interview" action.
async function handleScheduleInterview(
  db: pg.Pool,
  req: IncomingMessage,
  res: ServerResponse,
  claimNumber: string
) {
  const body = await readBody(req);
  const mode = String(body.mode ?? "").trim();
  const dateLabel = String(body.dateLabel ?? "").trim();
  const time = String(body.time ?? "").trim();
  const notes = String(body.notes ?? "").trim();

  if (!INTERVIEW_MODES.has(mode)) {
    sendJson(res, 400, { error: "mode must be 'Video Call' or 'Phone Call'" });
    return;
  }
  if (!dateLabel || !time) {
    sendJson(res, 400, { error: "A date and time slot must be selected" });
    return;
  }

  const claimR = await db.query(
    `SELECT id, policyholder_name FROM claims WHERE claim_number = $1`,
    [claimNumber]
  );
  if (claimR.rows.length === 0) {
    sendJson(res, 404, { error: `Claim ${claimNumber} not found` });
    return;
  }
  const claimRow = claimR.rows[0] as Row;

  const summary = `Interview scheduled via ${mode} on ${dateLabel} at ${time}.${notes ? ` Notes: ${notes}` : ""}`;
  const communicationId = `COMM-INTERVIEW-${claimNumber}-${Date.now()}`;
  await db.query(
    `INSERT INTO communication_history (
       communication_id, claim_row_id, claim_number, policyholder_name,
       communication_type, direction, subject, summary,
       handled_by, resolution_status, follow_up_required
     ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)`,
    [
      communicationId,
      claimRow.id,
      claimNumber,
      claimRow.policyholder_name,
      "Portal",
      "Outbound",
      "Interview Scheduled",
      summary,
      "Adjuster",
      "Scheduled",
      true,
    ]
  );

  sendJson(res, 200, { sent: true, communicationId });
}

async function handleSaveReserve(
  db: pg.Pool,
  req: IncomingMessage,
  res: ServerResponse,
  claimNumber: string
) {
  const body = await readBody(req);
  const amount = Number(body.adjustedReserve);
  if (!Number.isFinite(amount) || amount < 0) {
    sendJson(res, 400, { error: "A valid adjustedReserve amount is required" });
    return;
  }

  // adjuster_findings.claim_id holds the claim NUMBER for this dataset.
  const existing = await db.query(
    `SELECT id FROM adjuster_findings WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
    [claimNumber]
  );
  if (existing.rows.length > 0) {
    await db.query(`UPDATE adjuster_findings SET adjusted_reserve = $2 WHERE id = $1`, [
      (existing.rows[0] as Row).id,
      amount,
    ]);
  } else {
    // adjuster_name/cause_of_loss/coverage_confirmed/fraud_risk/repair_vs_replace
    // are all NOT NULL with no default — this INSERT only runs when nothing
    // (not even recommend_reserve, which normally seeds this row first) has
    // touched adjuster_findings for this claim yet.
    await db.query(
      `INSERT INTO adjuster_findings
         (claim_id, adjuster_name, cause_of_loss, coverage_confirmed, fraud_risk, repair_vs_replace, adjusted_reserve)
       VALUES ($1, 'Adjuster', 'Unknown', 'Pending', 'Medium', 'TBD', $2)`,
      [claimNumber, amount]
    );
  }
  sendJson(res, 200, { saved: true, adjustedReserve: amount });
}

// Per spec, the adjuster's saved settlement is persisted into
// ai_decision_recommendations.final_settlement_amount for the claim's latest
// row. ai_decision_recommendations.settlement_amount stays untouched (that's
// the AI's own original recommendation).
async function handleSaveSettlement(
  db: pg.Pool,
  req: IncomingMessage,
  res: ServerResponse,
  claimNumber: string
) {
  const body = await readBody(req);
  const amount = Number(body.finalSettlement);
  if (!Number.isFinite(amount) || amount < 0) {
    sendJson(res, 400, { error: "A valid finalSettlement amount is required" });
    return;
  }

  const r = await db.query(
    `UPDATE ai_decision_recommendations SET final_settlement_amount = $2
     WHERE id = (SELECT id FROM ai_decision_recommendations
                 WHERE claim_id = $1 ORDER BY id DESC LIMIT 1)`,
    [claimNumber, String(amount)]
  );
  if ((r.rowCount ?? 0) === 0) {
    sendJson(res, 404, {
      error: "No AI decision recommendation exists for this claim yet — run the settlement analysis first",
    });
    return;
  }
  sendJson(res, 200, { saved: true, finalSettlement: amount });
}

// Unlike Reserve/Settlement, the adjuster's decision here has no home in
// adjuster_findings — it lives directly on the same financial_leakage_score
// row (adjuster_override_risk_level/adjuster_notes columns).
// No fallback INSERT: an override only makes sense once an analysis run
// actually exists for the claim.
async function handleSaveFinancialLeakage(
  db: pg.Pool,
  req: IncomingMessage,
  res: ServerResponse,
  claimNumber: string
) {
  const body = await readBody(req);
  const rawRisk = String(body.riskOverride ?? "").trim();
  const notes = String(body.notes ?? "").trim();

  let normalizedRisk: string | null = null;
  if (rawRisk) {
    normalizedRisk = normalizeLeakageRisk(rawRisk);
    if (!normalizedRisk) {
      sendJson(res, 400, { error: "riskOverride must be one of Low, Medium, High, Critical" });
      return;
    }
  }

  const existing = await db.query(
    `SELECT id FROM financial_leakage_score WHERE claim_id = $1 ORDER BY id DESC LIMIT 1`,
    [claimNumber]
  );
  if (existing.rows.length === 0) {
    sendJson(res, 404, {
      error: "No financial leakage analysis has been run for this claim yet — run the analysis before saving a decision.",
    });
    return;
  }

  await db.query(
    `UPDATE financial_leakage_score SET adjuster_override_risk_level = $2, adjuster_notes = $3 WHERE id = $1`,
    [(existing.rows[0] as Row).id, normalizedRisk, notes || null]
  );
  sendJson(res, 200, { saved: true, riskOverride: normalizedRisk, notes: notes || null });
}

// "Complete Claim Intake Validation" override — only meaningful when
// EvidenceValidationAgent's automated check (persisted to
// claim_intake_validation by run_evidence_validation) reported Incomplete.
// Requires a reason, matching every other adjuster override in this app
// (Repair vs Replace, Financial Leakage notes, Request Additional Proof).
// Updates claim_journey_master.sub_status only — NOT current_stage, which
// stays owned by Verification's coverage-confirmation trigger in
// AdjusterOrchestrator (a different check that runs earlier in the flow);
// see claim_journey_stage_wiring / claim_intake_validation_check memory.
async function handleOverrideIntakeValidation(
  db: pg.Pool,
  req: IncomingMessage,
  res: ServerResponse,
  claimNumber: string
) {
  const body = await readBody(req);
  const notes = String(body.notes ?? "").trim();
  const overriddenBy = String(body.overriddenBy ?? "adjuster_1").trim() || "adjuster_1";

  if (!notes) {
    sendJson(res, 400, { error: "A reason is required to override intake validation." });
    return;
  }

  const existing = await db.query(
    `SELECT id, validation_passed, overridden FROM claim_intake_validation WHERE claim_id = $1`,
    [claimNumber]
  );
  if (existing.rows.length === 0) {
    sendJson(res, 404, {
      error: "No intake validation check has been run for this claim yet — run the AI investigation first.",
    });
    return;
  }
  const row = existing.rows[0] as Row;
  if (row.validation_passed) {
    sendJson(res, 400, {
      error: "Intake validation already passed automatically — there is nothing to override.",
    });
    return;
  }

  await db.query(
    `UPDATE claim_intake_validation
     SET overridden = TRUE, overridden_by = $2, overridden_notes = $3, updated_at = NOW()
     WHERE id = $1`,
    [row.id, overriddenBy, notes]
  );

  // Best-effort journey note — never block the override on this.
  try {
    await db.query(
      `UPDATE claim_journey_master
       SET sub_status = $2, last_stage_change_date = NOW()
       WHERE claim_number = $1`,
      [claimNumber, `Claim intake validation manually overridden by ${overriddenBy}`]
    );
  } catch (err) {
    console.error("claim_journey_master sub_status update failed (non-fatal):", err);
  }

  sendJson(res, 200, { saved: true, overridden: true, overriddenBy, notes });
}

// "Complete Investigation" — plain manual sign-off, gated server-side (not
// just in the UI) on Complete Claim Intake Validation having already passed
// or been overridden. Idempotent: clicking twice just returns the original
// completed_by/completed_at rather than erroring or creating a second row.
async function handleCompleteInvestigation(
  db: pg.Pool,
  req: IncomingMessage,
  res: ServerResponse,
  claimNumber: string
) {
  const body = await readBody(req);
  const completedBy = String(body.completedBy ?? "adjuster_1").trim() || "adjuster_1";

  const intake = await db.query(
    `SELECT validation_passed, overridden FROM claim_intake_validation WHERE claim_id = $1`,
    [claimNumber]
  );
  const intakeRow = intake.rows[0] as Row | undefined;
  if (!intakeRow || !(intakeRow.validation_passed || intakeRow.overridden)) {
    sendJson(res, 400, {
      error: "Complete Claim Intake Validation before completing the investigation.",
    });
    return;
  }

  const existing = await db.query(
    `SELECT completed_by, completed_at FROM claim_investigation_completion WHERE claim_id = $1`,
    [claimNumber]
  );
  if (existing.rows.length > 0) {
    const row = existing.rows[0] as Row;
    sendJson(res, 200, {
      saved: true,
      completed: true,
      completedBy: str(row.completed_by, completedBy),
      completedAt: str(row.completed_at, ""),
      alreadyCompleted: true,
    });
    return;
  }

  const inserted = await db.query(
    `INSERT INTO claim_investigation_completion (claim_id, completed_by)
     VALUES ($1, $2)
     RETURNING completed_by, completed_at`,
    [claimNumber, completedBy]
  );
  const row = inserted.rows[0] as Row;
  sendJson(res, 200, {
    saved: true,
    completed: true,
    completedBy: str(row.completed_by, completedBy),
    completedAt: str(row.completed_at, ""),
    alreadyCompleted: false,
  });
}

// "Respond to Escalation" — Follow My Claims' Stage Actions panel. Same
// communication_history notification pattern as handleRequestAdditionalProof/
// handleScheduleInterview above; the policyholder's original concern/escalation
// (if any) is read client-side from claim.updates by ClaimJourneyWorkspace.tsx
// rather than looked up again here, since that endpoint (/api/claim-journey)
// already returns every communication_history row for the claim.
async function handleRespondToEscalation(
  db: pg.Pool,
  req: IncomingMessage,
  res: ServerResponse,
  claimNumber: string
) {
  const body = await readBody(req);
  const message = String(body.message ?? "").trim();
  if (!message) {
    sendJson(res, 400, { error: "A response message is required" });
    return;
  }

  const claimR = await db.query(
    `SELECT id, policyholder_name FROM claims WHERE claim_number = $1`,
    [claimNumber]
  );
  if (claimR.rows.length === 0) {
    sendJson(res, 404, { error: `Claim ${claimNumber} not found` });
    return;
  }
  const claimRow = claimR.rows[0] as Row;

  const communicationId = `COMM-ESCALATION-${claimNumber}-${Date.now()}`;
  await db.query(
    `INSERT INTO communication_history (
       communication_id, claim_row_id, claim_number, policyholder_name,
       communication_type, direction, subject, summary,
       handled_by, resolution_status, follow_up_required
     ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)`,
    [
      communicationId,
      claimRow.id,
      claimNumber,
      claimRow.policyholder_name,
      "Portal",
      "Outbound",
      "Escalation Response",
      message,
      "Adjuster",
      "Resolved",
      false,
    ]
  );

  sendJson(res, 200, { sent: true, communicationId });
}

export function adjusterApi(): Plugin {
  return {
    name: "adjuster-api",
    configureServer(server) {
      server.middlewares.use(
        "/api/adjuster",
        async (req: IncomingMessage, res: ServerResponse) => {
          const db = getPool();
          if (!db) {
            sendJson(res, 500, { error: "Database is not configured" });
            return;
          }
          const url = new URL(req.url ?? "/", "http://localhost");
          const route = url.pathname.replace(/\/+$/, "") || "/";
          const claimNumber = (url.searchParams.get("claimNumber") ?? "").trim();

          try {
            switch (route) {
              case "/dashboard":
                await handleDashboard(db, res);
                return;
              case "/investigation-queue":
                await handleInvestigationQueue(db, res);
                return;
              case "/loss-assessment":
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleLossAssessment(db, res, claimNumber);
                return;
              case "/repair-vs-replacement":
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleRepairVsReplacement(db, res, claimNumber);
                return;
              case "/vendor-match":
                await handleVendorMatch(db, res, claimNumber);
                return;
              case "/verification":
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleVerification(db, res, claimNumber);
                return;
              case "/expert-dispatch":
                await handleExpertDispatch(db, res);
                return;
              case "/save-loss-assessment":
                if (req.method !== "POST") {
                  sendJson(res, 405, { error: "POST required" });
                  return;
                }
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleSaveLossAssessment(db, req, res, claimNumber);
                return;
              case "/save-reserve":
                if (req.method !== "POST") {
                  sendJson(res, 405, { error: "POST required" });
                  return;
                }
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleSaveReserve(db, req, res, claimNumber);
                return;
              case "/save-settlement":
                if (req.method !== "POST") {
                  sendJson(res, 405, { error: "POST required" });
                  return;
                }
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleSaveSettlement(db, req, res, claimNumber);
                return;
              case "/save-financial-leakage":
                if (req.method !== "POST") {
                  sendJson(res, 405, { error: "POST required" });
                  return;
                }
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleSaveFinancialLeakage(db, req, res, claimNumber);
                return;
              case "/override-intake-validation":
                if (req.method !== "POST") {
                  sendJson(res, 405, { error: "POST required" });
                  return;
                }
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleOverrideIntakeValidation(db, req, res, claimNumber);
                return;
              case "/complete-investigation":
                if (req.method !== "POST") {
                  sendJson(res, 405, { error: "POST required" });
                  return;
                }
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleCompleteInvestigation(db, req, res, claimNumber);
                return;
              case "/request-additional-proof":
                if (req.method !== "POST") {
                  sendJson(res, 405, { error: "POST required" });
                  return;
                }
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleRequestAdditionalProof(db, req, res, claimNumber);
                return;
              case "/schedule-interview":
                if (req.method !== "POST") {
                  sendJson(res, 405, { error: "POST required" });
                  return;
                }
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleScheduleInterview(db, req, res, claimNumber);
                return;
              case "/respond-to-escalation":
                if (req.method !== "POST") {
                  sendJson(res, 405, { error: "POST required" });
                  return;
                }
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleRespondToEscalation(db, req, res, claimNumber);
                return;
              case "/case-investigation":
                if (!claimNumber) {
                  sendJson(res, 400, { error: "claimNumber is required" });
                  return;
                }
                await handleCaseInvestigation(db, res, claimNumber);
                return;
              default:
                sendJson(res, 404, { error: "Unknown adjuster endpoint" });
                return;
            }
          } catch (err) {
            console.error(`adjuster api error (${route}):`, err);
            sendJson(res, 500, { error: "Failed to load adjuster data" });
          }
        }
      );
    },
  };
}
