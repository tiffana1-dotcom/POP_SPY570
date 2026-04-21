import type { OpportunityResult } from "./opportunityEngine";
import type { PopOpportunityFields } from "./popDiscovery";
import type { Product, ProductBuyerNotes, ProductSnapshot } from "./types";

export interface EnrichedProduct extends Product, OpportunityResult {
  buyer: ProductBuyerNotes;
  snapshots: ProductSnapshot[];
  /** Distinct signal lists seen in the rolling window */
  activeSources: string[];
  /** PoP sourcing: shelf-life / FDA / tariff heuristics + line ideas (server-side) */
  pop: PopOpportunityFields;
}

/** Built by feed modes before PoP compliance + Yami snapshot layer is attached. */
export type EnrichedProductInput = Omit<EnrichedProduct, "pop">;

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
