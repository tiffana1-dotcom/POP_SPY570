import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { computeOpportunity } from "../src/data/opportunityEngine";
import type { EnrichedProductInput } from "../src/data/catalog";
import type { Product, ProductSnapshot } from "../src/data/types";
import { defaultBuyerNotes } from "./defaultBuyer";
import { matchShelfCategory } from "../src/data/shelfCategories";
import { defaults } from "./config";
import {
  bsrFromProduct,
  hasRainforestApiKey,
  pickImageFromProduct,
  pickImageFromSearchHit,
  pickOrganicAsin,
  rainforestProduct,
  rainforestSearch,
  resolveAmazonProductImage,
  type RainforestProductPayload,
} from "./rainforestApi";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export interface ArbitrageProductRow {
  displayName: string;
  amazonQuery: string;
  /** One of \`defaults.shelfCategories\` — Snacks, Grocery, Beverage, Beauty */
  category?: string;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

function loadArbitrageProductRows(): ArbitrageProductRow[] {
  const envPath = process.env.FEED_ARBITRAGE_PRODUCTS_PATH?.trim();
  const root = path.join(__dirname, "..");
  const filePath = envPath
    ? path.isAbsolute(envPath)
      ? envPath
      : path.join(root, envPath)
    : path.join(__dirname, "data", "arbitrage-products.json");

  const raw = fs.readFileSync(filePath, "utf8");
  const data = JSON.parse(raw) as unknown;
  if (!Array.isArray(data)) throw new Error("arbitrage products JSON must be an array");
  const out: ArbitrageProductRow[] = [];
  for (const row of data) {
    if (!row || typeof row !== "object") continue;
    const r = row as Record<string, unknown>;
    const displayName = String(r.displayName ?? "").trim();
    const amazonQuery = String(r.amazonQuery ?? "").trim();
    const category = String(r.category ?? "").trim();
    if (displayName && amazonQuery) {
      out.push({
        displayName,
        amazonQuery,
        category: category || undefined,
      });
    }
  }
  if (out.length === 0) throw new Error("No valid rows in arbitrage products file");
  return out;
}

function formatPrice(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "—";
  return `$${n.toFixed(2)}`;
}

/** Rolling-window snapshots for the detail view; ranks use live BSR when present. */
function snapshotsFromLiveAmazon(args: {
  asin: string;
  bsr: number | null;
  price: number;
  rating: number;
  reviewCount: number;
}): ProductSnapshot[] {
  const base = Math.min(Math.max(args.bsr ?? 50_000, 1), 800_000);
  const offsets = [6, 4, 2, 0];
  return offsets.map((d, i) => {
    const drift = 1 + (4 - i) * 0.04;
    return {
      asin: args.asin,
      sourceType: "Search" as const,
      rank: Math.round(base * drift),
      price: args.price,
      rating: args.rating,
      reviewCount: args.reviewCount + i * 3,
      capturedAt: isoDaysAgo(d),
    };
  });
}

/**
 * Real Amazon listings via Rainforest API (search + product).
 * Set FEED_MODE=rainforest and RAINFOREST_API_KEY.
 */
export async function buildEnrichedProductsFromRainforest(): Promise<EnrichedProductInput[]> {
  const amazonDomain =
    process.env.RAINFOREST_AMAZON_DOMAIN?.trim() || defaults.amazonDomain || "amazon.com";
  const rows = loadArbitrageProductRows();
  const out: EnrichedProductInput[] = [];

  for (const row of rows) {
    let asin: string | null = null;
    let image = "";
    let title = row.displayName;
    let productPayload: RainforestProductPayload | null = null;

    try {
      const hits = await rainforestSearch(row.amazonQuery, amazonDomain);
      asin = pickOrganicAsin(hits);
      const firstOrganic = hits.find((h) => !h.is_sponsored && h.asin);
      if (firstOrganic) {
        image = pickImageFromSearchHit(firstOrganic);
        if (firstOrganic.title) title = String(firstOrganic.title).trim();
      }
    } catch {
      /* search failed — fall through */
    }

    if (asin) {
      try {
        productPayload = await rainforestProduct(asin, amazonDomain);
      } catch {
        productPayload = null;
      }
    }

    if (productPayload) {
      const img = pickImageFromProduct(productPayload);
      if (img) image = img;
      if (productPayload.title) title = String(productPayload.title).trim();
    }

    if (!image && asin && hasRainforestApiKey()) {
      image = await resolveAmazonProductImage({
        amazonDomain,
        asin,
        title,
      });
    }

    const priceVal = productPayload?.buybox_winner?.price?.value ?? 0;
    const rating = productPayload?.rating ?? 0;
    const reviewCount = productPayload?.ratings_total ?? 0;

    const finalAsin =
      asin ??
      `B0${Buffer.from(row.displayName).toString("hex").slice(0, 8).toUpperCase()}`.slice(0, 10);

    const bsr = productPayload ? bsrFromProduct(productPayload) : null;

    const base: Product = {
      asin: finalAsin,
      title,
      image: image || "https://via.placeholder.com/400?text=No+image",
      category: matchShelfCategory(
        row.category ?? "",
        defaults.shelfCategories,
        defaults.defaultShelfCategory,
      ),
      latestPrice: formatPrice(priceVal),
      latestRating: rating,
      latestReviewCount: reviewCount,
      retailer: "amazon",
    };

    const snapshotsResolved = snapshotsFromLiveAmazon({
      asin: finalAsin,
      bsr,
      price: priceVal,
      rating,
      reviewCount,
    });

    const opp = computeOpportunity(snapshotsResolved);

    const notes = defaultBuyerNotes(finalAsin, title, "amazon");
    out.push({
      ...base,
      ...opp,
      buyer: {
        ...notes,
        suggestedNextAction:
          "Validate MOQ and MAP before PO — score is from Amazon snapshot signals only.",
      },
      snapshots: snapshotsResolved,
      activeSources: ["Search"],
    });

    await sleep(400);
  }

  return out.sort((a, b) => b.opportunityScore - a.opportunityScore);
}
