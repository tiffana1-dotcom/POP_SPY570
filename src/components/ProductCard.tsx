import { Link } from "react-router-dom";
import type { EnrichedProduct } from "@/data/mockData";
import { AlertBadge } from "@/components/AlertBadge";

interface ProductCardProps {
  product: EnrichedProduct;
  /** Softer card for secondary dashboard lists */
  muted?: boolean;
}

export function ProductCard({ product, muted }: ProductCardProps) {
  const rankLabel =
    product.rankImprovement7d >= 0
      ? `↑ ${product.rankImprovement7d} over 7 days`
      : `↓ ${Math.abs(product.rankImprovement7d)} over 7 days`;

  return (
    <article
      className={
        muted
          ? "flex flex-col rounded-lg border border-slate-100/90 bg-white/70 shadow-none overflow-hidden transition-colors hover:bg-white/95"
          : "flex flex-col rounded-xl border border-slate-200/80 bg-white shadow-card transition-shadow hover:shadow-card-hover overflow-hidden"
      }
    >
      <div className="aspect-square bg-slate-50">
        <img
          src={product.image}
          alt=""
          className="h-full w-full object-cover"
          loading="lazy"
        />
      </div>
      <div className={`flex flex-1 flex-col ${muted ? "p-3.5" : "p-4"}`}>
        <div className="flex flex-wrap gap-1.5">
          <AlertBadge kind="tag">
            {product.retailer === "yamibuy" ? "Yamibuy" : "Amazon"}
          </AlertBadge>
          {product.activeSources.map((s) => (
            <AlertBadge key={s} kind="tag">
              {s}
            </AlertBadge>
          ))}
        </div>
        <h3
          className={
            muted
              ? "mt-2 line-clamp-2 text-xs font-medium text-slate-700 leading-snug"
              : "mt-2 line-clamp-2 text-sm font-semibold text-slate-900 leading-snug"
          }
        >
          {product.title}
        </h3>
        <p
          className={
            muted ? "mt-1 text-[11px] text-slate-400" : "mt-1 text-xs text-slate-500"
          }
        >
          {product.category}
        </p>
        <div className="mt-3 flex items-baseline justify-between gap-2">
          <span
            className={
              muted
                ? "text-xs font-medium text-slate-600"
                : "text-sm font-semibold text-slate-900"
            }
          >
            {product.latestPrice}
          </span>
          <span
            className={
              muted ? "text-[11px] text-slate-400" : "text-xs text-slate-500"
            }
          >
            Opportunity{" "}
            <span
              className={
                muted
                  ? "font-semibold text-slate-600 tabular-nums"
                  : "font-semibold text-slate-800 tabular-nums"
              }
            >
              {product.opportunityScore}
            </span>
          </span>
        </div>
        <p
          className={
            muted
              ? "mt-2 text-[10px] text-slate-500 leading-snug line-clamp-2"
              : "mt-2 text-[11px] text-slate-600 leading-snug line-clamp-2"
          }
        >
          {product.cardExplanation}
        </p>
        <dl
          className={
            muted
              ? "mt-3 space-y-1.5 text-[11px] text-slate-500"
              : "mt-3 space-y-1.5 text-xs text-slate-600"
          }
        >
          <div className="flex justify-between gap-2">
            <dt className={muted ? "text-slate-400" : "text-slate-500"}>
              Rank move
            </dt>
            <dd
              className={
                muted
                  ? "font-medium text-slate-600 tabular-nums text-right"
                  : "font-medium text-slate-800 tabular-nums text-right"
              }
            >
              {rankLabel}
            </dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className={muted ? "text-slate-400" : "text-slate-500"}>
              Reviews
            </dt>
            <dd
              className={
                muted ? "font-medium text-slate-600" : "font-medium text-slate-800"
              }
            >
              +{product.reviewGrowth7d} this week
            </dd>
          </div>
        </dl>
        <div className="mt-3 flex items-center justify-between gap-2">
          <AlertBadge
            kind="recommendation"
            recommendation={product.recommendation}
          />
          <Link
            to={`/products/${product.asin}`}
            className={
              muted
                ? "rounded-md bg-slate-600/90 px-2.5 py-1.5 text-[11px] font-medium text-white hover:bg-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-300 focus-visible:ring-offset-2"
                : "rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2"
            }
          >
            View Alert
          </Link>
        </div>
      </div>
    </article>
  );
}
