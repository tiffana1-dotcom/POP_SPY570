/**
 * PoP (Point of Purchase) buyer-facing discovery layer — compliance heuristics,
 * line-extension ideas, and opportunity angles. Server fills these via `popEnrichment.ts`.
 */

export type PopOpportunityAngle = "distribute_existing" | "develop_pop_branded";

export interface PopOpportunityFields {
  /** PoP taxonomy: dry goods, confections, teas, personal care, health & wellness */
  popCategory: string;
  /** Heuristic: ambient / shelf-stable SKU likely ≥12 months (not legal shelf-life data). */
  shelfLifeExceeds12Months: boolean;
  shelfLifeRationale: string;
  /**
   * Substring match on product title against `server/data/pop-fda-unapproved-ingredients.json`.
   * Not a regulatory determination — verify labels and intended use.
   */
  fdaUnapprovedIngredientHit: boolean;
  /** If no unapproved term appears in the title scan, we label "approved" for this screen only. */
  fdaIngredientListStatus: "approved" | "not_approved";
  fdaRationale: string;
  /** Title-level hint for higher tariff / trade-friction geographies (heuristic). */
  tariffOrTradeRisk: boolean;
  tariffRationale: string;
  countryOfOriginHint: string | null;
  opportunityAngles: PopOpportunityAngle[];
  /** e.g. kombucha + ginger RTD, ginseng + adaptogen snack */
  lineExtensionIdeas: string[];
  buyerActionSummary: string;
  /** How public signals + PoP filters combine for this row */
  compositeContext: string;
}

export interface DiscoveryMeta {
  /** Human-readable public inputs wired in this build */
  publicSources: { id: string; label: string; detail: string }[];
  /** Cached Yami-style ingredient/category pulse (not live browser fetch) */
  yamiSnapshot: {
    asOf: string;
    sourceLabel: string;
    trendingIngredientsSample: string[];
  };
  scoringExplainer: string;
  filteringExplainer: string;
}
