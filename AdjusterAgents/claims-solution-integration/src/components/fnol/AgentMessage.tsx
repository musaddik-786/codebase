import type { ReactNode } from "react";

// ── inline renderer: handles **bold** and *italic* ──────────────────────────
function renderInline(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i} className="font-semibold text-gray-900">{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*"))
      return <em key={i}>{part.slice(1, -1)}</em>;
    return part;
  });
}

// ── normalise: insert newlines before numbered items that are run together ──
function normaliseText(raw: string): string {
  return raw
    .replace(/([^\n])(\s*)(\d+\.\s)/g, "$1\n$3")
    .replace(/(\d+\.[^?!.\n]*[?!.])([A-Z])/g, "$1\n\n$2")
    .replace(/([.!?])([A-Z][a-z])/g, "$1\n$2")
    .trim();
}

// ── table helpers ────────────────────────────────────────────────────────────
function isSeparatorRow(line: string) {
  return /^\s*\|[\s\-:|]+\|\s*$/.test(line);
}

function parseTableRow(line: string): string[] {
  return line.split("|").slice(1, -1).map((c) => c.trim());
}

function parseMarkdownTable(content: string): { headers: string[]; rows: string[][] } | null {
  const lines = content.split("\n").filter((l) => l.trim().startsWith("|"));
  if (lines.length < 2) return null;
  const headers = parseTableRow(lines[0]);
  if (!headers.length) return null;
  const dataLines = lines.slice(1).filter((l) => !isSeparatorRow(l));
  const rows = dataLines.map(parseTableRow);
  return { headers, rows };
}

// ── segment splitter: splits raw text into prose vs table segments ───────────
type Segment = { type: "text"; content: string } | { type: "table"; content: string };

function splitSegments(raw: string): Segment[] {
  // Split concatenated table rows (row-end | + row-start | with no newline)
  const withRowBreaks = raw.replace(/\|\|/g, "|\n|");

  // Split each input line so any prose-before-pipe gets its own line
  const allLines: string[] = [];
  for (const line of withRowBreaks.split("\n")) {
    if (!line.includes("|")) {
      allLines.push(line);
      continue;
    }
    if (line.trimStart().startsWith("|")) {
      allLines.push(line);
    } else {
      // prose runs up to the first |, table content starts there
      const pipeIdx = line.indexOf("|");
      const prose = line.slice(0, pipeIdx).trim();
      const tableStart = line.slice(pipeIdx);
      if (prose) allLines.push(prose);
      if (tableStart) allLines.push(tableStart);
    }
  }

  // Group consecutive lines by type
  const segments: Segment[] = [];
  let currentType: "text" | "table" | null = null;
  let buffer: string[] = [];

  for (const line of allLines) {
    const type: "text" | "table" = line.trimStart().startsWith("|") ? "table" : "text";
    if (type !== currentType) {
      if (buffer.length && currentType) {
        segments.push({ type: currentType, content: buffer.join("\n") });
        buffer = [];
      }
      currentType = type;
    }
    buffer.push(line);
  }
  if (buffer.length && currentType) {
    segments.push({ type: currentType, content: buffer.join("\n") });
  }
  return segments;
}

// ── block types (for prose segments) ────────────────────────────────────────
type Block =
  | { kind: "paragraph"; lines: string[] }
  | { kind: "ordered"; items: string[] }
  | { kind: "bullet"; items: string[] };

// Split prose into non-question sentences and question sentences so that
// follow-up questions can always be rendered as a numbered list, even when
// the assistant writes them inline in a paragraph.
function extractQuestions(lines: string[]): { prose: string[]; questions: string[] } {
  const text = lines.join(" ");
  const sentences = text.split(/(?<=[.!?])\s+/);
  const prose: string[] = [];
  const questions: string[] = [];
  for (const raw of sentences) {
    const s = raw.trim();
    if (!s) continue;
    if (s.endsWith("?")) questions.push(s);
    else prose.push(s);
  }
  return { prose: prose.length ? [prose.join(" ")] : [], questions };
}

// Push a paragraph, converting any question sentences into an ordered list so
// follow-up questions always appear in numbered (1., 2., ...) form.
function pushParagraph(blocks: Block[], lines: string[]) {
  if (!lines.length) return;
  const { prose, questions } = extractQuestions(lines);
  if (prose.length) blocks.push({ kind: "paragraph", lines: prose });
  if (questions.length) blocks.push({ kind: "ordered", items: questions });
}

function parseBlocks(text: string): Block[] {
  const normalised = normaliseText(text);
  const paragraphs = normalised.split(/\n{2,}/);
  const blocks: Block[] = [];

  for (const para of paragraphs) {
    const lines = para.split("\n").map((l) => l.trim()).filter(Boolean);
    if (!lines.length) continue;

    const orderedItems: string[] = [];
    const bulletItems: string[] = [];
    const plainLines: string[] = [];

    for (const line of lines) {
      const ol = line.match(/^\d+\.\s+(.+)/);
      const ul = line.match(/^[*\-•]\s+(.+)/);
      if (ol) orderedItems.push(ol[1]);
      else if (ul) bulletItems.push(ul[1]);
      else plainLines.push(line);
    }

    if (orderedItems.length || bulletItems.length) {
      pushParagraph(blocks, plainLines);
      if (orderedItems.length) blocks.push({ kind: "ordered", items: orderedItems });
      if (bulletItems.length) blocks.push({ kind: "bullet", items: bulletItems });
    } else {
      pushParagraph(blocks, plainLines);
    }
  }
  return blocks;
}

// ── main component ───────────────────────────────────────────────────────────
export function AgentMessage({ text }: { text: string }) {
  if (!text) return null;

  // Strip internal sentinels that should never be shown to users
  const cleaned = text.replace(/##CONTINUE##/g, "").replace(/\bFNOL ID:\s*\d+/g, "").trim();
  if (!cleaned) return null;

  const segments = splitSegments(cleaned);

  return (
    <div className="space-y-2.5 text-[13.5px] leading-relaxed">
      {segments.map((seg, si) => {
        if (seg.type === "table") {
          const table = parseMarkdownTable(seg.content);
          if (!table) return null;
          return (
            <div key={si} className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm my-2">
              <table className="w-full text-[13px] border-collapse">
                <thead>
                  <tr className="bg-blue-50">
                    {table.headers.map((h, j) => (
                      <th
                        key={j}
                        className="px-4 py-2.5 text-left text-gray-800 font-semibold border-b border-gray-200 whitespace-nowrap"
                      >
                        {renderInline(h)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((row, j) => (
                    <tr
                      key={j}
                      className={j % 2 === 0 ? "bg-white" : "bg-gray-50"}
                    >
                      {row.map((cell, k) => (
                        <td
                          key={k}
                          className="px-4 py-2 text-gray-700 border-b border-gray-100 last:border-b-0"
                        >
                          {renderInline(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        // prose segment
        const blocks = parseBlocks(seg.content);
        return blocks.map((block, bi) => {
          const key = `${si}-${bi}`;
          if (block.kind === "paragraph") {
            return (
              <p key={key} className="text-gray-700 leading-relaxed">
                {renderInline(block.lines.join(" "))}
              </p>
            );
          }
          if (block.kind === "ordered") {
            return (
              <ol key={key} className="space-y-2 mt-1">
                {block.items.map((item, j) => (
                  <li key={j} className="flex items-start gap-2.5">
                    <span className="flex-shrink-0 mt-0.5 h-5 w-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center shadow-sm">
                      {j + 1}
                    </span>
                    <span className="text-gray-700 pt-0.5">{renderInline(item)}</span>
                  </li>
                ))}
              </ol>
            );
          }
          // bullet
          return (
            <ul key={key} className="space-y-1.5 mt-1">
              {block.items.map((item, j) => (
                <li key={j} className="flex items-start gap-2.5">
                  <span className="flex-shrink-0 mt-1.5 h-1.5 w-1.5 rounded-full bg-blue-500" />
                  <span className="text-gray-700">{renderInline(item)}</span>
                </li>
              ))}
            </ul>
          );
        });
      })}
    </div>
  );
}
