import "dotenv/config";
import cors from "cors";
import express from "express";
import "express-async-errors";
import { analyzeRetailSnippet } from "./gptAnalyze";
import { hasScrapeCredentials } from "./scraperClient";
import { defaults } from "./config";
import { resolveFeed } from "./resolveFeed";

export function createTrendScoutApp(): express.Application {
  const app = express();

  app.use(
    cors({
      origin(origin, cb) {
        if (!origin) {
          cb(null, true);
          return;
        }
        if (/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(origin)) {
          cb(null, true);
          return;
        }
        cb(null, false);
      },
    }),
  );
  app.use(express.json({ limit: "1mb" }));

  app.get("/api/health", (_req, res) => {
    res.json({ ok: true, service: "trendscout-api" });
  });

  app.get("/api/feed", async (_req, res) => {
    const mode = (process.env.FEED_MODE ?? "gpt").toLowerCase();
    if (mode === "gpt") {
      if (!process.env.OPENAI_API_KEY?.trim()) {
        res.status(503).json({
          error:
            "Set OPENAI_API_KEY in .env (https://platform.openai.com/api-keys). FEED_MODE=gpt uses OpenAI instead of scraping Amazon HTML.",
        });
        return;
      }
    } else if (mode === "rainforest") {
      if (!process.env.RAINFOREST_API_KEY?.trim()) {
        res.status(503).json({
          error:
            "Set RAINFOREST_API_KEY in .env (https://www.rainforestapi.com/). FEED_MODE=rainforest uses live Amazon search+product data with real listing images.",
        });
        return;
      }
    } else if (mode === "scraper" && !hasScrapeCredentials()) {
      res.status(503).json({
        error:
          "No scrape credentials: SCRAPER_API_KEY or Bright Data vars. Or FEED_MODE=gpt, FEED_MODE=rainforest (RAINFOREST_API_KEY), or FEED_MODE=snapshot.",
      });
      return;
    }
    const products = await resolveFeed();
    res.json({ products, shelfCategories: defaults.shelfCategories });
  });

  app.post("/api/analyze", async (req, res) => {
    if (!process.env.OPENAI_API_KEY?.trim()) {
      res.status(503).json({
        error: "OPENAI_API_KEY is not set — required for GPT analysis.",
      });
      return;
    }
    const text = typeof req.body?.text === "string" ? req.body.text : "";
    const context = typeof req.body?.context === "string" ? req.body.context : undefined;
    if (!text.trim()) {
      res.status(400).json({ error: "JSON body must include non-empty { \"text\": \"...\" }" });
      return;
    }
    const analysis = await analyzeRetailSnippet(text, context);
    res.json({ analysis });
  });

  app.use(
    (
      err: unknown,
      _req: express.Request,
      res: express.Response,
      _next: express.NextFunction,
    ) => {
      console.error("[TrendScout /api error]", err);
      if (res.headersSent) return;
      const message = err instanceof Error ? err.message : String(err);
      res.status(502).json({ error: message });
    },
  );

  return app;
}
