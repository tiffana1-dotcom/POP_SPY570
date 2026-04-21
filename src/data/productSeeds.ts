import type { ProductBuyerNotes } from "./types";

export interface ProductSeed {
  asin: string;
  title: string;
  image: string;
  category: string;
  buyer: ProductBuyerNotes;
}

export const productSeeds: ProductSeed[] = [
  {
    asin: "B0ADAP01TS",
    title: "Adaptogen Sparkling Tonic — Citrus & Ashwagandha",
    category: "Functional beverages",
    image:
      "https://images.unsplash.com/photo-1622483767028-3f66f29aefb8?w=400&h=400&fit=crop",
    buyer: {
      marketplaces: ["Amazon US", "Amazon CA"],
      suggestedNextAction:
        "Request MOQ and lead time for a 90-day test in club and specialty; reserve shelf for Q3.",
      sourcingStrategy:
        "Start with a single flavor run; negotiate exclusivity on the adaptogen blend for 6 months in your region.",
      suggestedPriceRange: "MAP $27.99–$32.99 (case of 12)",
      targetChannels: ["Regional grocery", "Natural channel", "Corporate gifting"],
      riskLevel: "Medium",
      manufacturerEmailSubject:
        "Partnership inquiry — adaptogen sparkling line (US distribution)",
      manufacturerEmailBody: `Dear Production Team,

We are a US-based CPG distributor focused on functional beverages and wellness adjacencies. We have been tracking strong velocity for adaptogen-forward sparkling tonics in the North American market and believe your Citrus & Ashwagandha profile aligns with our retail partners' assortment goals.

Could you share:
• MOQ, lead times, and co-packing options for a 12-pack format
• Certificates of analysis and allergen statements
• Whether you offer regional exclusivity for specific territories

If helpful, we can schedule a brief call this week to align on pricing tiers and a pilot timeline.

Best regards,
[Your Name]
[Company]
[Phone]`,
    },
  },
  {
    asin: "B0MUSH02LC",
    title: "Lion's Mane Instant Latte Mix — Unsweetened",
    category: "Mushroom coffee",
    image:
      "https://images.unsplash.com/photo-1497935586351-b67a49e012bf?w=400&h=400&fit=crop",
    buyer: {
      marketplaces: ["Amazon US"],
      suggestedNextAction:
        "Secure samples for two anchor accounts; validate café and office-channel fit.",
      sourcingStrategy:
        "Pilot with private-label-ready packaging; prioritize NSF-friendly facilities.",
      suggestedPriceRange: "$19.99–$24.99 (10-serving bag)",
      targetChannels: ["Office coffee", "E‑commerce bundles", "Specialty grocers"],
      riskLevel: "Low",
      manufacturerEmailSubject:
        "Distribution opportunity — lion's mane latte mix (North America)",
      manufacturerEmailBody: `Hello,

Our buying team monitors Amazon velocity and emerging mushroom coffee SKUs. Your unsweetened lion's mane latte mix is showing breakout signals in the US market.

We would appreciate:
• Product spec sheet and ingredient sourcing map
• MOQ and shelf-life for ocean freight
• Reference pricing for distributor tiers

We are evaluating a Q3 launch with two regional retailers and can share forecast ranges under NDA.

Thank you,
[Your Name]
[Company]`,
    },
  },
  {
    asin: "B0HERB03SM",
    title: "Cooling Herbal Tea Sampler — Peppermint & Tulsi",
    category: "Herbal tea",
    image:
      "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400&h=400&fit=crop",
    buyer: {
      marketplaces: ["Amazon US", "Amazon UK"],
      suggestedNextAction:
        "Monitor for two more weeks; if rank holds, request pallet pricing.",
      sourcingStrategy:
        "Hold for confirmation; prioritize suppliers with organic certification if you move.",
      suggestedPriceRange: "$12.99–$15.99",
      targetChannels: ["Natural sets", "Seasonal displays"],
      riskLevel: "Low",
      manufacturerEmailSubject: "Inquiry — herbal tea sampler (potential US partner)",
      manufacturerEmailBody: `Dear Team,

We are following your Cooling Herbal Tea Sampler due to steady Amazon momentum. Before committing to an import run, we would like to understand MOQs, lead times, and whether you support mixed pallets.

Best,
[Your Name]`,
    },
  },
  {
    asin: "B0COL04BT",
    title: "Marine Collagen Peptide Bites — Dark Chocolate Sea Salt",
    category: "Collagen snacks",
    image:
      "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=400&h=400&fit=crop",
    buyer: {
      marketplaces: ["Amazon US"],
      suggestedNextAction:
        "Fast-track supplier call; competitor collagen bars are already copying flavor notes.",
      sourcingStrategy:
        "Negotiate flavor exclusivity window; plan secondary flavor for Q4.",
      suggestedPriceRange: "$29.99–$36.99",
      targetChannels: ["Club", "Specialty", "DTC cross-promo"],
      riskLevel: "Medium",
      manufacturerEmailSubject: "Urgent — collagen bites manufacturing capacity (US)",
      manufacturerEmailBody: `Hello,

We represent a distributor seeing rapid Amazon uptake on marine collagen peptide bites in dark chocolate sea salt. We need to understand current capacity, lead times, and whether you can support a phased rollout (pilot → regional).

Please advise on MOQ and export documentation timelines.

Regards,
[Your Name]`,
    },
  },
  {
    asin: "B0VIT05EF",
    title: "Buffered Vitamin C + Zinc Effervescent — Travel Pack",
    category: "Vitamins / supplements",
    image:
      "https://images.unsplash.com/photo-1584308666744-24d5e474f2ae?w=400&h=400&fit=crop",
    buyer: {
      marketplaces: ["Amazon US", "Amazon MX"],
      suggestedNextAction:
        "Add to seasonal buy plan; confirm regulatory labeling for your state set.",
      sourcingStrategy:
        "Dual-source if volumes spike; keep backup supplier qualified.",
      suggestedPriceRange: "$16.99–$19.99",
      targetChannels: ["Drug", "Travel retail", "E‑commerce"],
      riskLevel: "Medium",
      manufacturerEmailSubject: "Vitamin C + zinc effervescent — capacity check",
      manufacturerEmailBody: `Dear Supplier,

We are evaluating additional capacity for a buffered vitamin C + zinc effervescent travel pack. Please share MOQ, lead times, and COA turnaround.

Thank you,
[Your Name]`,
    },
  },
  {
    asin: "B0ELEC06HY",
    title: "Electrolyte Hydration Mix — Watermelon (No Sugar)",
    category: "Functional beverages",
    image:
      "https://images.unsplash.com/photo-1523362628745-0c09033e485e?w=400&h=400&fit=crop",
    buyer: {
      marketplaces: ["Amazon US"],
      suggestedNextAction:
        "Compare against top 3 competitors' price-per-serving before committing.",
      sourcingStrategy: "Defer large MOQ until velocity inflects.",
      suggestedPriceRange: "$21.99–$26.99",
      targetChannels: ["Grocery", "Fitness"],
      riskLevel: "Medium",
      manufacturerEmailSubject: "Information request — electrolyte mix",
      manufacturerEmailBody: `Hello,

We are benchmarking electrolyte mixes. Please share spec sheet and distributor pricing.

Thanks,
[Your Name]`,
    },
  },
  {
    asin: "B0OTC07MG",
    title: "Nighttime Magnesium Glycinate — 120ct",
    category: "OTC wellness products",
    image:
      "https://images.unsplash.com/photo-1471864190281-a93a3070d6de?w=400&h=400&fit=crop",
    buyer: {
      marketplaces: ["Amazon US"],
      suggestedNextAction:
        "Skip import; if already stocked, promote only on margin-positive promos.",
      sourcingStrategy:
        "Not recommended for new distribution unless private label.",
      suggestedPriceRange: "$17.99–$22.99",
      targetChannels: ["Drug (promo only)"],
      riskLevel: "High",
      manufacturerEmailSubject: "Not pursuing at this time — magnesium glycinate",
      manufacturerEmailBody: `Dear Team,

Thank you for your patience. We will not move forward with a new import on this SKU due to category saturation in our markets. We may revisit if formulation differentiation improves.

Best,
[Your Name]`,
    },
  },
  {
    asin: "B0PROB08GS",
    title: "Probiotic Gut Shot — Ginger Lime",
    category: "Functional beverages",
    image:
      "https://images.unsplash.com/photo-1544145945-f90425340c7e?w=400&h=400&fit=crop",
    buyer: {
      marketplaces: ["Amazon US", "Amazon CA"],
      suggestedNextAction:
        "Prioritize cold-chain feasibility discussion and retailer demo dates.",
      sourcingStrategy:
        "Partner with a facility experienced in live cultures and short shelf life.",
      suggestedPriceRange: "$34.99–$42.99",
      targetChannels: ["Natural", "Prepared foods perimeter"],
      riskLevel: "Medium",
      manufacturerEmailSubject: "Cold chain distribution — probiotic gut shot",
      manufacturerEmailBody: `Hello,

We are impressed by early US velocity on your probiotic gut shot. We need to understand shelf life, cold-chain requirements, and export documentation timing.

Please propose a call this week.

Regards,
[Your Name]`,
    },
  },
];
