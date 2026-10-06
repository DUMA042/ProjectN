import { useState } from "react";
import { FileText, Sparkles } from "lucide-react";
import type {
  DetectedTopic,
  RecommendedRange,
  TopicChoice,
} from "@/lib/reportBuild";

const PRESETS: { label: string; min: number; max: number }[] = [
  { label: "500–1,000 words", min: 500, max: 1000 },
  { label: "1,000–1,500 words", min: 1000, max: 1500 },
  { label: "1,500–2,000 words", min: 1500, max: 2000 },
  { label: "2,000–3,000 words", min: 2000, max: 3000 },
];

const FOCUS_LABEL: Record<TopicChoice["focus"], string> = {
  low: "Low — brief summary and key figures",
  medium: "Medium — summary, trends and interpretation",
  high: "High — detailed analysis and comparisons",
};

interface Props {
  topics: DetectedTopic[];
  recommended: RecommendedRange;
  busy: boolean;
  /** False when the job has moved past topics_ready: Generate must not fire. */
  stageOk: boolean;
  /** Rebuild path: prefill a previously saved selection. */
  initialSelection?: { topics: TopicChoice[]; range: { min_words: number; max_words: number } } | null;
  onGenerate: (topics: TopicChoice[], range: { min_words: number; max_words: number }) => void;
}

/** Topic checkboxes + focus gauges + word-range confirm. */
export default function BuildTopics({ topics, recommended, busy, stageOk, initialSelection, onGenerate }: Props) {
  const [choices, setChoices] = useState<TopicChoice[]>(() => {
    if (initialSelection) {
      const byName = new Map(initialSelection.topics.map((t) => [t.name, t]));
      return topics.map((t) => byName.get(t.name) || { name: t.name, include: false, focus: t.suggested_focus });
    }
    return topics.map((t) => ({ name: t.name, include: true, focus: t.suggested_focus }));
  });
  const [preset, setPreset] = useState<number | null>(() => {
    if (!initialSelection) return null;
    const { min_words, max_words } = initialSelection.range;
    const i = PRESETS.findIndex((p) => p.min === min_words && p.max === max_words);
    return i >= 0 ? i : null;
  });
  const [customMin, setCustomMin] = useState(() => {
    if (!initialSelection) return "";
    const { min_words, max_words } = initialSelection.range;
    return PRESETS.some((p) => p.min === min_words && p.max === max_words) ? "" : String(min_words);
  });
  const [customMax, setCustomMax] = useState(() => {
    if (!initialSelection) return "";
    const { min_words, max_words } = initialSelection.range;
    return PRESETS.some((p) => p.min === min_words && p.max === max_words) ? "" : String(max_words);
  });

  const toggle = (name: string) =>
    setChoices((cs) => cs.map((c) => (c.name === name ? { ...c, include: !c.include } : c)));
  const setFocus = (name: string, focus: TopicChoice["focus"]) =>
    setChoices((cs) => cs.map((c) => (c.name === name ? { ...c, focus } : c)));

  const range =
    preset !== null
      ? { min_words: PRESETS[preset].min, max_words: PRESETS[preset].max }
      : customMin || customMax
        ? { min_words: Number(customMin) || 0, max_words: Number(customMax) || 0 }
        : { min_words: recommended.min_words, max_words: recommended.max_words };

  const valid =
    choices.some((c) => c.include) &&
    range.min_words >= 100 &&
    range.max_words >= range.min_words &&
    range.max_words <= 10000;

  return (
    <div className="card-container overflow-hidden">
      <div className="px-4 pt-3 pb-1">
        <h2 className="text-xs font-semibold text-text-primary">Report topics</h2>
        <p className="text-[11px] text-text-muted">
          Detected from your files. Tick what to include and set each topic's focus.
        </p>
      </div>
      <div className="px-4 pb-2 space-y-2">
        {topics.map((t) => {
          const c = choices.find((x) => x.name === t.name);
          if (!c) return null;
          return (
            <div key={t.name} className="p-2.5 rounded-btn border border-border">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={c.include}
                  onChange={() => toggle(t.name)}
                  className="accent-[#1677FF] w-3.5 h-3.5"
                />
                <span className="text-sm font-medium text-text-primary">{t.name}</span>
              </label>
              {t.coverage && (
                <p className="text-[11px] text-text-muted mt-0.5 ml-6">{t.coverage}</p>
              )}
              <div className="flex items-center gap-2 mt-1.5 ml-6">
                <span className="text-[11px] text-text-muted whitespace-nowrap">Focus</span>
                <input
                  type="range"
                  min={0}
                  max={2}
                  step={1}
                  value={c.focus === "low" ? 0 : c.focus === "high" ? 2 : 1}
                  onChange={(e) =>
                    setFocus(t.name, (["low", "medium", "high"] as const)[Number(e.target.value)])
                  }
                  disabled={!c.include}
                  aria-label={`${t.name} focus`}
                  className="flex-1 accent-[#1677FF] disabled:opacity-40"
                />
                <span className="text-[11px] font-medium text-accent w-14 text-right capitalize">
                  {c.focus}
                </span>
              </div>
              <p className="text-[10px] text-text-muted ml-6">{FOCUS_LABEL[c.focus]}</p>
            </div>
          );
        })}
      </div>
      <div className="px-4 pb-2">
        <h2 className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
          <FileText size={13} className="text-text-muted" /> Report length
        </h2>
        <div className="flex items-start gap-2 mt-1.5 p-2.5 rounded-btn bg-badge-blue-bg text-[11px] text-badge-blue-text">
          <Sparkles size={13} className="flex-shrink-0 mt-0.5" />
          <span>
            AI recommends <strong>{recommended.min_words.toLocaleString()}–{recommended.max_words.toLocaleString()} words</strong>
            {recommended.reasoning ? ` — ${recommended.reasoning}` : ". You can keep it or choose below."}
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {PRESETS.map((p, i) => (
            <button
              key={p.label}
              onClick={() => { setPreset(i); setCustomMin(""); setCustomMax(""); }}
              className={`px-2.5 py-1 text-[11px] rounded-btn border transition-colors ${
                preset === i
                  ? "border-accent text-accent bg-accent/5"
                  : "border-border text-text-secondary hover:bg-nav-hover"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 mt-2 text-[11px] text-text-secondary">
          <span>Custom</span>
          <input
            type="number"
            min={100}
            placeholder="Min"
            value={customMin}
            onChange={(e) => { setCustomMin(e.target.value); setPreset(null); }}
            className="w-20 px-2 py-1 text-[11px] rounded-btn border border-border bg-surface text-text-primary"
          />
          <span>–</span>
          <input
            type="number"
            min={100}
            placeholder="Max"
            value={customMax}
            onChange={(e) => { setCustomMax(e.target.value); setPreset(null); }}
            className="w-20 px-2 py-1 text-[11px] rounded-btn border border-border bg-surface text-text-primary"
          />
          <span>words</span>
        </div>
      </div>
      <div className="px-4 pb-3">
        {valid ? (
          <button
            onClick={() => onGenerate(choices, range)}
            disabled={busy || !stageOk}
            className="w-full px-3 py-2 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            {busy ? "Saving…" : "Generate Report"}
          </button>
        ) : (
          <p className="text-[11px] text-text-muted">
            Select at least one topic and a valid word range to generate the report.
          </p>
        )}
        {!stageOk && valid && (
          <p className="text-[11px] text-text-muted mt-1">Waiting on the build — Generate unlocks when analysis is current.</p>
        )}
        {!choices.some((c) => c.include) && (
          <p className="text-[11px] text-danger mt-1">Include at least one topic.</p>
        )}
      </div>
    </div>
  );
}
