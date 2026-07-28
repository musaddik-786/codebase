import type { Plugin } from "vite";
import { getPool, sendJson } from "./db";

export function claimInsightsApi(): Plugin {
  return {
    name: "claim-insights-api",
    configureServer(server) {
      server.middlewares.use("/api/claim-insights", async (req, res) => {
        const reqUrl = new URL(req.url ?? "", "http://localhost");
        const claimNumber = (reqUrl.searchParams.get("claimNumber") ?? "").trim();

        if (!claimNumber) {
          sendJson(res, 400, { error: "claimNumber is required" });
          return;
        }

        const db = getPool();
        if (!db) {
          sendJson(res, 500, { error: "Database not configured" });
          return;
        }

        try {
          const [readinessResult, stpResult, segResult, coverageResult, occupancyResult] = await Promise.all([
            db.query(
              `SELECT completeness_score, missing_fields, docs_status, missing_docs, overall_result
               FROM intake_validation_result_output WHERE claim_number = $1`,
              [claimNumber]
            ),
            db.query(
              `SELECT stp_category FROM stp_classification WHERE claim_number = $1`,
              [claimNumber]
            ),
            db.query(
              `SELECT severity, complexity FROM segmentation_result_output WHERE claim_number = $1`,
              [claimNumber]
            ),
            db.query(
              `SELECT coverage_verdict, net_payable, exclusion_triggered, exclusion_details
               FROM coverage_verification_results WHERE claim_number = $1`,
              [claimNumber]
            ),
            db.query(
              `SELECT f.occupancy_at_loss
               FROM claims cl
               LEFT JOIN LATERAL (
                 SELECT occupancy_at_loss FROM fnol_submissions
                 WHERE policy_number = cl.policy_number ORDER BY id DESC LIMIT 1
               ) f ON true
               WHERE cl.claim_number = $1 LIMIT 1`,
              [claimNumber]
            ),
          ]);

          const readiness = readinessResult.rows[0] as Record<string, unknown> | undefined;
          const stp = stpResult.rows[0] as Record<string, unknown> | undefined;
          const seg = segResult.rows[0] as Record<string, unknown> | undefined;
          const coverage = coverageResult.rows[0] as Record<string, unknown> | undefined;

          const parseCsv = (val: unknown): string[] | null => {
            if (!val || String(val).trim() === "") return null;
            const str = String(val).trim();
            if (str.startsWith("[")) {
              try {
                const parsed = JSON.parse(str);
                if (Array.isArray(parsed)) return (parsed as unknown[]).map(String).filter(Boolean);
              } catch {
                // fall through to comma split
              }
            }
            return str.split(",").map((s) => s.trim().replace(/^["'[\s]+|["'\]\s]+$/g, "")).filter(Boolean);
          };

          // "Occupancy at Loss" is an integer where 0 is a valid value. The
          // upstream missing_fields calc treats 0 as missing (falsy); correct
          // that here: only a NULL occupancy counts as missing, a 0 does not.
          const occupancyValue = (occupancyResult.rows[0] as Record<string, unknown> | undefined)?.occupancy_at_loss;
          const occupancyProvided = occupancyValue != null; // 0 is provided, NULL is not
          const rawMissingFields = readiness ? parseCsv(readiness.missing_fields) : null;
          const isOccupancyField = (f: string) =>
            f.replace(/[^a-z0-9]/gi, "").toLowerCase() === "occupancyatloss";
          let missingFields = rawMissingFields;
          if (missingFields && occupancyProvided) {
            missingFields = missingFields.filter((f) => !isOccupancyField(f));
            if (missingFields.length === 0) missingFields = null;
          }

          sendJson(res, 200, {
            completenessScore: readiness?.completeness_score != null
              ? Number(readiness.completeness_score) : null,
            missingFields,
            docsStatus: readiness?.docs_status ? String(readiness.docs_status) : null,
            missingDocs: readiness ? parseCsv(readiness.missing_docs) : null,
            overallResult: readiness?.overall_result ? String(readiness.overall_result) : null,
            stpCategory: stp?.stp_category ? String(stp.stp_category) : null,
            severity: seg?.severity ? String(seg.severity) : null,
            complexity: seg?.complexity ? String(seg.complexity) : null,
            coverageVerdict: coverage?.coverage_verdict ? String(coverage.coverage_verdict) : null,
            netPayable: coverage?.net_payable != null ? Number(coverage.net_payable) : null,
            exclusionTriggered: coverage ? Boolean(coverage.exclusion_triggered) : false,
            exclusionDetails: coverage?.exclusion_details ? String(coverage.exclusion_details) : null,
          });
        } catch (err) {
          console.error("claim-insights lookup error:", err);
          sendJson(res, 500, { error: "Failed to load claim insights" });
        }
      });
    },
  };
}
