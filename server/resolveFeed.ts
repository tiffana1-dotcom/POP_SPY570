import type { EnrichedProduct } from "../src/data/catalog";
import { buildEnrichedProductsFromGpt } from "./gptFeed";
import { buildEnrichedProductsFromScraper } from "./feedBuilder";
import { buildEnrichedProductsFromRainforest } from "./rainforestFeed";
import { hasScrapeCredentials } from "./scraperClient";
import { loadFeedSnapshot } from "./snapshotFeed";

function retailerKey(p: EnrichedProduct): string {
  return `${p.retailer ?? "amazon"}:${p.asin}`;
}

/** Snapshot rows first (e.g. Yamibuy), then live Amazon — same retailer+asin wins from `live`. */
export function mergeByRetailerAsin(
  snapshot: EnrichedProduct[],
  live: EnrichedProduct[],
): EnrichedProduct[] {
  const map = new Map<string, EnrichedProduct>();
  for (const p of snapshot) map.set(retailerKey(p), p);
  for (const p of live) map.set(retailerKey(p), p);
  return [...map.values()];
}

/**
 * `FEED_MODE`:
 * - `gpt` — OpenAI generates demo radar SKUs (default; needs OPENAI_API_KEY)
 * - `scraper` — HTML scrape via ScraperAPI / Bright Data
 * - `snapshot` — JSON only (`server/data/feed-snapshot.json` or example)
 * - `combined` — snapshot + live Amazon scrape
 * - `rainforest` — Rainforest API search+product (real images), plus Trends/Reddit/Walmart arbitrage score
 */
export async function resolveFeed(): Promise<EnrichedProduct[]> {
  const mode = (process.env.FEED_MODE ?? "gpt").toLowerCase();

  if (mode === "snapshot") {
    return loadFeedSnapshot();
  }

  if (mode === "rainforest") {
    return buildEnrichedProductsFromRainforest();
  }

  if (mode === "combined") {
    const snap = loadFeedSnapshot();
    if (!hasScrapeCredentials()) return snap;
    try {
      const live = await buildEnrichedProductsFromScraper();
      return mergeByRetailerAsin(snap, live);
    } catch {
      return snap;
    }
  }

  if (mode === "gpt") {
    return buildEnrichedProductsFromGpt();
  }

  if (!hasScrapeCredentials()) {
    throw new Error(
      "Missing scrape credentials, or use FEED_MODE=gpt (OPENAI_API_KEY), FEED_MODE=rainforest (RAINFOREST_API_KEY), or FEED_MODE=snapshot.",
    );
  }
  return buildEnrichedProductsFromScraper();
}
