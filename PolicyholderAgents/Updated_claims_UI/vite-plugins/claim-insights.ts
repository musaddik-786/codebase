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
          const [readinessResult, stpResult, segResult, coverageResult] = await Promise.all([
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

          sendJson(res, 200, {
            completenessScore: readiness?.completeness_score != null
              ? Number(readiness.completeness_score) : null,
            missingFields: readiness ? parseCsv(readiness.missing_fields) : null,
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
