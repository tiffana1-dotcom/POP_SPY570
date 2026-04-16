import type { ProductBuyerNotes, Retailer } from "../src/data/types";

export function defaultBuyerNotes(
  asin: string,
  title: string,
  retailer: Retailer = "amazon",
): ProductBuyerNotes {
  const marketplaces =
    retailer === "yamibuy"
      ? ["Yamibuy", "Amazon US"]
      : ["Amazon US"];
  return {
    marketplaces,
    suggestedNextAction:
      "Validate MAP, lead time, and MOQ with the brand or manufacturer; align with your regional retail plan.",
    sourcingStrategy:
      "Start with a limited buy or exclusive pilot where margin and velocity support it.",
    suggestedPriceRange:
      retailer === "yamibuy"
        ? "Compare Yamibuy shelf price vs Amazon ethnic set; confirm MAP if brand enforces cross-channel."
        : "Use live Amazon Buy Box as a reference; negotiate distributor tiers separately.",
    targetChannels: ["Regional grocery", "Natural / specialty", "E‑commerce"],
    riskLevel: "Medium",
    manufacturerEmailSubject: `Distribution inquiry — ${title.slice(0, 80)} (${asin})`,
    manufacturerEmailBody: `Hello,

We are evaluating assortment opportunities in the CPG space and noticed strong Amazon signals for this SKU. Could you share MOQ, lead times, and whether you work with distributors in our region?

Product: ${title}
ASIN: ${asin}

Best regards,
[Your name]
[Company]`,
  };
}
