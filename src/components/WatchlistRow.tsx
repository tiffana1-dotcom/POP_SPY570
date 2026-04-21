import { Link } from "react-router-dom";
import type { EnrichedProduct } from "@/data/mockData";
import type { WatchlistEntry } from "@/data/mockData";
import { AlertBadge } from "@/components/AlertBadge";

interface WatchlistRowProps {
  product: EnrichedProduct;
  entry: WatchlistEntry;
}

export function WatchlistRow({ product, entry }: WatchlistRowProps) {
  const today = product.opportunityScore;
  const delta = today - entry.yesterdayOpportunity;
  const deltaLabel =
    delta === 0 ? "0" : delta > 0 ? `+${delta}` : `${delta}`;

  return (
    <tr className="border-b border-slate-100 last:border-0 hover:bg-slate-50/80">
      <td className="px-4 py-3 align-top">
        <Link
          to={`/products/${product.asin}`}
          className="group flex gap-3 text-left"
        >
          <img
            src={product.image}
            alt=""
            className="h-11 w-11 shrink-0 rounded-lg object-cover ring-1 ring-slate-200/80"
          />
          <span>
            <span className="block text-sm font-medium text-slate-900 group-hover:text-slate-700 line-clamp-2">
              {product.title}
            </span>
            <span className="text-xs text-slate-500">{product.category}</span>
          </span>
        </Link>
      </td>
      <td className="px-4 py-3 align-top text-sm font-semibold tabular-nums text-slate-900">
        {today}
      </td>
      <td className="px-4 py-3 align-top text-sm tabular-nums text-slate-700">
        <span className="text-slate-500">{entry.yesterdayOpportunity}</span>
        <span className="mx-1 text-slate-300">→</span>
        <span className="font-medium text-slate-900">{today}</span>
        <span
          className={`ml-2 text-xs ${delta > 0 ? "text-emerald-700" : delta < 0 ? "text-rose-700" : "text-slate-500"}`}
        >
          ({deltaLabel})
        </span>
      </td>
      <td className="px-4 py-3 align-top">
        <AlertBadge
          kind="recommendation"
          recommendation={product.recommendation}
        />
      </td>
      <td className="px-4 py-3 align-top">
        <AlertBadge kind="severity" severity={entry.severity} />
      </td>
      <td className="px-4 py-3 align-top text-sm text-slate-600 max-w-[280px] leading-relaxed">
        {entry.statusSummary}
      </td>
    </tr>
  );
}
