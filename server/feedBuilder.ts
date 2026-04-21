import { computeOpportunity } from "../src/data/opportunityEngine";
import type { Product } from "../src/data/types";
import type { ProductSnapshot } from "../src/data/types";
import type { EnrichedProductInput } from "../src/data/catalog";
import { defaultBuyerNotes } from "./defaultBuyer";
import {
  fetchAndParseBestsellers,
  fetchAndParseSearch,
  type ScrapedAmazonRow,
} from "./amazonHtmlParser";
import { defaults } from "./config";
import { hasRainforestApiKey, resolveAmazonProductImage } from "./rainforestApi";

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

type SourceKey = "bs" | "movers" | "nr";

const SOURCE_TYPE: Record<SourceKey, ProductSnapshot["sourceType"]> = {
  bs: "Best Sellers",
  movers: "Movers & Shakers",
  nr: "New Releases",
};

function formatPrice(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "—";
  return `$${n.toFixed(2)}`;
}

function pickPrimaryAppearance(
  appearances: { rank: number; row: ScrapedAmazonRow }[],
) {
  return appearances.reduce((a, b) => (a.rank <= b.rank ? a : b));
}

function searchRowToBestseller(
  row: ScrapedAmazonRow,
  fallbackPosition: number,
): ScrapedAmazonRow {
  const pos = row.position ?? row.rank ?? fallbackPosition;
  return {
    ...row,
    position: pos,
    rank: pos,
  };
}

/** Live Amazon lists via ScraperAPI or Bright Data proxy (HTML fetch + parse). */
export async function buildEnrichedProductsFromScraper(): Promise<EnrichedProductInput[]> {
  const max = defaults.maxPerList;

  const [rowsBs, rowsMovers, rowsNr, ...searchRowLists] = await Promise.all([
    fetchAndParseBestsellers(defaults.urlBestSellers),
    fetchAndParseBestsellers(defaults.urlMovers),
    fetchAndParseBestsellers(defaults.urlNewReleases),
    ...defaults.searchQueries.map((q) =>
      fetchAndParseSearch(defaults.amazonDomain, q),
    ),
  ]);

  const slices: { key: SourceKey; rows: ScrapedAmazonRow[] }[] = [
    { key: "bs", rows: rowsBs.slice(0, max) },
    { key: "movers", rows: rowsMovers.slice(0, max) },
    { key: "nr", rows: rowsNr.slice(0, max) },
  ];

  const searchSlices: { rows: ScrapedAmazonRow[] }[] = searchRowLists.map((rows) => ({
    rows: rows.slice(0, max).map((row, i) => searchRowToBestseller(row, i + 1)),
  }));

  const merged = new Map<
    string,
    {
      asin: string;
      title: string;
      image: string;
      appearances: {
        sourceType: ProductSnapshot["sourceType"];
        rank: number;
        row: ScrapedAmazonRow;
      }[];
    }
  >();

  for (const { key, rows } of slices) {
    const sourceType = SOURCE_TYPE[key];
    for (const row of rows) {
      const asin = (row.asin ?? "").trim().toUpperCase();
      if (!asin) continue;
      const rank = row.rank ?? row.position ?? 9999;
      const title = row.title?.trim() || "Unknown product";
      const image = row.image?.trim() || "";
      const cur = merged.get(asin);
      const entry = { sourceType, rank, row };
      if (!cur) {
        merged.set(asin, { asin, title, image, appearances: [entry] });
      } else {
        if (title !== "Unknown product") cur.title = title;
        if (image) cur.image = image;
        cur.appearances.push(entry);
      }
    }
  }

  for (const { rows } of searchSlices) {
    const sourceType: ProductSnapshot["sourceType"] = "Search";
    for (const row of rows) {
      const asin = (row.asin ?? "").trim().toUpperCase();
      if (!asin) continue;
      const rank = row.rank ?? row.position ?? 9999;
      const title = row.title?.trim() || "Unknown product";
      const image = row.image?.trim() || "";
      const cur = merged.get(asin);
      const entry = { sourceType, rank, row };
      if (!cur) {
        merged.set(asin, { asin, title, image, appearances: [entry] });
      } else {
        if (title !== "Unknown product") cur.title = title;
        if (image) cur.image = image;
        cur.appearances.push(entry);
      }
    }
  }

  const capturedAt = new Date().toISOString();
  const out: EnrichedProductInput[] = [];

  for (const rec of merged.values()) {
    const snapshots: ProductSnapshot[] = rec.appearances.map((a) => ({
      asin: rec.asin,
      sourceType: a.sourceType,
      rank: a.rank,
      price: a.row.price?.value ?? 0,
      rating: a.row.rating ?? 0,
      reviewCount: a.row.ratings_total ?? 0,
      capturedAt,
    }));

    const opp = computeOpportunity(snapshots);
    const primary = pickPrimaryAppearance(rec.appearances);
    const row = primary.row;
    const priceVal = row.price?.value ?? 0;

    const base: Product = {
      asin: rec.asin,
      title: rec.title,
      image: rec.image || "https://via.placeholder.com/400?text=No+image",
      category: defaults.defaultShelfCategory,
      latestPrice: formatPrice(priceVal),
      latestRating: row.rating ?? 0,
      latestReviewCount: row.ratings_total ?? 0,
      retailer: "amazon",
    };

    out.push({
      ...base,
      ...opp,
      buyer: defaultBuyerNotes(rec.asin, rec.title, "amazon"),
      snapshots,
      activeSources: [...new Set(snapshots.map((s) => s.sourceType))],
    });
  }

  if (hasRainforestApiKey()) {
    const domain = defaults.amazonDomain;
    for (let i = 0; i < out.length; i++) {
      const p = out[i];
      const bad =
        !p.image ||
        /placeholder|picsum\.photos/i.test(p.image);
      if (!bad) continue;
      const img = await resolveAmazonProductImage({
        amazonDomain: domain,
        asin: p.asin,
        title: p.title,
      });
      if (img) {
        out[i] = { ...p, image: img };
      }
      await sleep(120);
    }
  }

  return out;
}
