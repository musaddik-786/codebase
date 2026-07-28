import pg from "pg";
import type { ServerResponse } from "http";

let pool: pg.Pool | null = null;

export function getPool(): pg.Pool | null {
  if (pool) return pool;
  const connectionString = process.env.AZURE_DATABASE_URL;
  if (!connectionString) return null;
  pool = new pg.Pool({
    connectionString,
    ssl: { rejectUnauthorized: true },
    connectionTimeoutMillis: 10000,
    max: 5,
  });
  return pool;
}

export function sendJson(res: ServerResponse, status: number, body: unknown) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(body));
}

export function formatDate(value: unknown): string | null {
  if (!value) return null;
  const d = new Date(value as string);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
}

export function formatDateTime(value: unknown): string | null {
  if (!value) return null;
  const d = new Date(value as string);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const SOURCE_MAP: Record<string, string> = {
  ai_inferred:        "AI Extracted",
  voice_transcript:   "From Your Voice",
  text_input:         "From Description",
  customer_confirmed: "Confirmed by You",
  customer_provided:  "You Provided",
  guidewire_lookup:   "Policy Record",
  human_edited:       "Human Edited",
};

export function mapSource(value: unknown): string {
  if (typeof value === "string" && SOURCE_MAP[value]) return SOURCE_MAP[value];
  return "AI-Inferred";
}
