interface KPIStatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  pulse?: boolean;
  /** Lighter treatment for secondary dashboard zones */
  muted?: boolean;
}

export function KPIStatCard({
  label,
  value,
  hint,
  pulse,
  muted,
}: KPIStatCardProps) {
  return (
    <div
      className={
        muted
          ? "rounded-lg border border-slate-100/90 bg-white/70 p-4 shadow-none backdrop-blur-[2px]"
          : "rounded-xl border border-slate-200/80 bg-white p-5 shadow-card"
      }
    >
      <div className="flex items-start justify-between gap-3">
        <p
          className={
            muted
              ? "text-[11px] font-medium uppercase tracking-wide text-slate-400"
              : "text-sm font-medium text-slate-500"
          }
        >
          {label}
        </p>
        {pulse ? (
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/70 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500/90" />
          </span>
        ) : null}
      </div>
      <p
        className={
          muted
            ? "mt-2.5 text-2xl font-semibold tracking-tight text-slate-600 tabular-nums"
            : "mt-3 text-3xl font-semibold tracking-tight text-slate-900"
        }
      >
        {value}
      </p>
      {hint ? (
        <p
          className={
            muted
              ? "mt-1.5 text-[11px] text-slate-400 leading-relaxed"
              : "mt-2 text-xs text-slate-500 leading-relaxed"
          }
        >
          {hint}
        </p>
      ) : null}
    </div>
  );
}
