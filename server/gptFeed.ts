import { randomBytes } from "node:crypto";
import { computeOpportunity } from "../src/data/opportunityEngine";
import type { EnrichedProduct } from "../src/data/catalog";
import type { Product, ProductSnapshot } from "../src/data/types";
import { defaultBuyerNotes } from "./defaultBuyer";
import { defaults } from "./config";
import { matchShelfCategory } from "../src/data/shelfCategories";
import { openaiChatJson } from "./openaiClient";
import {
  hasRainforestApiKey,
  resolveAmazonProductImage,
} from "./rainforestApi";

interface GptItem {
  asin: string;
  title: string;
  category: string;
  latestPriceUsd: number;
  rating: number;
  reviewCount: number;
  /** Why a buyer might care — shown in UI context */
  trendNote?: string;
}

interface GptFeedPayload {
  items?: GptItem[];
  /** Some models use "products" instead of "items" */
  products?: GptItem[];
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

/** Deterministic per-ASIN mix so GPT demo rows are not identical (~40 / all Avoid). */
function hashAsinMix(asin: string, reviewCount: number): number {
  let h = 2166136261;
  const s = `${asin}:${reviewCount}`;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

/**
 * Synthetic 7d history: ranks / sources / review deltas vary by ASIN so
 * `computeOpportunity` spreads scores (some Import / Watch, not all ~40 Avoid).
 */
function buildSnapshotsForItem(item: GptItem): ProductSnapshot[] {
  const asin = item.asin.trim().toUpperCase();
  const mix = hashAsinMix(asin, item.reviewCount);
  const tier = mix % 5;

  /** Four distinct days in the rolling window (uniqueSignalDays === 4). */
  const dayOffsets = [6, 4, 2, 0];

  /** Rank trajectories: stronger tiers = larger net climb (lower rank = better). */
  const rankSets: [number, number, number, number][] = [
    [88, 62, 35, 9],
    [72, 55, 34, 16],
    [58, 48, 38, 26],
    [50, 44, 39, 32],
    [46, 43, 41, 38],
  ];
  const ranks = rankSets[tier] ?? rankSets[2];

  const sourceSets: ProductSnapshot["sourceType"][][] = [
    ["Movers & Shakers", "Movers & Shakers", "Best Sellers", "Search"],
    ["Movers & Shakers", "Best Sellers", "New Releases", "Search"],
    ["Best Sellers", "Movers & Shakers", "Search", "Best Sellers"],
    ["Search", "Best Sellers", "Movers & Shakers", "Search"],
    ["Best Sellers", "Search", "Best Sellers", "Search"],
  ];
  const sources = sourceSets[tier] ?? sourceSets[2];

  const reviewStep = 2 + (mix % 8);
  return dayOffsets.map((d, i) => ({
    asin,
    sourceType: sources[i] ?? "Best Sellers",
    rank: ranks[i] ?? 40,
    price: item.latestPriceUsd,
    rating: item.rating,
    reviewCount: item.reviewCount + i * reviewStep,
    capturedAt: isoDaysAgo(d),
  }));
}

/** Fallback when Rainforest is off or cannot resolve a listing image. */
function gptFallbackImageUrl(asin: string): string {
  return `https://picsum.photos/seed/${encodeURIComponent(asin)}/400/400`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function formatPrice(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "—";
  return `$${n.toFixed(2)}`;
}

const ASIN_CHARS = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ";

/** Amazon ASINs are 10 alphanumeric chars; models often shorten or add dashes — normalize or synthesize. */
function normalizeAsin(raw: string | undefined, used: Set<string>): string {
  const cleaned = String(raw ?? "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "");
  let candidate = "";
  if (cleaned.length >= 10) {
    candidate = cleaned.slice(0, 10);
  } else if (cleaned.length >= 6) {
    candidate = (cleaned + "0000000000").slice(0, 10);
  }

  if (candidate.length === 10 && /^[A-Z0-9]{10}$/.test(candidate) && !used.has(candidate)) {
    used.add(candidate);
    return candidate;
  }

  for (let attempt = 0; attempt < 50; attempt++) {
    const buf = randomBytes(8);
    let s = "B0";
    for (let i = 0; i < 8; i++) s += ASIN_CHARS[buf[i] % ASIN_CHARS.length];
    const id = s.slice(0, 10);
    if (!used.has(id)) {
      used.add(id);
      return id;
    }
  }
  const fallback = `B0${Date.now().toString(36).toUpperCase().replace(/[^A-Z0-9]/g, "0").slice(-8)}`.slice(0, 10);
  used.add(fallback);
  return fallback;
}

function coerceNumber(v: unknown, fallback: number): number {
  const n = typeof v === "number" ? v : parseFloat(String(v ?? ""));
  return Number.isFinite(n) ? n : fallback;
}

/**
 * LLM-generated “radar” products — not live Amazon data. Good for demos without scrapers.
 */
export async function buildEnrichedProductsFromGpt(): Promise<EnrichedProduct[]> {
  const max = Math.min(20, defaults.maxPerList * 2);
  const themes = defaults.searchQueries.join("; ") || "Asian snacks, tea, pantry staples";

  const payload = await openaiChatJson<GptFeedPayload>({
    system: `You are a CPG and e-commerce analyst. Output valid JSON only (no markdown). 
The JSON must match the schema implied by the user message. 
Use realistic-sounding Amazon-style ASINs: exactly 10 characters, uppercase letters and digits, starting with B.`,
    user: `Generate exactly ${max} distinct plausible CPG / specialty SKUs a US buyer might track on Amazon
(snacks, pantry grocery, beverages, beauty where relevant).
Reference umbrella: "${defaults.categoryLabel}".
Themes to reflect: ${themes}.

Shelf category for each item must be EXACTLY one of: ${defaults.shelfCategories.join(", ")}.
Spread items across these shelves when it makes sense (not all in one shelf).

Return JSON:
{
  "items": [
    {
      "asin": "B0XXXXXXXX",
      "title": "product title",
      "category": "Grocery",
      "latestPriceUsd": 9.99,
      "rating": 4.2,
      "reviewCount": 350,
      "trendNote": "one sentence on why it could matter for assortment planning"
    }
  ]
}

Rules: items.length must be ${max}. Each asin must be exactly 10 alphanumeric characters (or omit asin and we will assign).`,
  });

  const rawList = payload.items ?? payload.products ?? [];
  const items = Array.isArray(rawList) ? rawList : [];
  if (items.length === 0) {
    throw new Error("GPT returned no items — try again or check OPENAI_MODEL");
  }

  const out: EnrichedProduct[] = [];
  const usedAsins = new Set<string>();

  for (const item of items.slice(0, max)) {
    const asin = normalizeAsin(item.asin, usedAsins);
    const priceUsd = coerceNumber(item.latestPriceUsd, 9.99);
    const rating = coerceNumber(item.rating, 4.3);
    const reviewCount = Math.max(0, Math.floor(coerceNumber(item.reviewCount, 100)));

    const normalized: GptItem = {
      asin,
      title: String(item.title ?? "Product").trim() || "Product",
      category: matchShelfCategory(
        String(item.category ?? ""),
        defaults.shelfCategories,
        defaults.defaultShelfCategory,
      ),
      latestPriceUsd: priceUsd,
      rating,
      reviewCount,
      trendNote: item.trendNote,
    };

    const snapshots = buildSnapshotsForItem(normalized);
    const opp = computeOpportunity(snapshots);

    let image = "";
    if (hasRainforestApiKey()) {
      image = await resolveAmazonProductImage({
        amazonDomain: defaults.amazonDomain,
        asin,
        title: normalized.title,
      });
      await sleep(150);
    }
    if (!image) {
      image = gptFallbackImageUrl(asin);
    }

    const base: Product = {
      asin,
      title: normalized.title,
      image,
      category: normalized.category,
      latestPrice: formatPrice(normalized.latestPriceUsd),
      latestRating: normalized.rating,
      latestReviewCount: normalized.reviewCount,
      retailer: "amazon",
    };

    const notes = defaultBuyerNotes(asin, base.title, "amazon");
    out.push({
      ...base,
      ...opp,
      buyer: {
        ...notes,
        suggestedNextAction: normalized.trendNote?.trim() || notes.suggestedNextAction,
      },
      snapshots,
      activeSources: [...new Set(snapshots.map((s) => s.sourceType))],
    });
  }

  if (out.length === 0) {
    throw new Error("Could not map any GPT items to products");
  }
  return out;
}
