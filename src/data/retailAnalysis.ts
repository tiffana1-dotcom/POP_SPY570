/** Structured output from POST /api/analyze (GPT retail analyst). */

export type AnalysisVerdict = "Good Product" | "Risky Product" | "Weak Product";

export type SectionRating = "Strong" | "Moderate" | "Weak";

export interface AnalysisSection {
  /** Stable key for layout, e.g. demand */
  id: string;
  /** Display title, e.g. "Demand signal" */
  label: string;
  rating: SectionRating;
  /** Short paragraph for the card body */
  summary: string;
}

export interface RetailAnalysisResult {
  verdict: AnalysisVerdict;
  /** 0–100 overall fit for assortment / sourcing */
  score: number;
  /** One-line takeaway above the grid */
  headline: string;
  sections: AnalysisSection[];
}
