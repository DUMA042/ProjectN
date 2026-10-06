import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface SchemaColumn {
  name: string;
  type: string;
  nullable: boolean;
}

export interface SchemaTable {
  table: string;
  columns: SchemaColumn[];
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  ts: number;
  /** Real result rows (BLUE data answers only — rendered in a collapsible table). */
  rows?: Record<string, unknown>[];
  /** Column metadata for the rows table. */
  columns?: BlueAnswerColumn[];
  /** Total rows available server-side (may exceed rows shown). */
  row_count?: number;
  /** True when the server capped the result set. */
  truncated?: boolean;
  /** Answer provenance: data (from your data) vs general/placeholder guidance. */
  mode?: string;
}

/** Live database structure (names + types only — never row data). */
export function useDbSchema() {
  return useQuery<{ tables: SchemaTable[]; table_count: number }>({
    queryKey: ["db-schema"],
    queryFn: () => api.get("/api/schema").then((r) => r.data),
    staleTime: 300_000,
  });
}

/** Compact schema summary for prompts and the context strip. */
export function buildSchemaContext(tables: SchemaTable[]): string {
  if (!tables.length) return "No schema loaded.";
  const parts = tables.map(
    (t) => `${t.table}(${t.columns.map((c) => c.name).join(", ")})`
  );
  return `Database schema (${tables.length} tables): ` + parts.join(" · ");
}

/** Find which table(s) hold a column with this name (case-insensitive). */
export function tablesWithColumn(tables: SchemaTable[], column: string): string[] {
  const want = column.trim().toLowerCase();
  return tables
    .filter((t) => t.columns.some((c) => c.name.toLowerCase() === want))
    .map((t) => t.table);
}

/**
 * Live chat via the backend proxy (the DeepSeek key lives ONLY in the
 * server's local .env — it never reaches the frontend). Falls back to the
 * schema-aware placeholder below when the proxy is unreachable or AI is
 * not configured, so the chat UX stays usable offline.
 */
export async function sendChat(
  history: ChatMessage[],
  tables: SchemaTable[]
): Promise<string> {
  const payload = history
    .filter((m) => m.content.trim())
    .map((m) => ({ role: m.role, content: m.content.trim() }));
  try {
    const res = await api.post("/api/assistant/chat", { messages: payload });
    const reply = typeof res.data?.reply === "string" ? res.data.reply.trim() : "";
    if (reply) return reply;
  } catch (e: any) {
    const detail = e?.response?.data?.detail;
    // Server-mapped safe messages (e.g. not-configured, rate limits).
    if (typeof detail === "string" && detail.trim()) return detail.trim();
  }
  return placeholderReply(history, tables);
}

export interface BlueAnswerColumn {
  name: string;
  type: string;
}

export interface BlueAnswer {
  text: string;
  rows: Record<string, unknown>[];
  columns: BlueAnswerColumn[];
  row_count: number;
  truncated: boolean;
  mode: string;
}

/** Typed failure from the BLUE pipeline (status known — no masquerading). */
export class BlueAskError extends Error {
  status?: number;
  detail?: string;
  constructor(message: string, status?: number, detail?: string) {
    super(message);
    this.name = "BlueAskError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * BLUE Q&A: the user question reaches the model verbatim; real answers are
 * assembled server-side through the controlled query pipeline.
 */
export async function askBlue(question: string): Promise<BlueAnswer> {
  let res;
  try {
    res = await api.post("/api/blue/ask", { question });
  } catch (e: any) {
    const status: number | undefined = e?.response?.status;
    const detail = typeof e?.response?.data?.detail === "string" ? e.response.data.detail : undefined;
    // No HTTP response at all: backend unreachable (network/server down).
    if (status === undefined) throw new BlueAskError("unreachable", undefined, detail);
    throw new BlueAskError(detail || `request failed (${status})`, status, detail);
  }
  const d = (res as any).data || {};
  if (typeof d.answer !== "string" || !d.answer.trim()) {
    throw new BlueAskError("Empty answer", (res as any).status);
  }
  return {
    text: d.answer.trim(),
    rows: Array.isArray(d.rows) ? d.rows : [],
    columns: Array.isArray(d.columns) ? d.columns : [],
    row_count: typeof d.row_count === "number" ? d.row_count : 0,
    truncated: d.truncated === true,
    mode: typeof d.mode === "string" ? d.mode : "unsupported",
  };
}

/** Schema-aware canned logic (offline fallback + pre-AI stand-in). */
async function placeholderReply(
  history: ChatMessage[],
  tables: SchemaTable[]
): Promise<string> {
  // Simulated latency so thinking/typing states are exercisable.
  await new Promise((r) => setTimeout(r, 900));
  const last = [...history].reverse().find((m) => m.role === "user");
  const q = (last?.content || "").toLowerCase();

  const tableList = tables.map((t) => t.table).join(", ");
  const columnHit = (["phone_number", "full_name", "id_no", "attendance", "leave", "training", "token"] as const).find(
    (k) => q.includes(k.replace("_", " ")) || q.includes(k)
  );
  if (q.includes("what tables") || q.includes("list tables") || q.includes("schema")) {
    return tables.length
      ? `I can see ${tables.length} tables: ${tableList}. Ask me where a specific column lives — e.g. “where are phone numbers stored?”`
      : "The schema hasn't loaded yet — try again in a moment.";
  }
  if (columnHit) {
    const holders = tablesWithColumn(tables, columnHit);
    if (!holders.length) return `I couldn't find a column matching “${columnHit}” in the current schema.`;
    return `“${columnHit}” lives in: ${holders.join(", ")}.`;
  }
  if (q.includes("phone")) {
    const holders = tablesWithColumn(tables, "phone_number");
    return holders.length
      ? `Phone numbers are stored in ${holders.join(", ")} (column phone_number). I can't see the numbers themselves — only the structure.`
      : "I couldn't find a phone number column in the current schema.";
  }
  if (q.includes("classif") || q.includes("absent") || q.includes("rule")) {
    return "Attendance classification (present / absent / leave / training / incomplete, early / normal / late) is computed by the rules engine over the attendance_daily fact table plus the working-hours, holidays, and eligible-statuses settings. Ask me which tables hold those inputs.";
  }
  if (q.includes("privacy") || q.includes("token") || q.includes("hash") || q.includes("anonym")) {
    return tables.some((t) => t.table === "privacy_tokens")
      ? "Anonymized sharing uses the privacy_tokens vault: random 32-character tokens map back to originals via the unhash endpoint. Ask me about its columns."
      : "I couldn't find the privacy vault tables in the current schema.";
  }
  return "I'm a stand-in for now — I can see the database structure but can't query data yet. Try “what tables exist?” or “where are phone numbers stored?” (DeepSeek wiring will replace me later.)";
}
