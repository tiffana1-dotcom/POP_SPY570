import type { DiscoveryMeta } from "@/data/popDiscovery";

export function DiscoveryRibbon({ meta }: { meta: DiscoveryMeta }) {
  return (
    <section className="rounded-2xl border border-emerald-200/80 bg-gradient-to-br from-emerald-50/90 to-white px-4 py-4 shadow-sm sm:px-5 sm:py-5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-900/80">
        Discovery pipeline
      </p>
      <p className="mt-2 text-sm font-medium text-slate-900">
        Public sources + PoP filters
      </p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {meta.publicSources.map((s) => (
          <li
            key={s.id}
            className="rounded-lg border border-emerald-100 bg-white/90 px-2.5 py-1.5 text-[11px] text-slate-700 shadow-sm"
            title={s.detail}
          >
            <span className="font-semibold text-emerald-900">{s.label}</span>
            <span className="text-slate-500"> — {s.detail}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 grid gap-3 border-t border-emerald-100/90 pt-4 text-xs text-slate-600 sm:grid-cols-2">
        <div>
          <p className="font-medium text-slate-800">Yami pulse (cached)</p>
          <p className="mt-1 leading-relaxed">
            {meta.yamiSnapshot.sourceLabel} · as of{" "}
            {new Date(meta.yamiSnapshot.asOf).toLocaleDateString()}
          </p>
          <p className="mt-1 text-[11px] text-slate-500">
            Ingredients: {meta.yamiSnapshot.trendingIngredientsSample.join(", ")}…
          </p>
        </div>
        <div>
          <p className="font-medium text-slate-800">Scoring &amp; filtering</p>
          <p className="mt-1 leading-relaxed">{meta.scoringExplainer}</p>
          <p className="mt-1 leading-relaxed text-slate-500">{meta.filteringExplainer}</p>
        </div>
      </div>
    </section>
  );
}
