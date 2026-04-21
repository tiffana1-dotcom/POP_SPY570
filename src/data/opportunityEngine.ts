import type {
  ConfidenceLevel,
  ProductSnapshot,
  Recommendation,
  SourceType,
} from "./types";

export interface OpportunityResult {
  opportunityScore: number;
  recommendation: Recommendation;
  confidenceLevel: ConfidenceLevel;
  explanationBullets: string[];
  headlineReason: string;
  cardExplanation: string;
  rankImprovement7d: number;
  reviewGrowth7d: number;
  uniqueSignalDays: number;
  snapshotCount: number;
  moversHits: number;
  bestSellersHits: number;
  newReleasesHits: number;
  searchHits: number;
  improvingSnapshotPairs: number;
  saturatedIncumbent: boolean;
}

function dayKey(iso: string): string {
  return iso.slice(0, 10);
}

function sortChrono(a: ProductSnapshot, b: ProductSnapshot): number {
  return new Date(a.capturedAt).getTime() - new Date(b.capturedAt).getTime();
}

function countSource(
  snaps: ProductSnapshot[],
  s: SourceType,
): number {
  return snaps.filter((x) => x.sourceType === s).length;
}

export function computeOpportunity(
  snapshots: ProductSnapshot[],
): OpportunityResult {
  if (snapshots.length === 0) {
    return {
      opportunityScore: 0,
      recommendation: "Avoid",
      confidenceLevel: "Low",
      explanationBullets: ["Insufficient snapshot history to score this ASIN."],
      headlineReason: "Not enough multi-day data yet.",
      cardExplanation: "Needs more tracking days.",
      rankImprovement7d: 0,
      reviewGrowth7d: 0,
      uniqueSignalDays: 0,
      snapshotCount: 0,
      moversHits: 0,
      bestSellersHits: 0,
      newReleasesHits: 0,
      searchHits: 0,
      improvingSnapshotPairs: 0,
      saturatedIncumbent: true,
    };
  }

  const sorted = [...snapshots].sort(sortChrono);
  const lastDate = new Date(sorted[sorted.length - 1].capturedAt);
  const windowStart = new Date(lastDate);
  windowStart.setDate(windowStart.getDate() - 6);
  const windowMs = windowStart.getTime();

  const inWindow = sorted.filter(
    (s) => new Date(s.capturedAt).getTime() >= windowMs,
  );
  const use = inWindow.length > 0 ? inWindow : sorted;

  const byDay = new Map<string, ProductSnapshot[]>();
  for (const s of use) {
    const k = dayKey(s.capturedAt);
    const arr = byDay.get(k) ?? [];
    arr.push(s);
    byDay.set(k, arr);
  }

  const days = [...byDay.keys()].sort();
  const bestRankByDay = days.map((d) => {
    const daySnaps = byDay.get(d)!;
    return Math.min(...daySnaps.map((x) => x.rank));
  });

  const firstRank = bestRankByDay[0] ?? use[0].rank;
  const lastRank = bestRankByDay[bestRankByDay.length - 1] ?? use[use.length - 1].rank;
  const rankImprovement7d = firstRank - lastRank;

  const firstReviews = use[0].reviewCount;
  const lastReviews = use[use.length - 1].reviewCount;
  const reviewGrowth7d = lastReviews - firstReviews;

  let improvingPairs = 0;
  for (let i = 1; i < bestRankByDay.length; i++) {
    if (bestRankByDay[i] < bestRankByDay[i - 1]) improvingPairs += 1;
  }

  const moversHits = countSource(use, "Movers & Shakers");
  const bestSellersHits = countSource(use, "Best Sellers");
  const newReleasesHits = countSource(use, "New Releases");
  const searchHits = countSource(use, "Search");
  const distinctSources = new Set(use.map((x) => x.sourceType)).size;

  const totalSnaps = use.length;
  const uniqueSignalDays = days.length;

  /** Higher rank number = worse; stable high rank + BS-only reads as incumbent */
  const saturatedIncumbent =
    rankImprovement7d < 8 &&
    uniqueSignalDays >= 4 &&
    moversHits + newReleasesHits <= 1 &&
    bestSellersHits >= Math.max(3, Math.floor(totalSnaps * 0.55)) &&
    lastRank <= 120;

  const rankScore = Math.min(38, Math.max(0, rankImprovement7d * 0.38));
  const persistenceScore = Math.min(
    22,
    improvingPairs * 5 + Math.min(6, uniqueSignalDays * 0.8),
  );
  const signalMixScore = Math.min(
    16,
    distinctSources * 5 +
      Math.min(6, (moversHits + newReleasesHits + searchHits) * 1.0),
  );
  const repeatSignalScore = Math.min(12, (totalSnaps - uniqueSignalDays) * 2);
  const reviewScore = Math.min(18, reviewGrowth7d * 0.65);
  const noveltyScore = Math.min(10, newReleasesHits * 3.2);

  let raw =
    rankScore +
    persistenceScore +
    signalMixScore +
    repeatSignalScore +
    reviewScore +
    noveltyScore;

  if (saturatedIncumbent) raw -= 26;
  if (lastRank > 220 && rankImprovement7d < 15) raw -= 8;

  const opportunityScore = Math.round(Math.min(100, Math.max(0, raw)));

  let recommendation: Recommendation = "Watch";
  if (opportunityScore >= 74 && !saturatedIncumbent) recommendation = "Import";
  else if (opportunityScore < 42 || saturatedIncumbent) recommendation = "Avoid";
  else recommendation = "Watch";

  /** Aligned with synthetic feeds (GPT / Rainforest) that emit 4 snapshots on 4 distinct days. */
  let confidenceLevel: ConfidenceLevel = "Low";
  if (uniqueSignalDays >= 5 && totalSnaps >= 10) confidenceLevel = "High";
  else if (uniqueSignalDays >= 3 && totalSnaps >= 4) confidenceLevel = "Medium";
  else confidenceLevel = "Low";

  const explanationBullets: string[] = [];
  if (improvingPairs >= 2 || rankImprovement7d >= 12) {
    explanationBullets.push(
      `Rank improved across ${Math.max(improvingPairs, 1)} multi-day windows in the last 7 days (≈${rankImprovement7d} positions net).`,
    );
  }
  if (moversHits >= 2) {
    explanationBullets.push(
      `Appeared in Movers & Shakers ${moversHits} times this week — repeated breakout signal.`,
    );
  }
  if (reviewGrowth7d > 0) {
    explanationBullets.push(
      `Review count increased by ${reviewGrowth7d} this week — demand looks sustained, not a one-day blip.`,
    );
  }
  if (newReleasesHits >= 1) {
    explanationBullets.push(
      `Also appeared in New Releases — novelty tailwind alongside momentum.`,
    );
  }
  if (searchHits >= 1) {
    explanationBullets.push(
      `Matched Amazon search results for your tracked queries — extra discovery beyond charts.`,
    );
  }
  if (distinctSources >= 2) {
    explanationBullets.push(
      `Surfaced across ${distinctSources} different Amazon signal lists — corroboration matters for buyers.`,
    );
  }
  if (saturatedIncumbent) {
    explanationBullets.push(
      `Saturation risk: mostly Best Sellers presence with limited rank progress — looks like a stable incumbent, not a new breakout.`,
    );
  }
  if (explanationBullets.length === 0) {
    explanationBullets.push(
      `Mixed signals: ${totalSnaps} snapshots over ${uniqueSignalDays} days — monitor before committing inventory.`,
    );
  }

  const headlineReason = explanationBullets[0] ?? "Multi-day signals are mixed.";
  const cardExplanation =
    explanationBullets[0]?.split("—")[0]?.trim().slice(0, 92) ??
    headlineReason.slice(0, 92);

  return {
    opportunityScore,
    recommendation,
    confidenceLevel,
    explanationBullets,
    headlineReason,
    cardExplanation,
    rankImprovement7d,
    reviewGrowth7d,
    uniqueSignalDays,
    snapshotCount: totalSnaps,
    moversHits,
    bestSellersHits,
    newReleasesHits,
    searchHits,
    improvingSnapshotPairs: improvingPairs,
    saturatedIncumbent,
  };
}
