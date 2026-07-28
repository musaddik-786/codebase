import type { Plugin } from "vite";
import { getPool, sendJson, formatDateTime } from "./db";

function categorize(documentType: unknown, contentType: unknown, fileName: unknown): string {
  const dt = String(documentType ?? "").toLowerCase();
  const ct = String(contentType ?? "").toLowerCase();
  const fn = String(fileName ?? "").toLowerCase();
  if (dt.includes("image") || ct.startsWith("image/")) return "Photos";
  if (dt.includes("invoice") || fn.includes("invoice") || fn.includes("receipt")) return "Invoices";
  if (dt.includes("estimate") || fn.includes("estimate") || fn.includes("quote")) return "Estimates";
  return "Reports";
}

export function documentsApi(): Plugin {
  return {
    name: "documents-api",
    configureServer(server) {
      // Distinct claim ids that have documents (for the claim selector).
      server.middlewares.use("/api/document-claims", async (_req, res) => {
        const db = getPool();
        if (!db) {
          sendJson(res, 500, { error: "Database is not configured" });
          return;
        }
        try {
          const result = await db.query(
            `SELECT c.claim_number AS claim_id,
                    c.policyholder_name,
                    c.loss_type,
                    COALESCE(d.doc_count, 0)::int AS doc_count
             FROM claims c
             LEFT JOIN (
               SELECT claim_number, COUNT(*)::int AS doc_count
               FROM documents
               WHERE claim_number IS NOT NULL
               GROUP BY claim_number
             ) d ON c.claim_number = d.claim_number
             ORDER BY c.filed_at DESC`
          );
          const claims = result.rows.map((r) => {
            const row = r as Record<string, unknown>;
            return {
              claimId: String(row.claim_id),
              docCount: Number(row.doc_count),
              policyholderName: row.policyholder_name ? String(row.policyholder_name) : null,
              lossType: row.loss_type ? String(row.loss_type) : null,
            };
          });
          sendJson(res, 200, { claims });
        } catch (err) {
          console.error("document-claims lookup error:", err);
          sendJson(res, 500, { error: "Failed to load document claims" });
        }
      });

      server.middlewares.use("/api/documents", async (req, res) => {
        const reqUrl = new URL(req.url ?? "", "http://localhost");
        const claimId = (reqUrl.searchParams.get("claimId") ?? "").trim();

        const db = getPool();
        if (!db) {
          sendJson(res, 500, { error: "Database is not configured" });
          return;
        }

        if (!claimId) {
          sendJson(res, 400, { error: "claimId is required" });
          return;
        }

        try {
          const result = await db.query(
            `SELECT document_id, claim_number, file_name, file_url, file_size,
                    content_type, document_type, classification_confidence,
                    uploaded_by_role, status, visibility, extracted_data,
                    insights, uploaded_at
             FROM documents
             WHERE claim_number = $1
             ORDER BY uploaded_at DESC`,
            [claimId]
          );

          const documents = result.rows.map((r) => {
            const row = r as Record<string, unknown>;
            const sizeBytes = Number(row.file_size ?? 0);
            return {
              id: String(row.document_id ?? row.file_name ?? Math.random()),
              name: String(row.file_name ?? "Untitled"),
              category: categorize(row.document_type, row.content_type, row.file_name),
              documentType: row.document_type ? String(row.document_type) : null,
              sizeKb: sizeBytes > 0 ? Math.max(1, Math.round(sizeBytes / 1024)) : 0,
              uploadedAt: formatDateTime(row.uploaded_at) ?? "—",
              uploadedAtIso: row.uploaded_at ? String(row.uploaded_at) : null,
              classificationConfidence:
                row.classification_confidence === null ||
                row.classification_confidence === undefined
                  ? null
                  : Number(row.classification_confidence),
              status: row.status ? String(row.status) : null,
              uploadedByRole: row.uploaded_by_role ? String(row.uploaded_by_role) : null,
              fileUrl: row.file_url ? String(row.file_url) : null,
              insights: row.insights ? String(row.insights) : null,
              extractedData: row.extracted_data ? String(row.extracted_data) : null,
            };
          });

          sendJson(res, 200, { claimId, documents });
        } catch (err) {
          console.error("documents lookup error:", err);
          sendJson(res, 500, { error: "Failed to load documents" });
        }
      });
    },
  };
}
