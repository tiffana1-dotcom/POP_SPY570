import type { EnrichedProduct, EnrichedProductInput } from "../src/data/catalog";
import { buildEnrichedProductsFromGpt } from "./gptFeed";
import { buildEnrichedProductsFromScraper } from "./feedBuilder";
import { buildEnrichedProductsFromRainforest } from "./rainforestFeed";
import { attachPopLayer } from "./popEnrichment";
import { hasScrapeCredentials } from "./scraperClient";
import { loadFeedSnapshot } from "./snapshotFeed";

function retailerKey(p: EnrichedProductInput): string {
  return `${p.retailer ?? "amazon"}:${p.asin}`;
}

/** Snapshot rows first (e.g. Yamibuy), then live Amazon — same retailer+asin wins from `live`. */
export function mergeByRetailerAsin(
  snapshot: EnrichedProductInput[],
  live: EnrichedProductInput[],
): EnrichedProductInput[] {
  const map = new Map<string, EnrichedProductInput>();
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
 * - `rainforest` — Rainforest API search+product (real images), scored from Amazon snapshots
 */
export async function resolveFeed(): Promise<EnrichedProduct[]> {
  const mode = (process.env.FEED_MODE ?? "gpt").toLowerCase();

  let products: EnrichedProductInput[];

  if (mode === "snapshot") {
    products = loadFeedSnapshot();
  } else if (mode === "rainforest") {
    products = await buildEnrichedProductsFromRainforest();
  } else if (mode === "combined") {
    const snap = loadFeedSnapshot();
    if (!hasScrapeCredentials()) {
      products = snap;
    } else {
      try {
        const live = await buildEnrichedProductsFromScraper();
        products = mergeByRetailerAsin(snap, live);
      } catch {
        products = snap;
      }
    }
  } else if (mode === "gpt") {
    products = await buildEnrichedProductsFromGpt();
  } else if (!hasScrapeCredentials()) {
    throw new Error(
      "Missing scrape credentials, or use FEED_MODE=gpt (OPENAI_API_KEY), FEED_MODE=rainforest (RAINFOREST_API_KEY), or FEED_MODE=snapshot.",
    );
  } else {
    products = await buildEnrichedProductsFromScraper();
  }

  return attachPopLayer(products);
}
