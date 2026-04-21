export type SourceType =
  | "Best Sellers"
  | "Movers & Shakers"
  | "New Releases"
  | "Search";

export type Recommendation = "Import" | "Watch" | "Avoid";

export type ConfidenceLevel = "High" | "Medium" | "Low";

export type CategoryHeat = "Heating Up" | "Stable" | "Saturated";

export type AlertSeverity = "Info" | "Elevated" | "Critical";

/** Sales channel the row was sourced from (Amazon vs specialty Asian e‑commerce, etc.) */
export type Retailer = "amazon" | "yamibuy";

export interface Product {
  /** Stable id in the app — Amazon ASIN or another retailer SKU string */
  asin: string;
  title: string;
  image: string;
  category: string;
  latestPrice: string;
  latestRating: number;
  latestReviewCount: number;
  /** Defaults to Amazon when omitted (live scrape / snapshot feed) */
  retailer?: Retailer;
}

export interface ProductSnapshot {
  asin: string;
  sourceType: SourceType;
  rank: number;
  price: number;
  rating: number;
  reviewCount: number;
  capturedAt: string;
}

/** Static buyer-facing fields not derived from snapshots */
export interface ProductBuyerNotes {
  marketplaces: string[];
  suggestedNextAction: string;
  sourcingStrategy: string;
  suggestedPriceRange: string;
  targetChannels: string[];
  riskLevel: "Low" | "Medium" | "High";
  manufacturerEmailSubject: string;
  manufacturerEmailBody: string;
}

export interface CategoryTrend {
  id: string;
  name: string;
  /** Composite momentum vs prior week (mock-derived / computed). */
  momentum7dPct: number;
  heat: CategoryHeat;
  /** Short explanation for buyers */
  summary: string;
}

export interface WatchlistEntry {
  asin: string;
  /** Simulated prior-day score for monitoring deltas */
  yesterdayOpportunity: number;
  severity: AlertSeverity;
  /** One-line monitoring summary */
  statusSummary: string;
}
