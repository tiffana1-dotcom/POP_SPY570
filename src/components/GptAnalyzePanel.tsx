import { useState } from "react";
import type {
  AnalysisVerdict,
  RetailAnalysisResult,
  SectionRating,
} from "@/data/retailAnalysis";

function verdictStyles(v: AnalysisVerdict): string {
  switch (v) {
    case "Good Product":
      return "border-emerald-200 bg-emerald-50/90 text-emerald-950";
    case "Risky Product":
      return "border-amber-200 bg-amber-50/90 text-amber-950";
    case "Weak Product":
      return "border-rose-200 bg-rose-50/80 text-rose-950";
    default:
      return "border-slate-200 bg-slate-50 text-slate-900";
  }
}

function ratingPillClass(r: SectionRating): string {
  switch (r) {
    case "Strong":
      return "bg-emerald-600 text-white ring-1 ring-emerald-700/20";
    case "Moderate":
      return "bg-amber-500 text-white ring-1 ring-amber-600/25";
    case "Weak":
      return "bg-slate-500 text-white ring-1 ring-slate-600/20";
    default:
      return "bg-slate-400 text-white";
  }
}

export function GptAnalyzePanel() {
  const [text, setText] = useState("");
  const [context, setContext] = useState("");
  const [out, setOut] = useState<RetailAnalysisResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          context: context.trim() || undefined,
        }),
      });
      const data = (await res.json()) as {
        analysis?: RetailAnalysisResult;
        error?: string;
      };
      if (!res.ok) throw new Error(data.error ?? `HTTP ${res.status}`);
      if (!data.analysis) throw new Error("Missing analysis payload");
      setOut(data.analysis);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
      setOut(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <h2 className="text-sm font-semibold tracking-tight text-slate-900">
          GPT analyst
        </h2>
        <p className="text-[11px] text-slate-500">
          Paste listing copy, bullets, or notes — not a live web scrape
        </p>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-slate-600">
        Structured verdict, score, and section ratings. Uses your OpenAI key on the
        server. For live Amazon listings, use{" "}
        <code className="rounded bg-slate-100 px-1 py-0.5 text-[11px]">
          FEED_MODE=rainforest
        </code>{" "}
        or{" "}
        <code className="rounded bg-slate-100 px-1 py-0.5 text-[11px]">
          scraper
        </code>
        .
      </p>
      <div className="mt-4 space-y-3">
        <div>
          <label htmlFor="gpt-ctx" className="sr-only">
            Optional context
          </label>
          <input
            id="gpt-ctx"
            type="text"
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="Optional: channel, margin goal, region…"
            className="w-full rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-xs text-slate-800 placeholder:text-slate-400"
          />
        </div>
        <div>
          <label htmlFor="gpt-text" className="sr-only">
            Text to analyze
          </label>
          <textarea
            id="gpt-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            placeholder="Paste product description, review summary, competitor positioning…"
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-800 placeholder:text-slate-400"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy || !text.trim()}
            onClick={() => void run()}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-40"
          >
            {busy ? "Analyzing…" : "Analyze with GPT"}
          </button>
          {err ? (
            <span className="text-xs text-rose-700">{err}</span>
          ) : null}
        </div>

        {out ? (
          <div className="mt-4 space-y-4">
            <div
              className={`flex flex-col gap-3 rounded-xl border px-4 py-4 sm:flex-row sm:items-center sm:justify-between ${verdictStyles(out.verdict)}`}
            >
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] opacity-80">
                  Verdict
                </p>
                <p className="mt-1 text-lg font-semibold tracking-tight">
                  {out.verdict}
                </p>
                <p className="mt-2 text-xs leading-relaxed opacity-90">
                  {out.headline}
                </p>
              </div>
              <div className="flex shrink-0 items-baseline gap-1 rounded-xl border border-white/60 bg-white/50 px-4 py-3 shadow-sm backdrop-blur-sm">
                <span className="text-4xl font-bold tabular-nums leading-none text-slate-900">
                  {out.score}
                </span>
                <span className="text-sm font-medium text-slate-500">/100</span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {out.sections.map((s) => (
                <article
                  key={s.id}
                  className="flex flex-col rounded-xl border border-slate-200/90 bg-slate-50/40 p-4 shadow-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <h3 className="text-sm font-semibold text-slate-900">
                      {s.label}
                    </h3>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${ratingPillClass(s.rating)}`}
                    >
                      {s.rating}
                    </span>
                  </div>
                  <p className="mt-3 text-xs leading-relaxed text-slate-700">
                    {s.summary}
                  </p>
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
