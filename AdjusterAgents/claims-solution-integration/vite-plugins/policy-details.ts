import type { Plugin } from "vite";
import { getPool, sendJson, formatDate } from "./db";

function buildAddress(row: Record<string, unknown>): string | null {
  if (row.policy_address) return String(row.policy_address);
  const parts = [row.city, row.state, row.postal_code, row.country]
    .filter((p) => p != null && String(p).trim() !== "")
    .map((p) => String(p).trim());
  return parts.length > 0 ? parts.join(", ") : null;
}

export function policyDetailsApi(): Plugin {
  return {
    name: "policy-details-api",
    configureServer(server) {
      server.middlewares.use("/api/policy-details", async (req, res) => {
        res.setHeader("Content-Type", "application/json");
        const reqUrl = new URL(req.url ?? "", "http://localhost");
        const policyNumber = (reqUrl.searchParams.get("policyNumber") ?? "").trim();

        if (!policyNumber) {
          res.statusCode = 400;
          res.end(JSON.stringify({ error: "policyNumber is required" }));
          return;
        }

        const db = getPool();
        if (!db) {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: "Database is not configured" }));
          return;
        }

        try {
          const result = await db.query(
            `SELECT policy_number, gw_policy_id, account_number, policyholder_name,
                    policy_address, city, state, postal_code, country,
                    effective_date, expiration_date
             FROM policy_details
             WHERE policy_number = $1 OR gw_policy_id = $1 OR account_number = $1
             ORDER BY id DESC
             LIMIT 1`,
            [policyNumber]
          );

          if (result.rows.length === 0) {
            res.statusCode = 404;
            res.end(JSON.stringify({ error: "Policy not found" }));
            return;
          }

          const row = result.rows[0] as Record<string, unknown>;
          const effective = formatDate(row.effective_date);
          const expiration = formatDate(row.expiration_date);
          const policyPeriod =
            effective || expiration
              ? `${effective ?? "—"} - ${expiration ?? "—"}`
              : null;

          res.statusCode = 200;
          res.end(
            JSON.stringify({
              policyNumber: row.policy_number ?? policyNumber,
              insuredName: row.policyholder_name ?? null,
              insuredAddress: buildAddress(row),
              policyPeriod,
            })
          );
        } catch (err) {
          console.error("policy-details lookup error:", err);
          res.statusCode = 500;
          res.end(JSON.stringify({ error: "Failed to look up policy details" }));
        }
      });
    },
  };
}
