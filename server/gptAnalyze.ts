import type {
  AnalysisVerdict,
  RetailAnalysisResult,
  SectionRating,
} from "../src/data/retailAnalysis";
import { openaiChatJson } from "./openaiClient";

const VERDICTS: AnalysisVerdict[] = ["Good Product", "Risky Product", "Weak Product"];
const RATINGS: SectionRating[] = ["Strong", "Moderate", "Weak"];

function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n));
}

function isVerdict(x: unknown): x is AnalysisVerdict {
  return typeof x === "string" && VERDICTS.includes(x as AnalysisVerdict);
}

function isRating(x: unknown): x is SectionRating {
  return typeof x === "string" && RATINGS.includes(x as SectionRating);
}

function normalizeResult(raw: unknown): RetailAnalysisResult {
  const o = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  let verdict: AnalysisVerdict = "Weak Product";
  if (isVerdict(o.verdict)) verdict = o.verdict;
  const rawScore = Number(o.score);
  const score = Number.isFinite(rawScore)
    ? clamp(Math.round(rawScore), 0, 100)
    : 50;
  const headline =
    typeof o.headline === "string" && o.headline.trim()
      ? o.headline.trim()
      : "Review the section cards below for sourcing implications.";

  const sectionsIn = Array.isArray(o.sections) ? o.sections : [];
  const sections: RetailAnalysisResult["sections"] = [];
  for (const row of sectionsIn) {
    if (!row || typeof row !== "object") continue;
    const r = row as Record<string, unknown>;
    const id = typeof r.id === "string" && r.id.trim() ? r.id.trim() : `sec-${sections.length}`;
    const label =
      typeof r.label === "string" && r.label.trim() ? r.label.trim() : "Insight";
    const rating: SectionRating = isRating(r.rating) ? r.rating : "Moderate";
    const summary =
      typeof r.summary === "string" && r.summary.trim()
        ? r.summary.trim()
        : "No detail provided.";
    sections.push({ id, label, rating, summary });
  }

  if (sections.length === 0) {
    sections.push({
      id: "overview",
      label: "Overview",
      rating: "Moderate",
      summary: "The model returned no structured sections; try again with more listing detail.",
    });
  }

  const scoreOut = Number.isFinite(score) ? score : 50;

  return {
    verdict,
    score: scoreOut,
    headline,
    sections,
  };
}

/**
 * Buyer-facing structured analysis of pasted text (listing copy, reviews, competitor notes).
 */
export async function analyzeRetailSnippet(
  text: string,
  context?: string,
): Promise<RetailAnalysisResult> {
  const trimmed = text.trim();
  if (!trimmed) throw new Error("text is empty");

  const raw = await openaiChatJson<unknown>({
    system: `You are an experienced CPG buyer and retail analyst. Output valid JSON only (no markdown).
Be honest about uncertainty. Each section rating must reflect evidence in the pasted text.

JSON schema:
{
  "verdict": "Good Product" | "Risky Product" | "Weak Product",
  "score": <integer 0-100, overall assortment fit / conviction>,
  "headline": "<one sentence takeaway>",
  "sections": [
    {
      "id": "demand",
      "label": "Demand signal",
      "rating": "Strong" | "Moderate" | "Weak",
      "summary": "<2-4 sentences, plain text>"
    },
    ... exactly 6 objects with these ids in order:
    "demand", "differentiation", "pricing", "seasonality", "channel", "next_step"
  ]
}

Rules:
- verdict must align with score (Good ≈ 72+, Risky ≈ 42–71, Weak ≈ 0–41) unless text clearly contradicts.
- "next_step" label should be "Suggested next step" with a concrete action.`,
    user: `Analyze for US market, omnichannel assortment / sourcing.

${context ? `User context: ${context}\n\n` : ""}---\n${trimmed}\n---`,
  });

  return normalizeResult(raw);
}
