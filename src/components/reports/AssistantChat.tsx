import { useEffect, useRef, useState } from "react";
import { ArrowDown, Check, Copy, RotateCcw, SendHorizonal, Trash2 } from "lucide-react";
import {
  askBlue,
  BlueAskError,
  buildSchemaContext,
  sendChat,
  useDbSchema,
  type ChatMessage,
} from "@/lib/assistant";

const SUGGESTIONS = [
  "Who checked in earliest yesterday?",
  "Which staff are on leave today?",
  "Who is absent most this month?",
  "What is the late checkout time?",
];

function TypingDots() {
  return (
    <span className="flex items-center gap-1 py-1" aria-label="BLUE is thinking">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-text-muted animate-bounce"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  );
}

function timeOf(ts: number): string {
  return new Date(ts).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

/** Minimalist assistant panel: schema-aware chat, session-only history. */
export default function AssistantChat() {
  const schema = useDbSchema();
  const tables = schema.data?.tables || [];
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [showContext, setShowContext] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [stickBottom, setStickBottom] = useState(true);
  const idRef = useRef(1);
  const listRef = useRef<HTMLDivElement>(null);
  const areaRef = useRef<HTMLTextAreaElement>(null);

  // Keep the latest message in view unless the user scrolled up.
  useEffect(() => {
    const el = listRef.current;
    if (el && stickBottom) el.scrollTop = el.scrollHeight;
  }, [messages, thinking, stickBottom]);

  const onScrollList = () => {
    const el = listRef.current;
    if (!el) return;
    setStickBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 40);
  };

  const send = async (text: string) => {
    const content = text.trim();
    if (!content || thinking) return;
    setError(null);
    setConfirmClear(false);
    const userMsg: ChatMessage = { id: idRef.current++, role: "user", content, ts: Date.now() };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setThinking(true);
    setStickBottom(true);
    try {
      // BLUE query pipeline (user text reaches the model verbatim; the
      // database is only ever touched through the controlled query API).
      const blue = await askBlue(content);
      if (blue.mode === "error") {
        setError(blue.text);
      } else {
        setMessages((prev) => [
          ...prev,
          { id: idRef.current++, role: "assistant", content: blue.text, ts: Date.now(), rows: blue.rows, columns: blue.columns, row_count: blue.row_count, truncated: blue.truncated, mode: blue.mode },
        ]);
      }
    } catch (e) {
      // Pipeline failures (500/502/4xx) surface as an error with Retry —
      // never a fallback answer masquerading as success. The placeholder
      // path runs ONLY when the backend is unreachable or AI is unconfigured.
      const err = e as BlueAskError;
      const status = err?.status;
      const detail = typeof err?.detail === "string" ? err.detail : "";
      const notConfigured = status === 503 && /not configured/i.test(detail);
      if (status === undefined || notConfigured) {
        try {
          const reply = await sendChat(history, tables);
          setMessages((prev) => [...prev, { id: idRef.current++, role: "assistant", content: reply, ts: Date.now(), mode: "general" }]);
        } catch {
          setError("Something went wrong reaching BLUE.");
        }
      } else if (status === 400 && detail) {
        setError(detail);
      } else {
        setError("BLUE couldn't run that question just now. Retry, or try rephrasing it.");
      }
    } finally {
      setThinking(false);
    }
  };

  const copy = async (m: ChatMessage) => {
    try {
      await navigator.clipboard.writeText(m.content);
      setCopiedId(m.id);
      window.setTimeout(() => setCopiedId((v) => (v === m.id ? null : v)), 1200);
    } catch {
      /* clipboard unavailable */
    }
  };

  const clear = () => {
    if (!confirmClear) {
      setConfirmClear(true);
      window.setTimeout(() => setConfirmClear(false), 3000);
      return;
    }
    setMessages([]);
    setError(null);
    setConfirmClear(false);
  };

  const contextText = buildSchemaContext(tables);
  const rows = Math.min(5, Math.max(1, input.split("\n").length));

  return (
    <div className="card-container p-4 flex flex-col h-full min-h-[560px]">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-2 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="relative flex w-2.5 h-2.5 flex-shrink-0">
            <span className={`absolute inline-flex w-full h-full rounded-full ${thinking ? "animate-ping bg-accent opacity-60" : "bg-success opacity-60"}`} />
            <span className={`relative inline-flex w-2.5 h-2.5 rounded-full ${thinking ? "bg-accent" : "bg-success"}`} />
          </span>
          <h2 className="text-xs font-semibold text-text-primary">BLUE</h2>
          <span className="text-[11px] text-text-muted">{thinking ? "Thinking…" : "Ready"}</span>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <button
            onClick={() => setShowContext((v) => !v)}
            title="What the assistant can see"
            className="px-2 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary hover:bg-nav-hover transition-colors"
          >
            {schema.isLoading ? "Loading context…" : `${tables.length} tables in context`}
          </button>
          <button
            onClick={clear}
            title={confirmClear ? "Click again to confirm clear" : "Clear conversation"}
            aria-label="Clear conversation"
            className={`p-2 rounded-btn transition-colors ${
              confirmClear ? "text-danger bg-badge-red-bg" : "text-text-muted hover:text-danger hover:bg-nav-hover"
            }`}
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Context strip */}
      {showContext && (
        <div className="mb-2 max-h-32 overflow-y-auto rounded-btn bg-nav-hover/60 px-3 py-2 flex-shrink-0">
          <p className="text-[11px] text-text-secondary leading-relaxed">{contextText}</p>
          <p className="text-[10px] text-text-muted mt-1">Structure only — the assistant never sees row data or personal details.</p>
        </div>
      )}

      {/* Messages */}
      <div
        ref={listRef}
        onScroll={onScrollList}
        aria-live="polite"
        className="relative flex-1 min-h-0 overflow-y-auto space-y-3 pr-1"
      >
        {messages.length === 0 && !thinking && (
          <div className="h-full flex flex-col items-center justify-center text-center gap-3 py-10">
            <p className="text-sm font-medium text-text-primary">Ask BLUE about your data</p>
            <p className="text-xs text-text-muted max-w-[280px]">
              Real answers with names and figures — assembled on your server, never shown to the AI.
            </p>
            <div className="flex flex-wrap justify-center gap-1.5 mt-1">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => { void send(s); }}
                  className="px-2.5 py-1.5 text-[11px] border border-border rounded-full bg-surface text-text-secondary hover:border-accent/40 hover:text-accent transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-accent/10 px-3.5 py-2.5">
                <p className="text-[13px] text-text-primary leading-relaxed whitespace-pre-wrap">{m.content}</p>
                <p className="text-[10px] text-text-muted mt-1 text-right">{timeOf(m.ts)}</p>
              </div>
            </div>
          ) : (
            <div key={m.id} className="flex justify-start group">
              <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-nav-hover/70 px-3.5 py-2.5">
                {m.mode && (
                  <p className="mb-1">
                    <span
                      className={`inline-block text-[10px] font-medium px-1.5 py-px rounded-full ${
                        m.mode === "data"
                          ? "bg-badge-blue-bg text-badge-blue-text"
                          : "bg-nav-hover text-text-secondary"
                      }`}
                    >
                      {m.mode === "data" ? "answered from your data" : "general guidance"}
                    </span>
                  </p>
                )}
                <p className="text-[13px] text-text-primary leading-relaxed whitespace-pre-wrap">{m.content}</p>
                {m.rows && m.rows.length > 0 && (
                  <details className="mt-2">
                    <summary className="text-[11px] text-accent cursor-pointer hover:underline">
                      View {m.row_count || m.rows.length} row{(m.row_count || m.rows.length) === 1 ? "" : "s"}
                      {m.truncated ? " (capped)" : ""}
                    </summary>
                    <div className="mt-1.5 overflow-x-auto max-h-48 overflow-y-auto rounded-btn border border-border">
                      <table className="text-[11px] w-full">
                        <thead className="sticky top-0 bg-surface">
                          <tr>
                            {(m.columns && m.columns.length > 0
                              ? m.columns.map((c) => c.name)
                              : Object.keys(m.rows[0])
                            ).map((k) => (
                              <th key={k} className="px-2 py-1 text-left font-semibold text-text-secondary whitespace-nowrap border-b border-divider">
                                {k}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {m.rows.slice(0, 10).map((r, i) => (
                            <tr key={i} className="border-b border-divider last:border-0">
                              {(m.columns && m.columns.length > 0
                                ? m.columns.map((c) => c.name)
                                : Object.keys(m.rows![0])
                              ).map((k) => (
                                <td key={k} className="px-2 py-1 text-text-primary whitespace-nowrap">
                                  {String(r[k] ?? "")}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {m.truncated && (
                      <p className="text-[10px] text-text-muted mt-1">
                        Showing first {m.rows.length} of {m.row_count} rows — narrow filters or dates for the full set.
                      </p>
                    )}
                  </details>
                )}
                <p className="flex items-center justify-between mt-1">
                  <span className="text-[10px] text-text-muted">{timeOf(m.ts)}</span>
                  <button
                    onClick={() => { void copy(m); }}
                    title="Copy response"
                    aria-label="Copy response"
                    className="p-1 rounded text-text-muted opacity-0 group-hover:opacity-100 hover:text-text-primary transition-opacity"
                  >
                    {copiedId === m.id ? <Check size={12} /> : <Copy size={12} />}
                  </button>
                </p>
              </div>
            </div>
          )
        )}
        {thinking && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-md bg-nav-hover/70 px-3.5 py-2.5">
              <TypingDots />
            </div>
          </div>
        )}
        {error && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-md border border-danger/30 px-3.5 py-2.5 flex items-center gap-2">
              <p className="text-[13px] text-danger">{error}</p>
              <button
                onClick={() => {
                  const lastUser = [...messages].reverse().find((x) => x.role === "user");
                  if (lastUser) void send(lastUser.content);
                }}
                title="Retry"
                className="p-1 rounded text-text-muted hover:text-text-primary transition-colors flex items-center gap-1 text-[11px]"
              >
                <RotateCcw size={12} /> Retry
              </button>
            </div>
          </div>
        )}
        {!stickBottom && messages.length > 0 && (
          <button
            onClick={() => {
              setStickBottom(true);
              const el = listRef.current;
              if (el) el.scrollTop = el.scrollHeight;
            }}
            title="Jump to latest"
            className="sticky bottom-2 left-1/2 -translate-x-1/2 p-2 rounded-full bg-surface border border-border shadow-lg text-text-muted hover:text-accent transition-colors"
          >
            <ArrowDown size={14} />
          </button>
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-divider mt-2 pt-3 flex-shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={areaRef}
            value={input}
            rows={rows}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(input);
              }
            }}
            placeholder="Ask who was earliest, who is on leave…"
            aria-label="Message BLUE"
            className="flex-1 min-w-0 resize-none px-3 py-2 text-[13px] border border-border rounded-input bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent transition-colors max-h-32"
          />
          <button
            onClick={() => { void send(input); }}
            disabled={!input.trim() || thinking}
            title="Send message"
            aria-label="Send message"
            className="w-9 h-9 rounded-full bg-accent text-white flex items-center justify-center flex-shrink-0 hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <SendHorizonal size={15} />
          </button>
        </div>
        <p className="text-[10px] text-text-muted mt-1.5">Enter to send · Shift+Enter for a new line</p>
      </div>
    </div>
  );
}
