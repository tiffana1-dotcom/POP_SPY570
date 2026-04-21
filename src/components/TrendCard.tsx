import type { CategoryTrend } from "@/data/mockData";
import { AlertBadge } from "@/components/AlertBadge";

interface TrendCardProps {
  trend: CategoryTrend;
  /** Softer card for secondary dashboard areas */
  muted?: boolean;
}

export function TrendCard({ trend, muted }: TrendCardProps) {
  const growthLabel =
    trend.momentum7dPct >= 0
      ? `+${trend.momentum7dPct}%`
      : `${trend.momentum7dPct}%`;

  return (
    <div
      className={
        muted
          ? "group rounded-lg border border-slate-100/90 bg-white/60 p-3.5 shadow-none transition-colors hover:bg-white/90"
          : "group rounded-xl border border-slate-200/80 bg-white p-4 shadow-card transition-shadow hover:shadow-card-hover"
      }
    >
      <div className="flex items-start justify-between gap-3">
        <h3
          className={
            muted
              ? "text-xs font-medium text-slate-600 leading-snug"
              : "text-sm font-semibold text-slate-900 leading-snug"
          }
        >
          {trend.name}
        </h3>
        <AlertBadge kind="categoryHeat" heat={trend.heat} />
      </div>
      <p
        className={
          muted
            ? "mt-2 text-xl font-semibold tabular-nums text-slate-700"
            : "mt-3 text-2xl font-semibold tabular-nums text-slate-900"
        }
      >
        {growthLabel}
      </p>
      <p
        className={
          muted ? "mt-0.5 text-[10px] text-slate-400" : "mt-1 text-xs text-slate-500"
        }
      >
        Multi-day momentum index (tracked ASINs)
      </p>
      <p
        className={
          muted
            ? "mt-2 text-[11px] text-slate-500 leading-relaxed line-clamp-3"
            : "mt-3 text-xs text-slate-600 leading-relaxed line-clamp-3"
        }
      >
        {trend.summary}
      </p>
    </div>
  );
}
