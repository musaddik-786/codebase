import type { Plugin } from "vite";
import { getPool, sendJson, mapSource } from "./db";

type FieldDef = {
  field: string;
  valueCol: string;
  sourceCol: string | null;
  required: boolean;
  staticSource?: string;
};

const FIELD_DEFS: FieldDef[] = [
  { field: "Type of Loss", valueCol: "loss_type", sourceCol: "loss_type_source", required: true },
  { field: "Cause of Loss", valueCol: "cause_of_loss", sourceCol: "cause_of_loss_source", required: true },
  { field: "Area Affected", valueCol: "area_affected", sourceCol: "area_affected_source", required: true },
  { field: "Date of Loss", valueCol: "date_of_loss", sourceCol: "date_of_loss_source", required: true },
  { field: "Time of Loss", valueCol: "time_of_loss", sourceCol: "time_of_loss_source", required: false },
  { field: "Sudden vs Gradual", valueCol: "sudden_vs_gradual", sourceCol: "sudden_vs_gradual_source", required: true },
  { field: "Occupancy at Time of Loss", valueCol: "occupancy_at_loss", sourceCol: "occupancy_at_loss_source", required: true },
  { field: "Severity", valueCol: "severity", sourceCol: "severity_source", required: false },
  { field: "Emotional Context", valueCol: "emotional_context", sourceCol: "emotional_context_source", required: false },
  { field: "Urgency Indicator", valueCol: "urgency_indicator", sourceCol: "urgency_indicator_source", required: false },
  { field: "Estimated Damage Amount", valueCol: "estimated_cost", sourceCol: null, required: false, staticSource: "You Provided" },
];

export function fnolSubmissionApi(): Plugin {
  return {
    name: "fnol-submission-api",
    configureServer(server) {
      server.middlewares.use("/api/fnol-submission", async (req, res) => {
        const reqUrl = new URL(req.url ?? "", "http://localhost");
        const policyNumber = (reqUrl.searchParams.get("policyNumber") ?? "").trim();

        if (policyNumber === "") {
          sendJson(res, 400, { error: "policyNumber query parameter is required" });
          return;
        }

        const db = getPool();
        if (!db) {
          sendJson(res, 500, { error: "Database is not configured" });
          return;
        }

        try {
          const result = await db.query(
            `SELECT * FROM fnol_submissions
             WHERE policy_number = $1
             ORDER BY id DESC
             LIMIT 1`,
            [policyNumber]
          );

          if (result.rows.length === 0) {
            sendJson(res, 404, { error: "No FNOL submission found" });
            return;
          }

          const row = result.rows[0] as Record<string, unknown>;

          const fields = FIELD_DEFS.map((def) => {
            const raw = row[def.valueCol];
            const value =
              raw === null || raw === undefined || String(raw).trim() === ""
                ? null
                : String(raw);
            return {
              field: def.field,
              value,
              source: def.staticSource ?? (def.sourceCol ? mapSource(row[def.sourceCol]) : "AI-Inferred"),
              required: def.required,
            };
          });

          const overallConfidence =
            row.overall_confidence === null || row.overall_confidence === undefined
              ? null
              : Number(row.overall_confidence);

          sendJson(res, 200, {
            id: typeof row.id === "number" ? row.id : Number(row.id) || null,
            policyNumber: row.policy_number ?? null,
            fnolNumber: row.fnol_number ?? null,
            overallConfidence,
            confidenceNotes: row.confidence_notes ?? null,
            fields,
          });
        } catch (err) {
          console.error("fnol-submission lookup error:", err);
          sendJson(res, 500, { error: "Failed to load FNOL submission" });
        }
      });
    },
  };
}
