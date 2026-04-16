/**
 * Amazon list URLs fetched via ScraperAPI (plain HTML). Adjust for your category.
 *
 * Feed modes (`FEED_MODE`): `gpt` | `scraper` | `snapshot` | `combined` | `rainforest`
 * — `rainforest` needs `RAINFOREST_API_KEY` (also used to hydrate real listing images in
 * `gpt` / `scraper` when set), optional `WALMART_CONSUMER_ID`, and
 * optional toggles `FEED_ENABLE_GOOGLE_TRENDS`, `FEED_ENABLE_REDDIT`, `FEED_ENABLE_WALMART`
 * (all default `1`). Product list: `server/data/arbitrage-products.json` or
 * `FEED_ARBITRAGE_PRODUCTS_PATH`.
 * Shelf filters: `FEED_SHELF_CATEGORIES` (default Snacks,Grocery,Beverage,Beauty) and
 * `FEED_DEFAULT_SHELF_CATEGORY` (default Grocery) for feeds without a per-SKU shelf.
 */
export const defaults = {
  /** e.g. amazon.com — used to build search URLs */
  amazonDomain: process.env.FEED_AMAZON_DOMAIN ?? process.env.AMAZON_DOMAIN ?? "amazon.com",
  urlBestSellers:
    process.env.FEED_URL_BESTSELLERS ??
    "https://www.amazon.com/Best-Sellers-Grocery-Gourmet-Food/zgbs/grocery/",
  urlMovers:
    process.env.FEED_URL_MOVERS ??
    "https://www.amazon.com/gp/movers-and-shakers/grocery/",
  urlNewReleases:
    process.env.FEED_URL_NEW_RELEASES ??
    "https://www.amazon.com/gp/new-releases/grocery/",
  /** Legacy umbrella label (scraper HTML feed still uses this if no shelf category). */
  categoryLabel:
    process.env.FEED_CATEGORY_LABEL ?? "Grocery & Gourmet (Amazon)",
  /**
   * Canonical shelf categories for GPT labeling and filters — comma-separated.
   * Default: Snacks, Grocery, Beverage, Beauty
   */
  shelfCategories: (process.env.FEED_SHELF_CATEGORIES ?? "Snacks,Grocery,Beverage,Beauty")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean),
  /** When a feed mode cannot infer shelf (e.g. scraper), tag rows with this shelf. */
  defaultShelfCategory:
    process.env.FEED_DEFAULT_SHELF_CATEGORY?.trim() || "Grocery",
  /** Max rows per list after HTML parse */
  maxPerList: Math.min(30, Number(process.env.FEED_MAX_PER_LIST) || 15),
  /**
   * Comma-separated search keywords (Amazon search results page).
   * Empty string disables search fetches.
   */
  searchQueries: (process.env.FEED_SEARCH_QUERIES ?? "Lotus Mooncake,Instant Matcha")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean),
};
