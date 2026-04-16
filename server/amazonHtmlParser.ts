import * as cheerio from "cheerio";
import { fetchAmazonPageHtml } from "./scraperClient";

/** Same shape the feed builder expects. */
export interface ScrapedAmazonRow {
  asin?: string;
  rank?: number;
  position?: number;
  title?: string;
  link?: string;
  image?: string;
  rating?: number;
  ratings_total?: number;
  price?: { value?: number; raw?: string; symbol?: string; currency?: string };
}

const ASIN_RE = /^[A-Z0-9]{10}$/;

function parsePriceText(raw: string): number | undefined {
  const cleaned = raw.replace(/[^\d.,]/g, "").replace(/,/g, "");
  const n = parseFloat(cleaned);
  return Number.isFinite(n) ? n : undefined;
}

function parseRatingFromAria(label: string): number | undefined {
  const m = label.match(/([\d.]+)\s+out of 5/);
  if (m) return parseFloat(m[1]);
  return undefined;
}

function parseReviewCount(text: string): number | undefined {
  const m = text.replace(/,/g, "").match(/(\d[\d,]*)/);
  if (!m) return undefined;
  const n = parseInt(m[1].replace(/,/g, ""), 10);
  return Number.isFinite(n) ? n : undefined;
}

function extractRowFromCard(
  $: cheerio.CheerioAPI,
  $card: cheerio.Cheerio<unknown>,
): ScrapedAmazonRow | null {
  const asinRaw =
    $card.attr("data-asin") ||
    $card.find("[data-asin]").first().attr("data-asin") ||
    "";
  const asin = asinRaw.trim().toUpperCase();
  if (!ASIN_RE.test(asin)) return null;

  let rank = 9999;
  const badgeTxt = $card.find("span.zg-badge-text, .zg-badge-text").first().text();
  const br = badgeTxt.match(/#?\s*(\d+)/);
  if (br) rank = parseInt(br[1], 10);

  const title =
    $card.find("img[alt]").not('[alt*="Amazon"]').first().attr("alt")?.trim() ||
    $card.find('span[id^="productTitle"], .p13n-sc-truncate, h2 span').first().text().trim() ||
    $card.find("a.a-link-normal span").first().text().trim() ||
    "Unknown product";

  const linkEl = $card.find('a[href*="/dp/"], a[href*="/gp/product/"]').first();
  const href = linkEl.attr("href") ?? "";

  const img =
    $card.find("img[src]").not('[src*="transparent"]').first().attr("src") ||
    $card.find("img[data-src]").first().attr("data-src") ||
    "";

  const priceRaw =
    $card.find("span.a-price .a-offscreen").first().text() ||
    $card.find(".a-price-whole").first().text();
  const priceVal = parsePriceText(priceRaw);

  const aria = $card.find('[aria-label*="out of 5"]').first().attr("aria-label") ?? "";
  const rating = parseRatingFromAria(aria);
  const rcText =
    $card.find("span[aria-label*='ratings'], a[aria-label*='ratings']").first().attr("aria-label") ?? "";
  const ratings_total = parseReviewCount(rcText);

  return {
    asin,
    rank,
    position: rank,
    title,
    link: href.startsWith("http") ? href : href ? `https://www.amazon.com${href}` : undefined,
    image: img,
    rating,
    ratings_total,
    price:
      priceVal !== undefined
        ? { value: priceVal, raw: priceRaw, symbol: "$", currency: "USD" }
        : undefined,
  };
}

/**
 * Best Sellers / Movers / New Releases — zgbs-style grids.
 */
export function parseAmazonBestsellersHtml(html: string): ScrapedAmazonRow[] {
  const $ = cheerio.load(html);
  const out: ScrapedAmazonRow[] = [];
  const seen = new Set<string>();

  const itemRoots = [
    'div[id^="zg-item-"]',
    "li.zg-item-immersion",
    "div.zg-grid-general-faceout",
  ];

  for (const sel of itemRoots) {
    $(sel).each((idx, el) => {
      const $card = $(el);
      const row = extractRowFromCard($, $card);
      if (!row || seen.has(row.asin!)) return;
      seen.add(row.asin!);
      if (row.rank === 9999) {
        row.rank = idx + 1;
        row.position = row.rank;
      }
      out.push(row);
    });
    if (out.length > 0) break;
  }

  if (out.length === 0) {
    return parseAmazonSearchHtml(html);
  }
  return out.sort((a, b) => (a.rank ?? 9999) - (b.rank ?? 9999));
}

/**
 * Search results page.
 */
export function parseAmazonSearchHtml(html: string): ScrapedAmazonRow[] {
  const $ = cheerio.load(html);
  const out: ScrapedAmazonRow[] = [];
  const seen = new Set<string>();

  $(
    'div[data-component-type="s-search-result"][data-asin], div.s-result-item[data-asin], div[role="listitem"][data-asin]',
  ).each((idx, el) => {
    const $el = $(el);
    const asin = ($el.attr("data-asin") ?? "").trim().toUpperCase();
    if (!ASIN_RE.test(asin) || seen.has(asin)) return;
    seen.add(asin);

    const pos = idx + 1;
    const h2 = $el.find("h2 a span, h2 span.a-text-normal").first();
    const title = h2.text().trim() || "Unknown product";
    const link = $el.find("h2 a").first().attr("href") ?? "";
    const img =
      $el.find("img.s-image").first().attr("src") ||
      $el.find("img").first().attr("src") ||
      "";

    const priceRaw = $el.find("span.a-price .a-offscreen").first().text();
    const priceVal = parsePriceText(priceRaw);

    const aria = $el.find('[aria-label*="out of 5 stars"]').first().attr("aria-label") ?? "";
    const rating = parseRatingFromAria(aria);
    const ratingsText = $el.find("span[aria-label*='ratings']").first().attr("aria-label") ?? "";
    const ratings_total = parseReviewCount(ratingsText);

    out.push({
      asin,
      rank: pos,
      position: pos,
      title,
      link: link.startsWith("http") ? link : link ? `https://www.amazon.com${link}` : undefined,
      image: img,
      rating,
      ratings_total,
      price:
        priceVal !== undefined
          ? { value: priceVal, raw: priceRaw, symbol: "$", currency: "USD" }
          : undefined,
    });
  });

  return out;
}

export async function fetchAndParseBestsellers(pageUrl: string): Promise<ScrapedAmazonRow[]> {
  const html = await fetchAmazonPageHtml(pageUrl);
  return parseAmazonBestsellersHtml(html);
}

export function amazonSearchUrl(domain: string, query: string): string {
  const d = domain.replace(/^www\./, "").trim();
  const host = d.includes(".") ? `www.${d}` : `www.${d}`;
  return `https://${host}/s?k=${encodeURIComponent(query)}`;
}

export async function fetchAndParseSearch(
  domain: string,
  searchTerm: string,
): Promise<ScrapedAmazonRow[]> {
  const url = amazonSearchUrl(domain, searchTerm);
  const html = await fetchAmazonPageHtml(url);
  return parseAmazonSearchHtml(html);
}
