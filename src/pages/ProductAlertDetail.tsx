import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTrendFeed } from "@/context/TrendFeedContext";
import { AlertBadge } from "@/components/AlertBadge";
import { EmailModal } from "@/components/EmailModal";
import { RecommendationPanel } from "@/components/RecommendationPanel";
import type { ProductSnapshot } from "@/data/mockData";

export function ProductAlertDetail() {
  const { id } = useParams();
  const { getProduct, loading } = useTrendFeed();
  const product = id ? getProduct(id) : undefined;
  const [emailOpen, setEmailOpen] = useState(false);

  if (loading && !product) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-card text-sm text-slate-600">
        Loading product…
      </div>
    );
  }

  if (!product) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-card">
        <p className="text-sm text-slate-600">
          Product not found in the current feed.
        </p>
        <Link
          to="/"
          className="mt-4 inline-block text-sm font-medium text-slate-900 underline-offset-4 hover:underline"
        >
          Back to radar
        </Link>
      </div>
    );
  }

  const rankSummary =
    product.rankImprovement7d >= 0
      ? `↑ ${product.rankImprovement7d} positions (net vs week start, best rank / day)`
      : `↓ ${Math.abs(product.rankImprovement7d)} positions vs week start`;

  const snapshotRows = [...product.snapshots].sort(
    (a, b) => new Date(b.capturedAt).getTime() - new Date(a.capturedAt).getTime(),
  );

  return (
    <>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Link
            to="/"
            className="text-slate-500 hover:text-slate-800 transition-colors"
          >
            Live radar
          </Link>
          <span className="text-slate-300">/</span>
          <span className="font-medium text-slate-900 line-clamp-1">
            {product.title}
          </span>
        </div>

        <div className="rounded-lg border border-amber-200/80 bg-amber-50/50 px-4 py-3 text-sm text-amber-950">
          <span className="font-semibold">Buyer alert: </span>
          {product.headlineReason}
        </div>

        <div className="grid gap-6 lg:grid-cols-12 lg:items-start">
          <div className="lg:col-span-5 space-y-4">
            <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-card">
              <div className="aspect-square bg-slate-50">
                <img
                  src={product.image}
                  alt=""
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="p-5 space-y-4">
                <div>
                  <h1 className="text-lg font-semibold text-slate-900 leading-snug">
                    {product.title}
                  </h1>
                  <p className="mt-1 text-xs font-mono text-slate-500">
                    {product.retailer === "yamibuy" ? "Yamibuy SKU · " : "ASIN · "}
                    {product.asin}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">{product.category}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {product.buyer.marketplaces.map((m) => (
                    <AlertBadge key={m} kind="tag">
                      {m}
                    </AlertBadge>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  {product.activeSources.map((s) => (
                    <AlertBadge key={s} kind="tag">
                      {s}
                    </AlertBadge>
                  ))}
                </div>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                  <div>
                    <dt className="text-xs font-medium text-slate-500">Price</dt>
                    <dd className="mt-0.5 font-semibold text-slate-900">
                      {product.latestPrice}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-slate-500">Rating</dt>
                    <dd className="mt-0.5 font-semibold tabular-nums text-slate-900">
                      {product.latestRating.toFixed(1)} ★
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-slate-500">
                      Review count
                    </dt>
                    <dd className="mt-0.5 font-semibold tabular-nums text-slate-900">
                      {product.latestReviewCount.toLocaleString()}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-slate-500">
                      Rank movement (7d)
                    </dt>
                    <dd className="mt-0.5 font-semibold text-slate-900">
                      {rankSummary}
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-xs font-medium text-slate-500">
                      Review growth (7d)
                    </dt>
                    <dd className="mt-0.5 text-slate-800">
                      +{product.reviewGrowth7d} net new reviews vs week start
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-xs font-medium text-slate-500">
                      Opportunity score
                    </dt>
                    <dd className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="text-2xl font-semibold tabular-nums text-slate-900">
                        {product.opportunityScore}
                      </span>
                      <AlertBadge
                        kind="recommendation"
                        recommendation={product.recommendation}
                      />
                      <span className="text-xs text-slate-500">
                        Confidence {product.confidenceLevel}
                      </span>
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 space-y-4">
            <RecommendationPanel product={product} />

            <section className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-card">
              <h2 className="text-sm font-semibold text-slate-900">
                Why it&apos;s rising
              </h2>
              <ul className="mt-4 space-y-3">
                {product.explanationBullets.map((line, i) => (
                  <li
                    key={i}
                    className="flex gap-3 text-sm text-slate-700 leading-relaxed"
                  >
                    <span
                      className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500"
                      aria-hidden
                    />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-card">
              <h2 className="text-sm font-semibold text-slate-900">
                Buyer action
              </h2>
              <dl className="mt-4 grid gap-4 sm:grid-cols-2 text-sm">
                <div>
                  <dt className="text-xs font-medium text-slate-500">
                    Suggested sourcing strategy
                  </dt>
                  <dd className="mt-1 text-slate-700 leading-relaxed">
                    {product.buyer.sourcingStrategy}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">
                    Suggested price range
                  </dt>
                  <dd className="mt-1 font-medium text-slate-900">
                    {product.buyer.suggestedPriceRange}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">
                    Target channels
                  </dt>
                  <dd className="mt-1 text-slate-700">
                    {product.buyer.targetChannels.join(" · ")}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">
                    Risk level
                  </dt>
                  <dd className="mt-1">
                    <span
                      className={`inline-flex rounded-md px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${
                        product.buyer.riskLevel === "Low"
                          ? "bg-emerald-50 text-emerald-900 ring-emerald-600/15"
                          : product.buyer.riskLevel === "Medium"
                            ? "bg-amber-50 text-amber-900 ring-amber-600/15"
                            : "bg-rose-50 text-rose-900 ring-rose-600/15"
                      }`}
                    >
                      {product.buyer.riskLevel}
                    </span>
                  </dd>
                </div>
              </dl>
              <div className="mt-5">
                <button
                  type="button"
                  onClick={() => setEmailOpen(true)}
                  className="inline-flex w-full sm:w-auto justify-center rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2"
                >
                  Generate outreach email
                </button>
              </div>
            </section>

            <SnapshotHistoryTable rows={snapshotRows} />
          </div>
        </div>
      </div>

      <EmailModal
        open={emailOpen}
        onClose={() => setEmailOpen(false)}
        subject={product.buyer.manufacturerEmailSubject}
        body={product.buyer.manufacturerEmailBody}
      />
    </>
  );
}

function SnapshotHistoryTable({ rows }: { rows: ProductSnapshot[] }) {
  return (
    <section className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-card">
      <h2 className="text-sm font-semibold text-slate-900">
        Snapshot history
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Captures from the current feed pull. Schedule recurring jobs to
        build true multi-day history in your database.
      </p>
      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-100">
        <table className="min-w-[640px] w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/80 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <th className="px-3 py-2 font-medium">Captured</th>
              <th className="px-3 py-2 font-medium">Source</th>
              <th className="px-3 py-2 font-medium">Rank</th>
              <th className="px-3 py-2 font-medium">Price</th>
              <th className="px-3 py-2 font-medium">Rating</th>
              <th className="px-3 py-2 font-medium">Reviews</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={`${r.capturedAt}-${r.sourceType}-${r.rank}`}
                className="border-b border-slate-50 last:border-0"
              >
                <td className="px-3 py-2 text-slate-700 tabular-nums">
                  {new Date(r.capturedAt).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </td>
                <td className="px-3 py-2 text-slate-800">{r.sourceType}</td>
                <td className="px-3 py-2 font-medium tabular-nums text-slate-900">
                  #{r.rank}
                </td>
                <td className="px-3 py-2 tabular-nums text-slate-700">
                  ${r.price.toFixed(2)}
                </td>
                <td className="px-3 py-2 tabular-nums text-slate-700">
                  {r.rating.toFixed(1)}
                </td>
                <td className="px-3 py-2 tabular-nums text-slate-700">
                  {r.reviewCount.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
