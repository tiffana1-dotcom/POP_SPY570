/**
 * Yami.com homepage / PLP text mining for POP-relevant trend candidates.
 * Mirrors logic from `scripts/yami_trends.py` (Playwright + BeautifulSoup).
 */

export const YAMI_RELEVANT_KEYWORDS = [
  "tea",
  "matcha",
  "ginger",
  "herbal",
  "ginseng",
  "drink",
  "beverage",
  "jelly",
  "collagen",
  "mushroom",
  "wolfberry",
  "chrysanthemum",
  "jujube",
  "brown sugar",
  "granule",
  "powder",
  "instant",
  "supplement",
  "tonic",
  "kombucha",
  "gut health",
  "adaptogen",
  "probiotic",
  "oolong",
  "konjac",
  "goji",
  "longan",
  "latte",
  "fruit tea",
  "milk tea",
  "white fungus",
  "snow fungus",
  "bird's nest",
  "osmanthus",
  "throat candy",
] as const;

export const YAMI_STOPWORDS = new Set([
  "the",
  "and",
  "for",
  "with",
  "from",
  "new",
  "sale",
  "shop",
  "home",
  "sign",
  "login",
  "sign up",
  "cart",
  "categories",
  "show",
  "only",
  "best",
  "sellers",
  "arrivals",
  "brands",
  "subscribe",
  "services",
  "fulfilled",
  "skip",
  "main",
  "content",
  "search",
  "filter",
  "keyboard",
  "shortcuts",
  "use",
  "keys",
  "navigate",
  "privacy",
  "cookie",
  "cookies",
  "consent",
  "reject",
  "accept",
  "customise",
  "powered",
  "necessary",
  "active",
  "description",
  "available",
  "view",
  "more",
  "all",
  "rating",
  "stars",
  "sold",
  "options",
]);

const JUNK_LINE_SUBSTRINGS = [
  "we value your privacy",
  "cookie",
  "consent",
  "accept all",
  "reject all",
  "sign in / sign up",
  "download the yami app",
  "feedback",
  "chat with us",
  "app store",
  "google play",
  "live chat",
  "shop on the go",
  "sale price alerts",
  "exclusive discounts",
  "faster & more secure checkout",
  "easy order tracking",
  "main content",
  "skip banner",
  "keyboard shortcuts",
  "show/hide shortcuts",
];

export function looksYamiRelevant(text: string): boolean {
  const low = text.toLowerCase();
  return YAMI_RELEVANT_KEYWORDS.some((k) => low.includes(k.toLowerCase()));
}

export function cleanVisibleText(text: string): string {
  let t = text.replace(/\xa0/g, " ");
  t = t.replace(/[ \t]+/g, " ");
  t = t.replace(/\n+/g, "\n");
  return t.trim();
}

export interface YamiTrendTerm {
  term: string;
  count: number;
}

export interface YamiTrendCandidates {
  seedUrl: string;
  topWords: YamiTrendTerm[];
  topPhrases: YamiTrendTerm[];
  relevantLines: string[];
  extractedTextLength: number;
  fetchedAt: string;
}

export function extractRelevantLines(fullText: string): string[] {
  const rawLines = fullText
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length >= 4);

  const filtered: string[] = [];
  const seen = new Set<string>();

  for (const line of rawLines) {
    const low = line.toLowerCase();
    if (JUNK_LINE_SUBSTRINGS.some((j) => low.includes(j))) continue;
    if (!looksYamiRelevant(low)) continue;
    if (seen.has(low)) continue;
    seen.add(low);
    filtered.push(line);
  }

  return filtered;
}

export function extractKeywordsAndPhrases(lines: string[]): {
  topWords: YamiTrendTerm[];
  topPhrases: YamiTrendTerm[];
} {
  const words: string[] = [];
  const phrases: string[] = [];

  for (const line of lines) {
    const cleaned = line
      .toLowerCase()
      .replace(/[^a-z0-9\s\-+]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    const tokens = cleaned.split(/\s+/).filter(Boolean);

    for (const token of tokens) {
      if (token.length < 4) continue;
      if (YAMI_STOPWORDS.has(token)) continue;
      words.push(token);
    }

    for (let i = 0; i < tokens.length - 1; i++) {
      const phrase = `${tokens[i]} ${tokens[i + 1]}`;
      const parts = phrase.split(" ");
      if (parts.some((p) => YAMI_STOPWORDS.has(p))) continue;
      phrases.push(phrase);
    }
  }

  const wordCounts = countMap(words);
  const phraseCounts = countMap(phrases);

  const topWords: YamiTrendTerm[] = [...wordCounts.entries()]
    .filter(([term]) => looksYamiRelevant(term))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 100)
    .map(([term, count]) => ({ term, count }));

  const topPhrases: YamiTrendTerm[] = [...phraseCounts.entries()]
    .filter(([term]) => looksYamiRelevant(term))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 100)
    .map(([term, count]) => ({ term, count }));

  return { topWords, topPhrases };
}

function countMap(items: string[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const x of items) {
    m.set(x, (m.get(x) ?? 0) + 1);
  }
  return m;
}
