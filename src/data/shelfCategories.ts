/** Canonical shelf categories for filters and feed labeling. */
export const SHELF_CATEGORIES = [
  "Snacks",
  "Grocery",
  "Beverage",
  "Beauty",
] as const;

export type ShelfCategory = (typeof SHELF_CATEGORIES)[number];

export function isShelfCategory(s: string): s is ShelfCategory {
  return (SHELF_CATEGORIES as readonly string[]).includes(s);
}

/** Coerce free text or API output to a configured shelf label. */
export function matchShelfCategory(
  raw: string,
  allowed: readonly string[],
  fallback: string,
): string {
  if (allowed.length === 0) return fallback;
  const t = raw.trim();
  if (!t) return fallback;
  const lower = t.toLowerCase();
  const exact = allowed.find((a) => a.toLowerCase() === lower);
  if (exact) return exact;
  for (const a of allowed) {
    const al = a.toLowerCase();
    if (lower.includes(al) || al.includes(lower)) return a;
  }
  return fallback;
}

/**
 * Dropdown / trend order: preferred shelf list first (from API or default), then any extra feed labels (sorted).
 */
export function mergeCategoryOptions(
  productCategories: string[],
  preferredOrder: readonly string[] = SHELF_CATEGORIES,
): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const c of preferredOrder) {
    if (c && !seen.has(c)) {
      seen.add(c);
      out.push(c);
    }
  }
  for (const p of [...new Set(productCategories)].sort((a, b) => a.localeCompare(b))) {
    if (p && !seen.has(p)) {
      seen.add(p);
      out.push(p);
    }
  }
  return out;
}
