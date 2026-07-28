import type { Plugin } from "vite";
import type { ServerResponse } from "http";
import { createHmac } from "crypto";
import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { getPool, sendJson, formatDateTime } from "./db";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// PolicyholderAgents' local-fallback upload directory (used when Azure Blob
// Storage is unreachable) — a sibling repo folder, three levels up from here.
const LOCAL_UPLOADS_DIR = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "PolicyholderAgents",
  "data",
  "uploads"
);

// Only trusts absolute paths that resolve inside LOCAL_UPLOADS_DIR — prevents
// this from becoming an arbitrary local-file-read endpoint via a crafted
// file_url value.
function resolveLocalUploadPath(fileUrl: string): string | null {
  if (!path.isAbsolute(fileUrl)) return null;
  const resolved = path.resolve(fileUrl);
  const relative = path.relative(LOCAL_UPLOADS_DIR, resolved);
  if (relative === "" || relative.startsWith("..") || path.isAbsolute(relative)) return null;
  return resolved;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function sendFileError(res: ServerResponse, status: number, title: string, detail: string) {
  const safeTitle = escapeHtml(title);
  const safeDetail = escapeHtml(detail);
  res.statusCode = status;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.end(`<!doctype html>
<html>
<head><meta charset="utf-8"><title>${safeTitle}</title></head>
<body style="font-family: system-ui, sans-serif; background: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0;">
  <div style="max-width: 420px; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px; text-align: center;">
    <div style="font-size: 32px; margin-bottom: 12px;">&#128196;</div>
    <h1 style="font-size: 18px; color: #0f172a; margin: 0 0 8px;">${safeTitle}</h1>
    <p style="font-size: 14px; color: #64748b; margin: 0;">${safeDetail}</p>
  </div>
</body>
</html>`);
}

// Only proxy files that live in Azure Blob Storage over HTTPS; anything else
// stored in file_url is rejected to prevent this endpoint becoming an SSRF sink.
function isAllowedFileUrl(rawUrl: string): boolean {
  try {
    const u = new URL(rawUrl);
    return u.protocol === "https:" && u.hostname.endsWith(".blob.core.windows.net");
  } catch {
    return false;
  }
}

// The AZURE_STORAGE_SAS secret may hold either a SAS token ("sv=...&sig=...")
// or a full storage connection string ("...AccountName=x;AccountKey=y;...").
// Both are supported: SAS tokens are appended to the blob URL, while account
// keys are used to sign requests with Azure Shared Key authorization.
type StorageCredential =
  | { kind: "sas"; token: string }
  | { kind: "key"; accountName: string; accountKey: string }
  | null;

function parseStorageCredential(raw: string): StorageCredential {
  const value = raw.trim();
  if (!value) return null;
  if (/accountkey=/i.test(value)) {
    const parts = new Map<string, string>();
    for (const segment of value.split(";")) {
      const idx = segment.indexOf("=");
      if (idx > 0) {
        parts.set(segment.slice(0, idx).trim().toLowerCase(), segment.slice(idx + 1).trim());
      }
    }
    const accountName = parts.get("accountname") ?? "";
    const accountKey = parts.get("accountkey") ?? "";
    if (accountName && accountKey) return { kind: "key", accountName, accountKey };
    return null;
  }
  return { kind: "sas", token: value.replace(/^\?/, "") };
}

function sharedKeyHeaders(
  method: string,
  url: URL,
  accountName: string,
  accountKey: string
): Record<string, string> {
  const xMsDate = new Date().toUTCString();
  const xMsVersion = "2021-08-06";
  const canonicalizedHeaders = `x-ms-date:${xMsDate}\nx-ms-version:${xMsVersion}`;
  const canonicalizedResource = `/${accountName}${url.pathname}`;
  const stringToSign = [
    method,
    "", // Content-Encoding
    "", // Content-Language
    "", // Content-Length (empty for 0)
    "", // Content-MD5
    "", // Content-Type
    "", // Date
    "", // If-Modified-Since
    "", // If-Match
    "", // If-None-Match
    "", // If-Unmodified-Since
    "", // Range
    canonicalizedHeaders,
    canonicalizedResource,
  ].join("\n");
  const signature = createHmac("sha256", Buffer.from(accountKey, "base64"))
    .update(stringToSign, "utf8")
    .digest("base64");
  return {
    "x-ms-date": xMsDate,
    "x-ms-version": xMsVersion,
    Authorization: `SharedKey ${accountName}:${signature}`,
  };
}

// Build a direct-to-Azure blob URL that a browser can open on its own.
// The container is private, so the URL must carry an access token:
//  - "sas"  credential → append the existing SAS token as-is.
//  - "key"  credential → mint a short-lived, read-only service SAS scoped to
//    this single blob (the account key never leaves the server).
// Returns null when no usable credential is available.
function buildDirectBlobUrl(fileUrl: string, credential: StorageCredential): string | null {
  if (!credential) return null;

  if (credential.kind === "sas") {
    // If the stored URL already has a query (its own SAS), leave it alone.
    return fileUrl.includes("?") ? fileUrl : `${fileUrl}?${credential.token}`;
  }

  // credential.kind === "key" → generate a service SAS for this blob.
  const url = new URL(fileUrl);
  const signedVersion = "2022-11-02";
  const signedResource = "b"; // blob
  const signedPermissions = "r"; // read only
  const fmt = (d: Date) => d.toISOString().replace(/\.\d+Z$/, "Z");
  // Start slightly in the past to tolerate clock skew; expire quickly.
  const signedStart = fmt(new Date(Date.now() - 5 * 60 * 1000));
  const signedExpiry = fmt(new Date(Date.now() + 10 * 60 * 1000));
  const signedProtocol = "https";
  const canonicalizedResource = `/blob/${credential.accountName}${decodeURIComponent(url.pathname)}`;
  const stringToSign = [
    signedPermissions,
    signedStart,
    signedExpiry,
    canonicalizedResource,
    "", // signedIdentifier
    "", // signedIP
    signedProtocol,
    signedVersion,
    signedResource,
    "", // signedSnapshotTime
    "", // signedEncryptionScope
    "", // rscc — Cache-Control
    "", // rscd — Content-Disposition
    "", // rsce — Content-Encoding
    "", // rscl — Content-Language
    "", // rsct — Content-Type
  ].join("\n");
  const signature = createHmac("sha256", Buffer.from(credential.accountKey, "base64"))
    .update(stringToSign, "utf8")
    .digest("base64");
  const params = new URLSearchParams({
    sv: signedVersion,
    sr: signedResource,
    sp: signedPermissions,
    st: signedStart,
    se: signedExpiry,
    spr: signedProtocol,
    sig: signature,
  });
  return `${url.origin}${url.pathname}?${params.toString()}`;
}

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

      // Streams the original document through the server so the browser gets
      // real file bytes (with a correct content type) instead of a raw XML
      // error page from blob storage.
      server.middlewares.use("/api/document-file", async (req, res) => {
        const reqUrl = new URL(req.url ?? "", "http://localhost");
        const id = (reqUrl.searchParams.get("id") ?? "").trim();

        const db = getPool();
        if (!db) {
          sendFileError(res, 500, "Service unavailable", "Database is not configured.");
          return;
        }
        if (!id) {
          sendFileError(res, 400, "Missing document", "No document id was provided.");
          return;
        }

        try {
          const result = await db.query(
            `SELECT file_name, file_url, content_type
             FROM documents
             WHERE document_id = $1
             LIMIT 1`,
            [id]
          );
          const row = result.rows[0] as Record<string, unknown> | undefined;
          const fileUrl = row?.file_url ? String(row.file_url) : "";
          if (!fileUrl) {
            sendFileError(
              res,
              404,
              "Document not found",
              "This document has no stored file to view."
            );
            return;
          }

          const fileName = String(row?.file_name ?? "document");

          if (!isAllowedFileUrl(fileUrl)) {
            // Not an Azure Blob URL — check whether it's a trusted local-fallback
            // path (used when Azure Blob Storage upload failed or wasn't
            // configured) before giving up.
            const localPath = resolveLocalUploadPath(fileUrl);
            if (!localPath) {
              sendFileError(
                res,
                404,
                "File unavailable",
                "This document's stored file location is not supported."
              );
              return;
            }
            try {
              const data = await fs.readFile(localPath);
              const contentType =
                (row?.content_type ? String(row.content_type) : "") ||
                "application/octet-stream";
              res.statusCode = 200;
              res.setHeader("Content-Type", contentType);
              res.setHeader(
                "Content-Disposition",
                `inline; filename="${fileName.replace(/[^\w.\- ]+/g, "_")}"`
              );
              res.setHeader("Content-Length", String(data.length));
              res.end(data);
            } catch (err) {
              console.error("local document read error:", err);
              sendFileError(
                res,
                404,
                "File unavailable",
                `The original file "${fileName}" could not be found on local storage.`
              );
            }
            return;
          }

          // Blob container is private; use the credential from AZURE_STORAGE_SAS
          // (either a SAS token or a connection string with an account key) so
          // the original file can actually be retrieved.
          const credential = parseStorageCredential(process.env.AZURE_STORAGE_SAS ?? "");
          let fetchUrl = fileUrl;
          let fetchHeaders: Record<string, string> | undefined;
          if (credential?.kind === "sas" && !fileUrl.includes("?")) {
            fetchUrl = `${fileUrl}?${credential.token}`;
          } else if (credential?.kind === "key") {
            fetchHeaders = sharedKeyHeaders(
              "GET",
              new URL(fileUrl),
              credential.accountName,
              credential.accountKey
            );
          }
          const upstream = await fetch(fetchUrl, { headers: fetchHeaders });
          if (!upstream.ok) {
            sendFileError(
              res,
              404,
              "File unavailable",
              `The original file "${fileName}" could not be retrieved from storage. It may have been moved or is no longer accessible.`
            );
            return;
          }

          const contentType =
            upstream.headers.get("content-type") ||
            (row?.content_type ? String(row.content_type) : "") ||
            "application/octet-stream";
          const body = Buffer.from(await upstream.arrayBuffer());
          res.statusCode = 200;
          res.setHeader("Content-Type", contentType);
          res.setHeader(
            "Content-Disposition",
            `inline; filename="${fileName.replace(/[^\w.\- ]+/g, "_")}"`
          );
          res.setHeader("Content-Length", String(body.length));
          res.end(body);
        } catch (err) {
          console.error("document-file proxy error:", err);
          sendFileError(
            res,
            502,
            "File unavailable",
            "The original file could not be retrieved from storage right now. Please try again later."
          );
        }
      });

      // Returns a direct-to-Azure blob URL (with a short-lived access token)
      // so the browser can open the original file straight from storage instead
      // of streaming it through /api/document-file. Falls back to an error the
      // client can handle (it then uses the proxy endpoint).
      server.middlewares.use("/api/document-file-url", async (req, res) => {
        const reqUrl = new URL(req.url ?? "", "http://localhost");
        const id = (reqUrl.searchParams.get("id") ?? "").trim();

        // Redirect the browser straight to a location that serves the file.
        // When we can mint a direct Azure link we send the tab there; otherwise
        // we fall back to the streaming proxy so the tab always ends up on the
        // real file (no intermediate blank page, no popup-blocker issues).
        const redirectTo = (location: string) => {
          res.statusCode = 302;
          res.setHeader("Location", location);
          res.setHeader("Cache-Control", "no-store");
          res.end();
        };
        const proxyUrl = `/api/document-file?id=${encodeURIComponent(id)}`;

        if (!id) {
          sendJson(res, 400, { error: "No document id was provided" });
          return;
        }

        const db = getPool();
        if (!db) {
          redirectTo(proxyUrl);
          return;
        }

        try {
          const result = await db.query(
            `SELECT file_url FROM documents WHERE document_id = $1 LIMIT 1`,
            [id]
          );
          const row = result.rows[0] as Record<string, unknown> | undefined;
          const fileUrl = row?.file_url ? String(row.file_url) : "";
          if (!fileUrl || !isAllowedFileUrl(fileUrl)) {
            redirectTo(proxyUrl);
            return;
          }

          const credential = parseStorageCredential(process.env.AZURE_STORAGE_SAS ?? "");
          const directUrl = buildDirectBlobUrl(fileUrl, credential);
          redirectTo(directUrl || proxyUrl);
        } catch (err) {
          console.error("document-file-url error:", err);
          redirectTo(proxyUrl);
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
                    insights, investigation_notes, uploaded_at
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
              investigationNotes: row.investigation_notes ? String(row.investigation_notes) : null,
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
