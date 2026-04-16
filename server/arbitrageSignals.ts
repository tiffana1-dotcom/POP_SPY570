/**
 * External signals for arbitrage scoring (Google Trends, Reddit, Walmart)
 * aligned with the user's Python reference pipeline.
 */

import type { OpportunityResult } from "../src/data/opportunityEngine";
import type { Recommendation } from "../src/data/types";
import {
  bsrFromProduct,
  type RainforestProductPayload,
} from "./rainforestApi";

const SUBREDDITS = [
  "asianeats",
  "tea",
  "casualuk",
  "EatCheapAndHealthy",
  "xxkpop",
] as const;

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export async function getTrendScores(
  displayNames: string[],
): Promise<Record<string, number>> {
  const enabled = (process.env.FEED_ENABLE_GOOGLE_TRENDS ?? "1").trim() === "1";
  const scores: Record<string, number> = {};
  if (!enabled || displayNames.length === 0) {
    for (const n of displayNames) scores[n] = 0;
    return scores;
  }

  let googleTrends: typeof import("google-trends-api").default;
  try {
    googleTrends = (await import("google-trends-api")).default;
  } catch {
    for (const n of displayNames) scores[n] = 0;
    return scores;
  }

  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - 12);

  for (let i = 0; i < displayNames.length; i += 5) {
    const batch = displayNames.slice(i, i + 5);
    try {
      const results = await googleTrends.interestOverTime({
        keyword: batch.length === 1 ? batch[0] : batch,
        startTime: start,
        endTime: end,
        geo: "US",
        hl: "en-US",
      });
      const raw =
        typeof results === "string" ? JSON.parse(results) : results;
      const timeline = raw?.default?.timelineData as
        | { value?: number[] }[]
        | undefined;
      if (Array.isArray(timeline) && timeline.length > 0) {
        const nkw = batch.length;
        for (let k = 0; k < batch.length; k++) {
          const term = batch[k];
          let sum = 0;
          let count = 0;
          for (const row of timeline) {
            const v = row.value?.[k];
            if (typeof v === "number") {
              sum += v;
              count += 1;
            }
          }
          scores[term] =
            count > 0 ? Math.round(sum / count) : nkw > 1 ? 0 : Math.round(sum);
        }
      }
    } catch {
      for (const term of batch) {
        if (scores[term] === undefined) scores[term] = 0;
      }
    }
    await sleep(1000);
  }

  for (const n of displayNames) {
    if (scores[n] === undefined) scores[n] = 0;
  }
  return scores;
}

export async function getRedditSignal(productName: string): Promise<{
  mentions: number;
  signal: "high" | "med" | "low";
}> {
  const enabled = (process.env.FEED_ENABLE_REDDIT ?? "1").trim() === "1";
  if (!enabled) {
    return { mentions: 0, signal: "low" };
  }

  let mentionCount = 0;
  const headers = {
    "User-Agent": "TrendScout/1.0 (arbitrage feed; +https://localhost)",
  };
  for (const sub of SUBREDDITS) {
    const u = new URL(`https://www.reddit.com/r/${sub}/search.json`);
    u.searchParams.set("q", productName);
    u.searchParams.set("limit", "25");
    u.searchParams.set("sort", "new");
    u.searchParams.set("restrict_sr", "1");
    try {
      const r = await fetch(u.toString(), { headers, signal: AbortSignal.timeout(8000) });
      if (!r.ok) continue;
      const data = (await r.json()) as {
        data?: { children?: unknown[] };
      };
      mentionCount += data.data?.children?.length ?? 0;
    } catch {
      /* ignore */
    }
    await sleep(500);
  }

  const signal: "high" | "med" | "low" =
    mentionCount > 10 ? "high" : mentionCount > 3 ? "med" : "low";
  return { mentions: mentionCount, signal };
}

export async function checkWalmartGap(productName: string): Promise<{
  walmart_count: number;
  gap: "high" | "med" | "low" | "unknown";
}> {
  const key = process.env.WALMART_CONSUMER_ID?.trim();
  const enabled = (process.env.FEED_ENABLE_WALMART ?? "1").trim() === "1";
  if (!enabled || !key) {
    return { walmart_count: -1, gap: "unknown" };
  }

  const url = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2/search";
  try {
    const u = new URL(url);
    u.searchParams.set("query", productName);
    u.searchParams.set("numItems", "5");
    const r = await fetch(u.toString(), {
      headers: {
        "WM_SEC.KEY_VERSION": "1",
        "WM_CONSUMER.ID": key,
      },
      signal: AbortSignal.timeout(8000),
    });
    if (!r.ok) return { walmart_count: -1, gap: "unknown" };
    const data = (await r.json()) as { items?: unknown[] };
    const items = Array.isArray(data.items) ? data.items : [];
    const count = items.length;
    const gap: "high" | "med" | "low" =
      count === 0 ? "high" : count < 3 ? "med" : "low";
    return { walmart_count: count, gap };
  } catch {
    return { walmart_count: -1, gap: "unknown" };
  }
}

export function amazonCompositeFromProduct(p: RainforestProductPayload): number {
  const sellerCount = p.marketplace_sellers_count ?? 99;
  const bsr = bsrFromProduct(p);
  const rating = p.rating ?? 0;
  const reviewCount = p.ratings_total ?? 0;

  const sellerScore = Math.max(0, 100 - sellerCount * 8);
  const bsrScore =
    bsr != null ? Math.max(0, 100 - bsr / 500) : 30;
  const reviewScore =
    reviewCount > 20 ? Math.min(rating * 15, 75) : 10;

  return Math.round(sellerScore * 0.5 + bsrScore * 0.3 + reviewScore * 0.2);
}

export function arbitrageScore(
  trend: number,
  redditSignal: "high" | "med" | "low",
  walmartGap: "high" | "med" | "low" | "unknown",
  amazonComposite: number,
): number {
  const trendPts = Math.min(trend, 100) * 0.35;
  const redditPts =
    ({ high: 100, med: 50, low: 10 }[redditSignal] ?? 0) * 0.2;
  const walmartPts =
    ({ high: 100, med: 50, low: 10, unknown: 30 }[walmartGap] ?? 0) * 0.15;
  const amazonPts = amazonComposite * 0.3;
  return Math.round(trendPts + redditPts + walmartPts + amazonPts);
}

function recommendationFromScore(score: number, saturated: boolean): Recommendation {
  if (score >= 74 && !saturated) return "Import";
  if (score < 42 || saturated) return "Avoid";
  return "Watch";
}

export function opportunityFromArbitrage(args: {
  score: number;
  displayName: string;
  trend: number;
  redditMentions: number;
  redditSignal: "high" | "med" | "low";
  walmartGap: "high" | "med" | "low" | "unknown";
  amazonComposite: number;
}): OpportunityResult {
  const saturated = false;
  const rec = recommendationFromScore(args.score, saturated);
  const bullets = [
    `12‑month US Google Trends interest (avg): ${args.trend}`,
    `Reddit mentions in tracked subs: ${args.redditMentions} (${args.redditSignal})`,
    `Walmart search gap signal: ${args.walmartGap}`,
    `Amazon composite (sellers / BSR / reviews): ${args.amazonComposite}`,
  ];

  return {
    opportunityScore: Math.min(100, Math.max(0, Math.round(args.score))),
    recommendation: rec,
    confidenceLevel: "Medium",
    explanationBullets: bullets,
    headlineReason: bullets[0],
    cardExplanation: bullets[0].slice(0, 92),
    rankImprovement7d: Math.min(40, Math.round(args.trend / 4)),
    reviewGrowth7d: Math.min(80, Math.round(args.amazonComposite / 2)),
    uniqueSignalDays: 4,
    snapshotCount: 4,
    moversHits: 0,
    bestSellersHits: 0,
    newReleasesHits: 0,
    searchHits: 1,
    improvingSnapshotPairs: 1,
    saturatedIncumbent: false,
  };
}
