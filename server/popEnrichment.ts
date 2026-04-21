import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { EnrichedProduct, EnrichedProductInput } from "../src/data/catalog";
import type {
  DiscoveryMeta,
  PopOpportunityAngle,
  PopOpportunityFields,
} from "../src/data/popDiscovery";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

interface YamiSignalsFile {
  asOf: string;
  sourceLabel: string;
  trendingIngredients: string[];
  categoryPulse: string[];
  lineAnchors: Record<string, string>;
}

interface TariffHintsFile {
  countryKeywords: { match: string; label: string }[];
}

function readJson<T>(name: string): T {
  const p = path.join(__dirname, "data", name);
  return JSON.parse(fs.readFileSync(p, "utf8")) as T;
}

let cachedYami: YamiSignalsFile | null = null;
let cachedFda: string[] | null = null;
let cachedTariff: TariffHintsFile | null = null;

export function loadYamiSignals(): YamiSignalsFile {
  if (!cachedYami) cachedYami = readJson<YamiSignalsFile>("yami-signals-public.json");
  return cachedYami;
}

function loadFdaUnapprovedIngredients(): string[] {
  if (!cachedFda) cachedFda = readJson<string[]>("pop-fda-unapproved-ingredients.json");
  return cachedFda;
}

function loadTariffHints(): TariffHintsFile {
  if (!cachedTariff) cachedTariff = readJson<TariffHintsFile>("pop-tariff-hints.json");
  return cachedTariff;
}

function inferPopCategory(title: string, feedCategory: string): string {
  const blob = `${title} ${feedCategory}`.toLowerCase();
  if (/toner|serum|cream|skincare|spf|lotion|shampoo|personal care/i.test(blob)) {
    return "Personal care";
  }
  if (/supplement|vitamin|collagen|probiotic|wellness|functional|adaptogen|ginseng extract/i.test(blob)) {
    return "Health & wellness";
  }
  if (/tea|matcha|oolong|chrysanthemum|brew|bag|leaf/i.test(blob)) {
    return "Teas";
  }
  if (/candy|chocolate|snack|cookie|wafer|jelly bean|confection/i.test(blob)) {
    return "Confections";
  }
  if (/noodle|rice|flour|vermicelli|pantry|dried|instant noodle|grain/i.test(blob)) {
    return "Dry goods";
  }
  return feedCategory || "Dry goods";
}

function estimateShelfLife(title: string, popCategory: string): { ok: boolean; why: string } {
  const t = title.toLowerCase();
  if (/fresh|refrigerat|frozen|perishable|short shelf|must refrigerate/i.test(t)) {
    return {
      ok: false,
      why: "Listing language suggests chilled/fresh — likely under 12 months; verify spec sheet.",
    };
  }
  if (popCategory === "Teas" || popCategory === "Dry goods" || popCategory === "Confections") {
    return {
      ok: true,
      why: "Ambient shelf-stable format typical for this PoP bucket — default ≥12 mo until COA confirms.",
    };
  }
  if (popCategory === "Personal care" || popCategory === "Health & wellness") {
    return {
      ok: true,
      why: "Typical CPG shelf for this aisle is ≥12 months — confirm on-pack date code.",
    };
  }
  return {
    ok: true,
    why: "No fresh/chilled cues in title; treat as shelf-stable pending supplier confirmation.",
  };
}

function scanFdaUnapproved(title: string, terms: string[]): { hit: boolean; rationale: string } {
  const low = title.toLowerCase();
  for (const kw of terms) {
    const k = kw.toLowerCase();
    if (low.includes(k)) {
      return {
        hit: true,
        rationale: `Not approved for this screen — title matches FDA-unapproved-ingredient term “${kw}”. Independent label review still required.`,
      };
    }
  }
  return {
    hit: false,
    rationale:
      "Approved — no terms from the curated unapproved-ingredient list appear in the title (title-only scan; confirm full ingredient deck and claims).",
  };
}

function scanTariff(
  title: string,
  hints: TariffHintsFile,
): { risk: boolean; label: string | null; rationale: string } {
  const low = title.toLowerCase();
  for (const row of hints.countryKeywords) {
    if (low.includes(row.match.toLowerCase())) {
      return {
        risk: true,
        label: row.label,
        rationale: `Origin or sourcing cue mentions ${row.label} — review current tariff / trade posture for this SKU.`,
      };
    }
  }
  return {
    risk: false,
    label: null,
    rationale: "No high-friction country keyword in title — still confirm COO with supplier.",
  };
}

function lineIdeas(
  title: string,
  yami: YamiSignalsFile,
  popCategory: string,
): string[] {
  const low = title.toLowerCase();
  const ideas: string[] = [];
  const ti = yami.trendingIngredients;

  const wantsGinger = ti.some((x) => x === "ginger") && /tea|beverage|drink|kombucha|latte/i.test(low);
  if (wantsGinger && /kombucha|adaptogen|probiotic|functional/i.test(low)) {
    ideas.push("Pilot kombucha–ginger RTD under PoP wellness set (tie-in to Yami ingredient pulse).");
  }
  if (ti.some((x) => x === "ginseng") && /adaptogen|energy|shot|stick|snack/i.test(low)) {
    ideas.push("Ginseng + adaptogen functional snack — leverage PoP ginseng equity with on-trend adaptogen story.");
  }
  if (/matcha|tea/i.test(low) && popCategory === "Teas") {
    ideas.push("Seasonal matcha–osmanthus blend extension for existing tea shelf.");
  }
  if (ideas.length === 0 && yami.trendingIngredients.length > 0) {
    const pick = yami.trendingIngredients.slice(0, 2).join(" + ");
    ideas.push(`Monitor ${pick} velocity — consider limited PoP bundle with ${popCategory.toLowerCase()} hero SKU.`);
  }
  return ideas.slice(0, 3);
}

function angles(
  p: EnrichedProductInput,
  ideas: string[],
): PopOpportunityAngle[] {
  const out = new Set<PopOpportunityAngle>();
  if (p.opportunityScore >= 48 || p.recommendation === "Import" || p.recommendation === "Watch") {
    out.add("distribute_existing");
  }
  if (ideas.length > 0 || /ginger|ginseng|kombucha|adaptogen/i.test(p.title)) {
    out.add("develop_pop_branded");
  }
  if (out.size === 0) out.add("distribute_existing");
  return [...out];
}

function compositeNote(p: EnrichedProductInput): string {
  const parts: string[] = [];
  parts.push(`Opportunity score ${p.opportunityScore} (${p.recommendation}).`);
  if (p.activeSources.length) {
    parts.push(`Signals: ${p.activeSources.join(", ")}.`);
  }
  parts.push("PoP filters below are heuristic — validate shelf life, label, and origin with the supplier.");
  return parts.join(" ");
}

function buyerSummary(
  p: EnrichedProductInput,
  fdaUnapprovedHit: boolean,
  shelfOk: boolean,
  tariffRisk: boolean,
  tariffWhy: string,
  angles: PopOpportunityAngle[],
): string {
  if (fdaUnapprovedHit) {
    return "Stop: title matches an FDA-unapproved-ingredient list term — resolve before sourcing.";
  }
  if (!shelfOk) {
    return "Defer: shelf-life profile may not meet PoP ≥12 mo rule unless reformulated or frozen line.";
  }
  if (tariffRisk) {
    return `Review: ${tariffWhy} Model margin with updated landed cost.`;
  }
  if (angles.includes("develop_pop_branded")) {
    return "Explore: strong narrative for PoP line extension — run a small market test alongside import of the hero SKU.";
  }
  return "Qualify: request spec sheet, COO, MOQ, and MAP; compare to adjacent PoP SKUs.";
}

export function buildPopFields(p: EnrichedProductInput): PopOpportunityFields {
  const yami = loadYamiSignals();
  const fdaTerms = loadFdaUnapprovedIngredients();
  const tariff = loadTariffHints();

  const popCategory = inferPopCategory(p.title, p.category);
  const shelf = estimateShelfLife(p.title, popCategory);
  const fdaScan = scanFdaUnapproved(p.title, fdaTerms);
  const tr = scanTariff(p.title, tariff);
  const ideas = lineIdeas(p.title, yami, popCategory);
  const opportunityAngles = angles(p, ideas);

  let country: string | null = tr.label;
  if (!country && /japan|korea|taiwan|vietnam|thailand/i.test(p.title)) {
    const m = p.title.match(/Japan|Korea|Taiwan|Vietnam|Thailand/i);
    country = m ? m[0] : null;
  }

  return {
    popCategory,
    shelfLifeExceeds12Months: shelf.ok,
    shelfLifeRationale: shelf.why,
    fdaUnapprovedIngredientHit: fdaScan.hit,
    fdaIngredientListStatus: fdaScan.hit ? "not_approved" : "approved",
    fdaRationale: fdaScan.rationale,
    tariffOrTradeRisk: tr.risk,
    tariffRationale: tr.rationale,
    countryOfOriginHint: country,
    opportunityAngles,
    lineExtensionIdeas: ideas,
    buyerActionSummary: buyerSummary(
      p,
      fdaScan.hit,
      shelf.ok,
      tr.risk,
      tr.rationale,
      opportunityAngles,
    ),
    compositeContext: compositeNote(p),
  };
}

export function attachPopLayer(products: EnrichedProductInput[]): EnrichedProduct[] {
  return products.map((p) => ({
    ...p,
    pop: buildPopFields(p),
  }));
}

export function getDiscoveryMeta(): DiscoveryMeta {
  const yami = loadYamiSignals();
  return {
    publicSources: [
      {
        id: "amazon",
        label: "Amazon US",
        detail: "Listings, BSR, reviews — Rainforest API or HTML scrape depending on FEED_MODE.",
      },
      {
        id: "yami",
        label: "Yami ingredient pulse",
        detail: yami.sourceLabel,
      },
    ],
    yamiSnapshot: {
      asOf: yami.asOf,
      sourceLabel: yami.sourceLabel,
      trendingIngredientsSample: yami.trendingIngredients.slice(0, 12),
    },
    scoringExplainer:
      "Signal strength comes from Amazon snapshot history: rank velocity, multi-day corroboration, review growth, and chart/search appearances.",
    filteringExplainer:
      "PoP gates: ≥12 mo shelf-life heuristic, title scan against a curated FDA-unapproved-ingredient word list (not a legal clearance), tariff/trade keyword flag.",
  };
}
