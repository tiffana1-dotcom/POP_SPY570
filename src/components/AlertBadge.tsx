import type {
  AlertSeverity,
  CategoryHeat,
  Recommendation,
} from "@/data/mockData";

const recommendationClass: Record<Recommendation, string> = {
  Import:
    "bg-emerald-50 text-emerald-900 ring-1 ring-inset ring-emerald-600/15",
  Watch: "bg-amber-50 text-amber-900 ring-1 ring-inset ring-amber-600/15",
  Avoid: "bg-rose-50 text-rose-900 ring-1 ring-inset ring-rose-600/15",
};

const categoryHeatClass: Record<CategoryHeat, string> = {
  "Heating Up":
    "bg-orange-50 text-orange-900 ring-1 ring-inset ring-orange-600/15",
  Stable: "bg-slate-50 text-slate-700 ring-1 ring-inset ring-slate-500/15",
  Saturated:
    "bg-violet-50 text-violet-900 ring-1 ring-inset ring-violet-600/15",
};

const severityClass: Record<AlertSeverity, string> = {
  Info: "bg-slate-50 text-slate-700 ring-1 ring-inset ring-slate-500/15",
  Elevated:
    "bg-amber-50 text-amber-900 ring-1 ring-inset ring-amber-600/15",
  Critical: "bg-rose-50 text-rose-900 ring-1 ring-inset ring-rose-600/15",
};

const baseClass =
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium";

type AlertBadgeProps =
  | {
      kind: "recommendation";
      recommendation: Recommendation;
      className?: string;
    }
  | {
      kind: "categoryHeat";
      heat: CategoryHeat;
      className?: string;
    }
  | {
      kind: "severity";
      severity: AlertSeverity;
      className?: string;
    }
  | {
      kind: "tag";
      children: React.ReactNode;
      className?: string;
    };

export function AlertBadge(props: AlertBadgeProps) {
  if (props.kind === "recommendation") {
    return (
      <span
        className={`${baseClass} ${recommendationClass[props.recommendation]} ${props.className ?? ""}`}
      >
        {props.recommendation}
      </span>
    );
  }
  if (props.kind === "categoryHeat") {
    return (
      <span
        className={`${baseClass} ${categoryHeatClass[props.heat]} ${props.className ?? ""}`}
      >
        {props.heat}
      </span>
    );
  }
  if (props.kind === "severity") {
    return (
      <span
        className={`${baseClass} ${severityClass[props.severity]} ${props.className ?? ""}`}
      >
        {props.severity}
      </span>
    );
  }
  return (
    <span
      className={`${baseClass} bg-white text-slate-600 ring-1 ring-inset ring-slate-200 shadow-sm ${props.className ?? ""}`}
    >
      {props.children}
    </span>
  );
}
