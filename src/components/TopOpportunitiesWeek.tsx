import { Link } from "react-router-dom";
import type { EnrichedProduct } from "@/data/mockData";
import { AlertBadge } from "@/components/AlertBadge";

interface TopOpportunitiesWeekProps {
  products: EnrichedProduct[];
}

export function TopOpportunitiesWeek({ products }: TopOpportunitiesWeekProps) {
  const top = [...products]
    .sort((a, b) => b.opportunityScore - a.opportunityScore)
    .slice(0, 5);

  return (
    <section className="relative overflow-hidden rounded-2xl border-2 border-slate-200/95 bg-white shadow-[0_24px_70px_-18px_rgba(15,23,42,0.14)] ring-1 ring-slate-900/[0.04] sm:rounded-3xl">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(1200px_400px_at_50%_-20%,rgba(16,185,129,0.07),transparent_55%)]"
        aria-hidden
      />
      <div className="relative px-5 pb-6 pt-7 sm:px-8 sm:pb-8 sm:pt-9">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-800/90">
              Sourcing priority
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl sm:tracking-tight">
              Top opportunities this week
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600 sm:text-[15px]">
              Ranked by Opportunity Score from multi-day Amazon signal snapshots —
              built to answer what deserves buyer attention first.
            </p>
          </div>
          <span className="inline-flex w-fit shrink-0 items-center gap-2 rounded-full bg-emerald-600 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-white shadow-sm">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white/70 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-white" />
            </span>
            Live shortlist
          </span>
        </div>

        {top.length === 0 ? (
          <p className="mt-7 rounded-2xl border border-dashed border-slate-200/90 bg-slate-50/50 px-4 py-10 text-center text-sm text-slate-500 sm:mt-8">
            No products match this filter, or the feed is empty. Check API status
            and filters.
          </p>
        ) : (
          <ol className="mt-7 divide-y divide-slate-200/90 rounded-2xl border border-slate-200/90 bg-slate-50/40 shadow-inner backdrop-blur-[2px] sm:mt-8">
            {top.map((p, i) => (
              <li key={p.asin}>
                <Link
                  to={`/products/${p.asin}`}
                  className="group flex flex-col gap-4 p-4 transition-colors hover:bg-white/90 sm:flex-row sm:items-center sm:gap-5 sm:p-5"
                >
                  <div className="flex items-start gap-4 sm:contents">
                    <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-900 text-base font-bold text-white shadow-md tabular-nums ring-2 ring-white sm:h-14 sm:w-14 sm:text-lg">
                      #{i + 1}
                    </span>
                    <img
                      src={p.image}
                      alt=""
                      className="h-16 w-16 shrink-0 rounded-2xl object-cover shadow-md ring-2 ring-white sm:h-[4.75rem] sm:w-[4.75rem]"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-[15px] font-semibold leading-snug text-slate-900 group-hover:text-slate-800 sm:text-base">
                        {p.title}
                      </p>
                      <p className="mt-1.5 text-sm leading-relaxed text-slate-600 line-clamp-2">
                        {p.headlineReason}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center justify-between gap-4 border-t border-slate-200/80 pt-4 sm:w-48 sm:flex-col sm:items-end sm:border-0 sm:pt-0">
                    <div className="text-left sm:text-right">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
                        Opportunity
                      </p>
                      <p className="text-3xl font-bold tabular-nums leading-none text-slate-900 sm:text-[2.125rem]">
                        {p.opportunityScore}
                      </p>
                    </div>
                    <AlertBadge
                      kind="recommendation"
                      recommendation={p.recommendation}
                    />
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
