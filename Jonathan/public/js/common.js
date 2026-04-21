/* global fetch */

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function recClass(rec) {
  const r = String(rec || "").toLowerCase();
  if (r === "import") return "import";
  if (r === "avoid") return "avoid";
  return "watch";
}

function fmtMoney(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return "$" + Number(n).toFixed(2);
}

function fmtNum(n) {
  if (n === null || n === undefined) return "—";
  const x = Number(n);
  if (Number.isNaN(x)) return "—";
  return x.toLocaleString();
}

async function loadFeed() {
  const r = await fetch("/api/feed", { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error("Feed HTTP " + r.status);
  return await r.json();
}

async function postRefresh() {
  const r = await fetch("/api/refresh", { method: "POST", headers: { Accept: "application/json" } });
  const body = await r.json().catch(() => ({}));
  if (!r.ok || body.ok === false) {
    const msg = body && body.error ? String(body.error) : "Refresh failed";
    throw new Error(msg);
  }
  return body;
}

const WATCH_KEY = "beverageTrendScout_watchlist_v1";

function readWatchlist() {
  try {
    const raw = localStorage.getItem(WATCH_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr.map(String) : [];
  } catch {
    return [];
  }
}

function writeWatchlist(ids) {
  const uniq = [...new Set(ids.map(String))];
  localStorage.setItem(WATCH_KEY, JSON.stringify(uniq));
}

function toggleWatch(id) {
  const ids = readWatchlist();
  const s = String(id);
  const i = ids.indexOf(s);
  if (i >= 0) ids.splice(i, 1);
  else ids.push(s);
  writeWatchlist(ids);
  return ids.includes(s);
}

function isWatched(id) {
  return readWatchlist().includes(String(id));
}
