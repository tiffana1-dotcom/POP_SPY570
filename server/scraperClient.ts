/**
 * HTML fetch for Amazon pages via either:
 * - ScraperAPI — `?api_key=&url=` (https://www.scraperapi.com)
 * - Bright Data — HTTP(S) proxy `user:pass@host:port` (https://brightdata.com)
 *
 * If you see ScraperAPI 401, you may be using Bright Data credentials in SCRAPER_API_KEY.
 * Set BRIGHTDATA_USERNAME / BRIGHTDATA_PASSWORD (Bright Data is used automatically when both are set).
 */

import { fetch, ProxyAgent } from "undici";

const SCRAPER_BASE = "https://api.scraperapi.com";

const DEFAULT_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36";

export type ScrapeProviderName = "scraperapi" | "brightdata";

function hasBrightDataCreds(): boolean {
  return !!(process.env.BRIGHTDATA_USERNAME?.trim() && process.env.BRIGHTDATA_PASSWORD?.trim());
}

/**
 * Routing: explicit `SCRAPER_PROVIDER` wins; otherwise if Bright Data user+pass are set, use Bright Data
 * (so a stale `SCRAPER_API_KEY` does not keep causing 401). Default is ScraperAPI only when no Bright Data creds.
 */
export function getScrapeProvider(): ScrapeProviderName {
  const explicit = process.env.SCRAPER_PROVIDER?.trim();
  if (explicit) {
    const p = explicit.toLowerCase();
    if (p === "brightdata" || p === "bright" || p === "brd") return "brightdata";
    if (p === "scraperapi") return "scraperapi";
  }
  if (hasBrightDataCreds()) return "brightdata";
  return "scraperapi";
}

export function hasScrapeCredentials(): boolean {
  if (getScrapeProvider() === "brightdata") {
    return hasBrightDataCreds();
  }
  return !!process.env.SCRAPER_API_KEY?.trim();
}

async function fetchViaBrightDataProxy(targetUrl: string): Promise<string> {
  const username = process.env.BRIGHTDATA_USERNAME?.trim();
  const password = process.env.BRIGHTDATA_PASSWORD?.trim();
  if (!username || !password) {
    throw new Error(
      "BRIGHTDATA_USERNAME and BRIGHTDATA_PASSWORD are required for Bright Data (set both in .env).",
    );
  }

  const host = process.env.BRIGHTDATA_HOST?.trim() ?? "brd.superproxy.io";
  const port = process.env.BRIGHTDATA_PORT?.trim() ?? "33335";

  /**
   * Scraping Browser zones (dashboard ports 9222 WebSocket / 9515 Selenium) are NOT HTTP CONNECT proxies.
   * This app uses undici + HTTP proxy. You need a Residential, ISP, or Datacenter *proxy* zone — same host
   * `brd.superproxy.io` but port from that zone’s doc (often 33335 or 22225). Username looks like
   * `brd-customer-…-zone-<zone_name>` for any zone; each zone type has its own port.
   */
  if (port === "9222" || port === "9515") {
    throw new Error(
      `BRIGHTDATA_PORT=${port} is for Scraping Browser (Playwright/Selenium WebSocket), not HTTP proxy. ` +
        `Create a Residential / ISP / Datacenter proxy zone in Bright Data, copy its port (often 33335 or 22225), ` +
        `set BRIGHTDATA_PORT to that value, and use that zone’s username/password in .env.`,
    );
  }

  const proxyUrl = `http://${encodeURIComponent(username)}:${encodeURIComponent(password)}@${host}:${port}`;
  const dispatcher = new ProxyAgent(proxyUrl);

  const res = await fetch(targetUrl, {
    dispatcher,
    method: "GET",
    redirect: "follow",
    headers: {
      Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9",
      "User-Agent": DEFAULT_UA,
    },
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(
      `Bright Data proxy HTTP ${res.status}: ${text.slice(0, 450)}. Try BRIGHTDATA_PORT=22225 (residential) or 33335 (datacenter), or create a Residential/ISP proxy zone if your zone is WebSocket-only.`,
    );
  }
  return text;
}

async function fetchViaScraperApi(targetUrl: string): Promise<string> {
  const apiKey = process.env.SCRAPER_API_KEY?.trim();
  if (!apiKey) {
    throw new Error("SCRAPER_API_KEY is not set (required when SCRAPER_PROVIDER=scraperapi)");
  }

  const u = new URL(SCRAPER_BASE);
  u.searchParams.set("api_key", apiKey);
  u.searchParams.set("url", targetUrl);

  if (process.env.SCRAPER_RENDER === "true") {
    u.searchParams.set("render", "true");
  }
  const cc = process.env.SCRAPER_COUNTRY?.trim();
  if (cc) {
    u.searchParams.set("country_code", cc);
  }

  const res = await fetch(u.toString(), {
    method: "GET",
    headers: { Accept: "text/html,application/json;q=0.9,*/*;q=0.8" },
  });

  const text = await res.text();

  if (!res.ok) {
    const hint401 =
      res.status === 401
        ? " Get a valid key at https://www.scraperapi.com/ or leave SCRAPER_API_KEY empty and set BRIGHTDATA_USERNAME + BRIGHTDATA_PASSWORD for Bright Data (brd.superproxy.io)."
        : "";
    throw new Error(`ScraperAPI HTTP ${res.status}: ${text.slice(0, 500)}${hint401}`);
  }

  const trimmed = text.trim();
  if (trimmed.startsWith("{") && trimmed.includes('"error"')) {
    try {
      const j = JSON.parse(trimmed) as { error?: string; message?: string };
      const msg = j.error ?? j.message;
      if (msg) throw new Error(`ScraperAPI: ${msg}`);
    } catch (e) {
      if (e instanceof Error && e.message.startsWith("ScraperAPI:")) throw e;
    }
  }

  return text;
}

/** Fetches raw HTML for a public Amazon URL (through configured provider). */
export async function fetchAmazonPageHtml(targetUrl: string): Promise<string> {
  if (getScrapeProvider() === "brightdata") {
    return fetchViaBrightDataProxy(targetUrl);
  }
  return fetchViaScraperApi(targetUrl);
}
