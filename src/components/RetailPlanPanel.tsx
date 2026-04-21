import {
  getSeasonalContext,
  getUpcomingRetailMoments,
} from "@/data/retailCalendar";

const HORIZON_DAYS = 60;

export function RetailPlanPanel() {
  const moments = getUpcomingRetailMoments(new Date(), HORIZON_DAYS);
  const season = getSeasonalContext(new Date());

  return (
    <section className="rounded-2xl border border-slate-200/90 bg-gradient-to-br from-slate-50/90 to-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <h2 className="text-sm font-semibold tracking-tight text-slate-900">
          Retail calendar &amp; seasonality
        </h2>
        <p className="text-[11px] text-slate-500">
          Next ~{HORIZON_DAYS} days · planning view (not live sales data)
        </p>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Seasonal lens
          </p>
          <p className="mt-2 text-sm font-medium text-slate-900">{season.label}</p>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
            {season.narrative}
          </p>
          <ul className="mt-3 flex flex-wrap gap-1.5">
            {season.typicalDemand.map((t) => (
              <li
                key={t}
                className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] text-slate-700"
              >
                {t}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Upcoming moments
          </p>
          {moments.length === 0 ? (
            <p className="mt-2 text-xs text-slate-500">
              No major events in this window — widen your sourcing horizon or add
              custom events in code.
            </p>
          ) : (
            <ul className="mt-2 space-y-3">
              {moments.map((m) => (
                <li key={m.id} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-slate-900">{m.label}</p>
                    <span className="shrink-0 text-[11px] tabular-nums text-slate-500">
                      {m.daysUntilPeak >= 0
                        ? `in ${m.daysUntilPeak}d`
                        : `${-m.daysUntilPeak}d ago`}
                    </span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    {m.buyerNotes}
                  </p>
                  <p className="mt-1.5 text-[11px] text-slate-500">
                    Lead time (rule of thumb): ~{m.leadWeeks} wk ·{" "}
                    {m.focusKeywords.join(", ")}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
