import type { Plugin } from "vite";
import { getPool, sendJson } from "./db";

export function voiceExtractionApi(): Plugin {
  return {
    name: "voice-extraction-api",
    configureServer(server) {
      server.middlewares.use("/api/voice-extraction", async (req, res) => {
        const reqUrl = new URL(req.url ?? "", "http://localhost");
        const policyNumber = (reqUrl.searchParams.get("policyNumber") ?? "").trim();
        const inputType = (reqUrl.searchParams.get("inputType") ?? "").trim();

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
          // Scope the extraction to the requesting policy by joining through the
          // submission that owns it (fnol_voice_text_extraction.fnol_id ->
          // fnol_submissions.id -> policy_number). inputType is an optional
          // filter (e.g. "voice" vs "text").
          const result = await db.query(
            `SELECT v.transcribed_text, v.raw_input, v.input_type,
                    v.extraction_confidence, v.created_at
             FROM fnol_voice_text_extraction v
             JOIN fnol_submissions f ON f.id = v.fnol_id
             WHERE f.policy_number = $1
               AND ($2 = '' OR v.input_type = $2)
             ORDER BY v.id DESC
             LIMIT 1`,
            [policyNumber, inputType]
          );

          if (result.rows.length === 0) {
            sendJson(res, 404, { error: "No voice extraction found" });
            return;
          }

          const row = result.rows[0] as Record<string, unknown>;
          const text =
            (row.transcribed_text as string | null) ||
            (row.raw_input as string | null) ||
            null;

          sendJson(res, 200, {
            text,
            inputType: row.input_type ?? null,
            confidence: row.extraction_confidence ?? null,
          });
        } catch (err) {
          console.error("voice-extraction lookup error:", err);
          sendJson(res, 500, { error: "Failed to load voice extraction" });
        }
      });
    },
  };
}
