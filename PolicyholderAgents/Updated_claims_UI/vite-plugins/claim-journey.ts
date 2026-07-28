import type { Plugin } from "vite";
import { getPool, sendJson, formatDate, formatDateTime } from "./db";

const JOURNEY_STAGES = [
  "Claim Initiated",
  "Claim Intake Validation",
  "Segmentation & Triage",
  "Loss Investigation",
  "Loss Assessment",
  "Decision Pending",
  "Decision & Settlement",
  "Claim Closed",
];

function prettySla(value: unknown): string | null {
  if (typeof value !== "string" || value.trim() === "") return null;
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function truncate(value: unknown, max = 220): string | null {
  if (value === null || value === undefined) return null;
  const text = String(value).replace(/\s+/g, " ").trim();
  if (text === "") return null;
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export function claimJourneyApi(): Plugin {
  return {
    name: "claim-journey-api",
    configureServer(server) {
      server.middlewares.use("/api/claim-journey", async (req, res) => {
        const reqUrl = new URL(req.url ?? "", "http://localhost");
        const claimNumber = (reqUrl.searchParams.get("claimNumber") ?? "").trim();

        if (claimNumber === "") {
          sendJson(res, 400, { error: "claimNumber query parameter is required" });
          return;
        }

        const db = getPool();
        if (!db) {
          sendJson(res, 500, { error: "Database is not configured" });
          return;
        }

        try {
          const result = await db.query(
            `SELECT c.claim_number, c.status, c.policyholder_name, c.policy_number,
                    c.loss_type, c.date_of_loss,
                    j.current_stage, j.current_stage_name, j.sub_status,
                    j.overall_sla_status, j.expected_completion_date,
                    j.total_days_in_journey
             FROM claims c
             LEFT JOIN claim_journey_master j ON j.claim_id = c.id
             WHERE c.claim_number = $1
             LIMIT 1`,
            [claimNumber]
          );

          if (result.rows.length === 0) {
            sendJson(res, 404, { error: "Claim not found" });
            return;
          }

          const row = result.rows[0] as Record<string, unknown>;

          const total = JOURNEY_STAGES.length;
          const rawStage =
            row.current_stage === null || row.current_stage === undefined
              ? 1
              : Number(row.current_stage);
          const stageIndex = Math.min(Math.max(rawStage - 1, 0), total - 1);
          const currentStageName =
            (row.current_stage_name as string | null) || JOURNEY_STAGES[stageIndex];
          const subStatus = (row.sub_status as string | null) || null;
          const slaLabel = prettySla(row.overall_sla_status);

          const nextStageName =
            stageIndex < total - 1 ? JOURNEY_STAGES[stageIndex + 1] : null;

          const whatsHappeningNow = subStatus
            ? `Your claim is currently in the "${currentStageName}" stage (${subStatus}).`
            : `Your claim is currently in the "${currentStageName}" stage.`;

          const whatHappensNext = nextStageName
            ? `Your claim will advance to "${nextStageName}".`
            : "Your claim has reached its final stage. No further steps are required.";

          const nextStatusLabel =
            slaLabel ?? subStatus ?? (nextStageName ? "In Progress" : "Closed");

          const progress = Math.round((rawStage / total) * 100);

          const expectedCompletion = formatDate(row.expected_completion_date);
          const estCompletion = expectedCompletion ?? "To be determined";

          // Latest customer-facing update from communication history.
          const commResult = await db.query(
            `SELECT subject, summary, handled_by, communication_date
             FROM communication_history
             WHERE claim_number = $1
             ORDER BY communication_date DESC
             LIMIT 1`,
            [claimNumber]
          );

          let latestUpdate: {
            title: string;
            actor: string;
            detail: string;
            timestamp: string;
          } | null = null;

          if (commResult.rows.length > 0) {
            const comm = commResult.rows[0] as Record<string, unknown>;
            latestUpdate = {
              title: (comm.subject as string | null)?.trim() || "Claim Update",
              actor: (comm.handled_by as string | null)?.trim() || "Claims Team",
              detail:
                truncate(comm.summary) || "An update was recorded on your claim.",
              timestamp: formatDateTime(comm.communication_date) ?? "—",
            };
          }

          sendJson(res, 200, {
            id: String(row.claim_number ?? claimNumber),
            status: String(row.status ?? "—"),
            policyNumber: String(row.policy_number ?? "—"),
            policyholder: String(row.policyholder_name ?? "—"),
            type: String(row.loss_type ?? "—"),
            dateOfLoss: row.date_of_loss ? String(row.date_of_loss) : "—",
            stages: JOURNEY_STAGES,
            stageIndex,
            whatsHappeningNow,
            whatHappensNext,
            nextStatusLabel,
            latestUpdate,
            progress,
            estCompletion,
          });
        } catch (err) {
          console.error("claim-journey lookup error:", err);
          sendJson(res, 500, { error: "Failed to load claim journey" });
        }
      });
    },
  };
}
