import type { Plugin } from "vite";
import { getPool, sendJson, formatDate } from "./db";

export function claimsApi(): Plugin {
  return {
    name: "claims-api",
    configureServer(server) {
      server.middlewares.use("/api/claims", async (req, res) => {
        const db = getPool();
        if (!db) {
          sendJson(res, 500, { error: "Database is not configured" });
          return;
        }

        try {
          const result = await db.query(
            `SELECT claim_number, policyholder_name, policy_number, loss_type,
                    short_description, ai_generated_summary, detected_cause,
                    severity, estimated_cost, coverage, ai_confidence, status,
                    location, filed_at, date_of_loss
             FROM claims
             ORDER BY filed_at DESC`
          );

          const claims = result.rows.map((r) => {
            const row = r as Record<string, unknown>;
            const coverage =
              row.coverage === true
                ? "Covered"
                : row.coverage === false
                  ? "Under Review"
                  : "Under Review";
            return {
              id: String(row.claim_number ?? "—"),
              status: String(row.status ?? "—"),
              description: String(row.short_description ?? "—"),
              date: formatDate(row.filed_at) ?? "—",
              type: String(row.loss_type ?? "—"),
              location: row.location ? String(row.location) : "—",
              policyholder: String(row.policyholder_name ?? "—"),
              policyNumber: String(row.policy_number ?? "—"),
              dateFiled: formatDate(row.filed_at) ?? "—",
              dateOfLoss: row.date_of_loss ? String(row.date_of_loss) : "—",
              estimatedCost: row.estimated_cost ? String(row.estimated_cost) : "—",
              severity: String(row.severity ?? "—"),
              coverage,
              assessmentSummary:
                (row.ai_generated_summary as string | null) ||
                (row.short_description as string | null) ||
                "No assessment summary available yet.",
              aiConfidence:
                row.ai_confidence === null || row.ai_confidence === undefined
                  ? null
                  : Number(row.ai_confidence),
            };
          });

          sendJson(res, 200, { claims });
        } catch (err) {
          console.error("claims lookup error:", err);
          sendJson(res, 500, { error: "Failed to load claims" });
        }
      });
    },
  };
}
