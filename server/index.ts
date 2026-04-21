import "dotenv/config";
import { createTrendScoutApp } from "./app";

const PORT = Number(process.env.PORT) || 8787;
const HOST = process.env.BIND_HOST ?? "127.0.0.1";

const app = createTrendScoutApp();
const server = app.listen(PORT, HOST, () => {
  console.log(`TrendScout API listening on http://${HOST}:${PORT}`);
});
server.on("error", (err: NodeJS.ErrnoException) => {
  if (err.code === "EADDRINUSE") {
    console.error(
      `[TrendScout] Port ${PORT} is already in use — another API process is running. Stop it or set PORT=8790. (macOS: lsof -i :${PORT})`,
    );
  } else {
    console.error("[TrendScout] Failed to start server:", err);
  }
  process.exit(1);
});
