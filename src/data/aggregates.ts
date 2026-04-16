import type { EnrichedProduct } from "./catalog";
import type { CategoryTrend } from "./types";

function mean(nums: number[]): number {
  if (nums.length === 0) return 0;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

function heatFromMomentum(m: number): CategoryTrend["heat"] {
  if (m >= 18) return "Heating Up";
  if (m <= 2) return "Saturated";
  return "Stable";
}

/**
 * Build category cards from whatever categories appear in the current feed.
 */
export function buildCategoryTrendsFromProducts(
  products: EnrichedProduct[],
  categoryOrder?: string[],
): CategoryTrend[] {
  const byCat = new Map<string, EnrichedProduct[]>();
  for (const p of products) {
    const arr = byCat.get(p.category) ?? [];
    arr.push(p);
    byCat.set(p.category, arr);
  }

  const names =
    categoryOrder?.filter((n) => byCat.has(n)) ??
    [...byCat.keys()].sort();

  return names.map((name, i) => {
    const list = byCat.get(name) ?? [];
    const avgRank = mean(list.map((x) => x.rankImprovement7d));
    const avgOpp = mean(list.map((x) => x.opportunityScore));
    const momentum7dPct = Math.round(
      Math.min(55, Math.max(-8, avgRank * 0.22 + (avgOpp - 58) * 0.45)),
    );
    const heat = heatFromMomentum(momentum7dPct);
    const summary =
      heat === "Heating Up"
        ? `Avg SKU rank velocity + opportunity are outpacing last week in ${name}.`
        : heat === "Saturated"
          ? `Leaders are entrenched; whitespace is limited without differentiation in ${name}.`
          : `Momentum is constructive but not uniform across tracked ASINs in ${name}.`;
    return {
      id: `c${i + 1}`,
      name,
      momentum7dPct,
      heat,
      summary,
    };
  });
}

export function buildDashboardKpisFromProducts(
  products: EnrichedProduct[],
  trends: CategoryTrend[],
) {
  const risingWeek = products.filter((p) => p.rankImprovement7d >= 14).length;
  const breakoutAlerts = products.filter(
    (p) => p.recommendation === "Import" && p.opportunityScore >= 78,
  ).length;
  const heatingCats = trends.filter((c) => c.heat === "Heating Up").length;
  const worthImport = products.filter((p) => p.recommendation === "Import")
    .length;
  return {
    risingWeek,
    breakoutAlerts,
    heatingCats,
    worthImport,
  };
}
