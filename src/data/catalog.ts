import type { OpportunityResult } from "./opportunityEngine";
import type { Product, ProductBuyerNotes, ProductSnapshot } from "./types";

export interface EnrichedProduct extends Product, OpportunityResult {
  buyer: ProductBuyerNotes;
  snapshots: ProductSnapshot[];
  /** Distinct signal lists seen in the rolling window */
  activeSources: string[];
}

export function findEnrichedByAsin(
  products: EnrichedProduct[],
  asin: string,
): EnrichedProduct | undefined {
  return products.find((p) => p.asin === asin);
}

/** @deprecated Use findEnrichedByAsin(products, id) */
export function getEnrichedByAsin(
  products: EnrichedProduct[],
  asin: string,
): EnrichedProduct | undefined {
  return findEnrichedByAsin(products, asin);
}
