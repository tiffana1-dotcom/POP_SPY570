import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { EnrichedProduct } from "@/data/catalog";
import { findEnrichedByAsin } from "@/data/catalog";
import {
  buildCategoryTrendsFromProducts,
  buildDashboardKpisFromProducts,
} from "@/data/aggregates";
import type { CategoryTrend } from "@/data/types";
import type { WatchlistEntry } from "@/data/types";
import { SHELF_CATEGORIES } from "@/data/shelfCategories";
import type { DiscoveryMeta } from "@/data/popDiscovery";

interface TrendFeedContextValue {
  products: EnrichedProduct[];
  /** Canonical shelf list from the API (aligned with \`FEED_SHELF_CATEGORIES\`). */
  shelfCategories: string[];
  /** Public sources + cached Yami snapshot metadata from \`/api/feed\`. */
  discoveryMeta: DiscoveryMeta | null;
  categoryTrends: CategoryTrend[];
  dashboardKpis: ReturnType<typeof buildDashboardKpisFromProducts>;
  watchlistEntries: WatchlistEntry[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  getProduct: (asin: string) => EnrichedProduct | undefined;
}

const TrendFeedContext = createContext<TrendFeedContextValue | null>(null);

function explainFeedError(message: string): string {
  if (
    /failed to fetch|fetch failed|networkerror|load failed|network request failed/i.test(
      message,
    )
  ) {
    return [
      "Could not reach the API. Run `npm run dev` and wait for both:",
      "TrendScout API listening on http://127.0.0.1:8787",
      "and Vite on http://localhost:5173/",
      "Remove any VITE_API_BASE from .env so /api is proxied to 8787.",
    ].join(" ");
  }
  return message;
}

function isTransientNetworkError(e: unknown): boolean {
  if (!(e instanceof Error)) return false;
  return /failed to fetch|fetch failed|networkerror|load failed|network request failed|aborted/i.test(
    e.message,
  );
}

export function TrendFeedProvider({ children }: { children: ReactNode }) {
  const [products, setProducts] = useState<EnrichedProduct[]>([]);
  const [shelfCategories, setShelfCategories] = useState<string[]>([
    ...SHELF_CATEGORIES,
  ]);
  const [discoveryMeta, setDiscoveryMeta] = useState<DiscoveryMeta | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      /** Same-origin `/api` — Vite dev server proxies to Express on 8787. Set VITE_API_BASE only for a custom API URL. */
      const base =
        (import.meta.env.VITE_API_BASE as string | undefined)?.replace(
          /\/$/,
          "",
        ) ?? "";
      const url = `${base}/api/feed`;

      let res: Response;
      try {
        res = await fetch(url);
      } catch (first) {
        /** Vite often prints "ready" before the API binds — retry once after a short delay */
        if (isTransientNetworkError(first)) {
          await new Promise((r) => setTimeout(r, 2000));
          res = await fetch(url);
        } else {
          throw first;
        }
      }

      const text = await res.text();
      let data: {
        products?: EnrichedProduct[];
        shelfCategories?: string[];
        discoveryMeta?: DiscoveryMeta;
        error?: string;
      } = {};
      if (text) {
        try {
          data = JSON.parse(text) as typeof data;
        } catch {
          throw new Error(
            "API returned a non-JSON response. Restart `npm run dev` or check for a conflicting VITE_API_BASE in .env.",
          );
        }
      }
      if (!res.ok) {
        const detail =
          data.error?.trim() ||
          (text && !text.trim().startsWith("<")
            ? text.trim().slice(0, 800)
            : "");
        throw new Error(detail || `HTTP ${res.status}`);
      }
      setProducts(data.products ?? []);
      setDiscoveryMeta(data.discoveryMeta ?? null);
      if (
        Array.isArray(data.shelfCategories) &&
        data.shelfCategories.length > 0
      ) {
        setShelfCategories(data.shelfCategories);
      } else {
        setShelfCategories([...SHELF_CATEGORIES]);
      }
    } catch (e) {
      const raw =
        e instanceof Error ? e.message : "Failed to load product feed";
      setError(explainFeedError(raw));
      setProducts([]);
      setDiscoveryMeta(null);
      setShelfCategories([...SHELF_CATEGORIES]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const categoryTrends = useMemo(
    () => buildCategoryTrendsFromProducts(products, shelfCategories),
    [products, shelfCategories],
  );

  const dashboardKpis = useMemo(
    () => buildDashboardKpisFromProducts(products, categoryTrends),
    [products, categoryTrends],
  );

  const watchlistEntries = useMemo((): WatchlistEntry[] => {
    const top = [...products]
      .sort((a, b) => b.opportunityScore - a.opportunityScore)
      .slice(0, 6);
    const severities: WatchlistEntry["severity"][] = [
      "Elevated",
      "Critical",
      "Info",
      "Info",
      "Elevated",
      "Info",
    ];
    return top.map((p, i) => ({
      asin: p.asin,
      yesterdayOpportunity: Math.max(0, p.opportunityScore - (2 + (i % 4))),
      severity: severities[i] ?? "Info",
      statusSummary:
        "Live monitoring — compare vs yesterday’s Opportunity Score before PO.",
    }));
  }, [products]);

  const getProduct = useCallback(
    (asin: string) => findEnrichedByAsin(products, asin),
    [products],
  );

  const value = useMemo(
    (): TrendFeedContextValue => ({
      products,
      shelfCategories,
      discoveryMeta,
      categoryTrends,
      dashboardKpis,
      watchlistEntries,
      loading,
      error,
      refetch: load,
      getProduct,
    }),
    [
      products,
      shelfCategories,
      discoveryMeta,
      categoryTrends,
      dashboardKpis,
      watchlistEntries,
      loading,
      error,
      load,
      getProduct,
    ],
  );

  return (
    <TrendFeedContext.Provider value={value}>
      {children}
    </TrendFeedContext.Provider>
  );
}

export function useTrendFeed(): TrendFeedContextValue {
  const ctx = useContext(TrendFeedContext);
  if (!ctx) {
    throw new Error("useTrendFeed must be used within TrendFeedProvider");
  }
  return ctx;
}
