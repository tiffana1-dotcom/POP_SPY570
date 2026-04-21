/**
 * Rainforest API (Amazon search + product) — real ASINs and images.
 * https://www.rainforestapi.com/docs
 */

const BASE = "https://api.rainforestapi.com/request";

export interface RainforestSearchHit {
  asin?: string;
  title?: string;
  is_sponsored?: boolean;
  image?: string | { link?: string };
  /** Some responses use thumbnail instead of image */
  thumbnail?: string | { link?: string };
}

export interface RainforestBsrEntry {
  rank?: number;
}

export interface RainforestProductPayload {
  asin?: string;
  title?: string;
  main_image?: { link?: string } | string;
  image?: string;
  /** Gallery / alternate images */
  images?: Array<{ link?: string } | string>;
  bestsellers_rank?: RainforestBsrEntry[];
  marketplace_sellers_count?: number;
  rating?: number;
  ratings_total?: number;
  buybox_winner?: {
    price?: { value?: number };
    availability?: { type?: string };
  };
}

function getApiKey(): string {
  const k = process.env.RAINFOREST_API_KEY?.trim();
  if (!k) throw new Error("RAINFOREST_API_KEY is not set");
  return k;
}

/** True when Rainforest calls can be made (optional image hydration, etc.). */
export function hasRainforestApiKey(): boolean {
  return Boolean(process.env.RAINFOREST_API_KEY?.trim());
}

function firstHttpString(x: unknown): string {
  if (typeof x === "string") {
    const s = x.trim();
    if (s.startsWith("http")) return s;
  }
  return "";
}

export async function rainforestSearch(
  searchTerm: string,
  amazonDomain: string,
): Promise<RainforestSearchHit[]> {
  const params = new URLSearchParams({
    api_key: getApiKey(),
    type: "search",
    amazon_domain: amazonDomain,
    search_term: searchTerm,
  });
  const r = await fetch(`${BASE}?${params.toString()}`);
  if (!r.ok) throw new Error(`Rainforest search HTTP ${r.status}`);
  const data = (await r.json()) as { search_results?: RainforestSearchHit[] };
  return Array.isArray(data.search_results) ? data.search_results : [];
}

export async function rainforestProduct(
  asin: string,
  amazonDomain: string,
): Promise<RainforestProductPayload | null> {
  const params = new URLSearchParams({
    api_key: getApiKey(),
    type: "product",
    amazon_domain: amazonDomain,
    asin,
  });
  const r = await fetch(`${BASE}?${params.toString()}`);
  if (!r.ok) throw new Error(`Rainforest product HTTP ${r.status}`);
  const data = (await r.json()) as { product?: RainforestProductPayload };
  return data.product ?? null;
}

export function pickOrganicAsin(hits: RainforestSearchHit[]): string | null {
  const organic = hits.filter((x) => !x.is_sponsored && x.asin);
  const first = organic[0];
  return first?.asin?.trim().toUpperCase() ?? null;
}

export function pickImageFromSearchHit(hit: RainforestSearchHit): string {
  const im = hit.image;
  if (typeof im === "string") {
    const u = firstHttpString(im);
    if (u) return u;
  }
  if (im && typeof im === "object" && typeof im.link === "string") {
    const u = firstHttpString(im.link);
    if (u) return u;
  }
  const th = hit.thumbnail;
  if (typeof th === "string") {
    const u = firstHttpString(th);
    if (u) return u;
  }
  if (th && typeof th === "object" && typeof th.link === "string") {
    const u = firstHttpString(th.link);
    if (u) return u;
  }
  return "";
}

export function pickImageFromProduct(p: RainforestProductPayload): string {
  if (typeof p.image === "string") {
    const u = firstHttpString(p.image);
    if (u) return u;
  }
  const m = p.main_image;
  if (typeof m === "string") {
    const u = firstHttpString(m);
    if (u) return u;
  }
  if (m && typeof m === "object" && typeof m.link === "string") {
    const u = firstHttpString(m.link);
    if (u) return u;
  }
  const imgs = p.images;
  if (Array.isArray(imgs)) {
    for (const entry of imgs) {
      if (typeof entry === "string") {
        const u = firstHttpString(entry);
        if (u) return u;
      }
      if (entry && typeof entry === "object" && typeof entry.link === "string") {
        const u = firstHttpString(entry.link);
        if (u) return u;
      }
    }
  }
  return "";
}

/**
 * Real Amazon listing image for a SKU: product-by-ASIN first, then search-by-title.
 * Use when GPT/demo ASINs are fake or HTML scrape missed `src`.
 */
export async function resolveAmazonProductImage(opts: {
  amazonDomain: string;
  asin: string;
  title: string;
}): Promise<string> {
  if (!hasRainforestApiKey()) return "";
  const domain = opts.amazonDomain.trim() || "amazon.com";
  const asin = opts.asin.trim().toUpperCase();
  const title = opts.title.trim();

  try {
    const prod = await rainforestProduct(asin, domain);
    if (prod) {
      const u = pickImageFromProduct(prod);
      if (u) return u;
    }
  } catch {
    /* invalid ASIN or API error */
  }

  const q = title.slice(0, 120).trim();
  if (!q) return "";

  try {
    const hits = await rainforestSearch(q, domain);
    const organic = hits.filter((h) => !h.is_sponsored);
    const preferAsin = organic.find(
      (h) => h.asin && h.asin.trim().toUpperCase() === asin,
    );
    const row = preferAsin ?? organic[0];
    if (row) {
      const u = pickImageFromSearchHit(row);
      if (u) return u;
    }
  } catch {
    /* ignore */
  }

  return "";
}

export function bsrFromProduct(p: RainforestProductPayload): number | null {
  const list = p.bestsellers_rank;
  if (!Array.isArray(list) || list.length === 0) return null;
  let best = list[0];
  let bestRank = best?.rank ?? 9_999_999;
  for (const x of list) {
    const rk = x.rank ?? 9_999_999;
    if (rk < bestRank) {
      bestRank = rk;
      best = x;
    }
  }
  return typeof best?.rank === "number" ? best.rank : null;
}

/** Heuristic 0–100 strength from live Amazon listing fields (used for diagnostics only). */
export function amazonCompositeFromProduct(p: RainforestProductPayload): number {
  const sellerCount = p.marketplace_sellers_count ?? 99;
  const bsr = bsrFromProduct(p);
  const rating = p.rating ?? 0;
  const reviewCount = p.ratings_total ?? 0;

  const sellerScore = Math.max(0, 100 - sellerCount * 8);
  const bsrScore = bsr != null ? Math.max(0, 100 - bsr / 500) : 30;
  const reviewScore = reviewCount > 20 ? Math.min(rating * 15, 75) : 10;

  return Math.round(sellerScore * 0.5 + bsrScore * 0.3 + reviewScore * 0.2);
}
