import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { computeOpportunity } from "../src/data/opportunityEngine";
import type { EnrichedProduct } from "../src/data/catalog";
import type { Product, ProductSnapshot, Retailer, SourceType } from "../src/data/types";
import { defaultBuyerNotes } from "./defaultBuyer";

const SOURCE_TYPES: SourceType[] = [
  "Best Sellers",
  "Movers & Shakers",
  "New Releases",
  "Search",
];

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

function parseOne(raw: unknown): { base: Product; snapshots: ProductSnapshot[] } {
  if (!isRecord(raw)) throw new Error("Each snapshot row must be an object");
  const asin = String(raw.asin ?? "").trim();
  if (!asin) throw new Error("snapshot item missing asin");
  const title = String(raw.title ?? "Unknown product").trim();
  const image = String(raw.image ?? "").trim();
  const category = String(raw.category ?? "Uncategorized").trim();
  const latestPrice = String(raw.latestPrice ?? "—");
  const lr = Number(raw.latestRating);
  const lrc = Number(raw.latestReviewCount);
  const retailer: Retailer = raw.retailer === "yamibuy" ? "yamibuy" : "amazon";

  const snapsRaw = raw.snapshots;
  if (!Array.isArray(snapsRaw) || snapsRaw.length === 0) {
    throw new Error(`snapshots[] required for ${asin}`);
  }

  const snapshots: ProductSnapshot[] = snapsRaw.map((s, i) => {
    if (!isRecord(s)) throw new Error(`snapshot[${i}] invalid`);
    const st = s.sourceType;
    if (typeof st !== "string" || !SOURCE_TYPES.includes(st as SourceType)) {
      throw new Error(`snapshot[${i}].sourceType invalid`);
    }
    return {
      asin,
      sourceType: st as SourceType,
      rank: Number(s.rank) || 0,
      price: Number(s.price) || 0,
      rating: Number(s.rating) || 0,
      reviewCount: Number(s.reviewCount) || 0,
      capturedAt: String(s.capturedAt || new Date().toISOString()),
    };
  });

  const base: Product = {
    asin,
    title,
    image: image || "https://via.placeholder.com/400?text=No+image",
    category,
    latestPrice,
    latestRating: Number.isFinite(lr) ? lr : 0,
    latestReviewCount: Number.isFinite(lrc) ? lrc : 0,
    retailer,
  };

  return { base, snapshots };
}

/**
 * Load merged catalog from JSON (manual edits, scraper output, or exports).
 * Prefer `server/data/feed-snapshot.json`; fall back to `feed-snapshot.example.json`.
 */
export function loadFeedSnapshot(): EnrichedProduct[] {
  const root = process.cwd();
  const preferred = path.join(root, "server", "data", "feed-snapshot.json");
  const example = path.join(root, "server", "data", "feed-snapshot.example.json");
  const file = existsSync(preferred) ? preferred : example;
  const text = readFileSync(file, "utf-8");
  const data = JSON.parse(text) as unknown;
  if (!Array.isArray(data)) throw new Error("feed snapshot must be a JSON array");

  const out: EnrichedProduct[] = [];
  for (const row of data) {
    const { base, snapshots } = parseOne(row);
    const opp = computeOpportunity(snapshots);
    const activeSources = [...new Set(snapshots.map((s) => s.sourceType))];
    out.push({
      ...base,
      ...opp,
      buyer: defaultBuyerNotes(base.asin, base.title, base.retailer ?? "amazon"),
      snapshots,
      activeSources,
    });
  }
  return out;
}
