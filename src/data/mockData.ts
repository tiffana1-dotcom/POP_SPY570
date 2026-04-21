/** Barrel — types, aggregates, and catalog helpers (live data loads via /api/feed). */
export * from "./types";
export type { EnrichedProduct } from "./catalog";
export { findEnrichedByAsin, getEnrichedByAsin } from "./catalog";
export {
  buildCategoryTrendsFromProducts,
  buildDashboardKpisFromProducts,
} from "./aggregates";
