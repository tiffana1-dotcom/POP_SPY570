/* global document, loadFeed, postRefresh, esc, recClass, fmtMoney, fmtNum, toggleWatch, isWatched */

let state = {
  feed: null,
  query: "",
  beverageType: "All types",
  loading: true,
  error: "",
};

function byScoreDesc(list) {
  return [...list].sort((a, b) => (b.opportunity_score || 0) - (a.opportunity_score || 0));
}

function filteredOpps() {
  const all = (state.feed && state.feed.opportunities) || [];
  const q = state.query.trim().toLowerCase();
  return all.filter((p) => {
    const typeOk =
      state.beverageType === "All types" ? true : p.beverage_type === state.beverageType;
    const text = `${p.title || ""} ${p.beverage_type || ""}`.toLowerCase();
    const qOk = !q || text.includes(q);
    return typeOk && qOk;
  });
}

function renderKpis(pool) {
  const rising = pool.filter((p) => (p.amazon && p.amazon.bsr && p.amazon.bsr < 200) || false).length;
  const avg =
    pool.length === 0
      ? 0
      : Math.round(pool.reduce((s, p) => s + (Number(p.opportunity_score) || 0), 0) / pool.length);
  const importish = pool.filter((p) => String(p.recommendation).toLowerCase() === "import").length;
  const cats = new Set(pool.map((p) => p.beverage_type).filter(Boolean)).size;

  document.getElementById("kpiRising").textContent = String(rising);
  document.getElementById("kpiAvg").textContent = String(avg);
  document.getElementById("kpiImport").textContent = String(importish);
  document.getElementById("kpiCats").textContent = String(cats);
}

function renderTop(pool) {
  const el = document.getElementById("shortlist");
  const top = byScoreDesc(pool).slice(0, 5);
  if (!top.length) {
    el.innerHTML =
      '<p class="empty" style="margin:1.75rem 1rem">No beverage opportunities match filters yet.</p>';
    return;
  }
  el.innerHTML =
    "<ol>" +
    top
      .map((p, i) => {
        const img = p.image
          ? `<img class="thumb" src="${esc(p.image)}" alt="" loading="lazy" />`
          : `<div class="thumb" aria-hidden="true"></div>`;
        return `
        <li>
          <a class="row" href="detail.html?id=${encodeURIComponent(p.id)}">
            <div style="display:flex;align-items:flex-start;gap:0.9rem;min-width:0;flex:1">
              <span class="rank-pill">#${i + 1}</span>
              ${img}
              <div style="min-width:0">
                <h3>${esc(p.title)}</h3>
                <p>${esc(p.headline_reason || "")}</p>
              </div>
            </div>
            <div class="score-block" style="min-width:9rem">
              <div class="score-label">Opportunity</div>
              <div class="score-val">${esc(String(p.opportunity_score ?? ""))}</div>
              <div style="margin-top:0.35rem"><span class="rec ${recClass(p.recommendation)}">${esc(
                p.recommendation || "",
              )}</span></div>
            </div>
          </a>
        </li>`;
      })
      .join("") +
    "</ol>";
}

function renderGrid(pool) {
  const el = document.getElementById("grid");
  const sorted = byScoreDesc(pool);
  if (!sorted.length) {
    el.innerHTML = '<div class="empty">No matches — try another beverage type or clear search.</div>';
    return;
  }
  el.innerHTML = sorted
    .map((p) => {
      const watched = isWatched(p.id);
      const img = p.image
        ? `<img src="${esc(p.image)}" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover" />`
        : "";
      return `
      <article class="card">
        <div class="media">${img}</div>
        <div class="body">
          <div class="meta-row">
            <span class="tag">${esc(p.beverage_type || "Beverage")}</span>
            <span class="rec ${recClass(p.recommendation)}">${esc(p.recommendation || "")}</span>
          </div>
          <h3>${esc(p.title)}</h3>
          <p style="margin:0;font-size:0.8125rem;color:#64748b;line-height:1.45">${esc(
            p.card_explanation || (p.explanation_bullets && p.explanation_bullets[0]) || "",
          )}</p>
          <div style="display:flex;justify-content:space-between;gap:0.75rem;font-size:0.8125rem;color:#334155;margin-top:0.25rem">
            <div>BSR <strong>${
              p.amazon && p.amazon.bsr ? "#" + esc(fmtNum(p.amazon.bsr)) : esc("—")
            }</strong></div>
            <div>Score <strong>${esc(String(p.opportunity_score ?? ""))}</strong></div>
          </div>
          <div class="card-actions">
            <button type="button" class="watch-btn" data-id="${esc(p.id)}">${watched ? "Unwatch" : "Watch"}</button>
            <a class="primary" href="detail.html?id=${encodeURIComponent(p.id)}">Details</a>
          </div>
        </div>
      </article>`;
    })
    .join("");

  el.querySelectorAll(".watch-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-id");
      const on = toggleWatch(id);
      btn.textContent = on ? "Unwatch" : "Watch";
    });
  });
}

function renderMeta() {
  const banner = document.getElementById("banner");
  const status = document.getElementById("statusPill");
  if (!state.feed) return;
  const st = state.feed.source_status || {};
  const parts = [
    `Rainforest: ${st.rainforest || "?"}`,
    `Trends: ${st.google_trends || "?"}`,
    `Reddit: ${st.reddit || "?"}`,
  ];
  status.textContent = state.feed.cache_stale ? "Cache (stale)" : "Cache (fresh)";
  if (state.error) {
    banner.className = "banner";
    banner.style.display = "block";
    banner.textContent = state.error;
  } else if (state.feed.cache_stale) {
    banner.className = "banner info";
    banner.style.display = "block";
    banner.textContent =
      "Cache is older than TTL — data is still shown for speed. Use Refresh data to pull the latest cross-source snapshot.";
  } else {
    banner.style.display = "none";
  }
  document.getElementById("sourceLine").textContent =
    `Generated ${state.feed.generated_at || "unknown"} · ` + parts.join(" · ");
}

function wire() {
  document.getElementById("search").addEventListener("input", (e) => {
    state.query = e.target.value;
    const pool = filteredOpps();
    renderKpis(pool);
    renderTop(pool);
    renderGrid(pool);
  });
  document.getElementById("type").addEventListener("change", (e) => {
    state.beverageType = e.target.value;
    const pool = filteredOpps();
    renderKpis(pool);
    renderTop(pool);
    renderGrid(pool);
  });
  const refreshBtn = document.getElementById("refresh");
  refreshBtn.addEventListener("click", async () => {
    refreshBtn.disabled = true;
    try {
      await postRefresh();
      state.feed = await loadFeed();
      state.error = "";
      const pool = filteredOpps();
      renderMeta();
      renderKpis(pool);
      renderTop(pool);
      renderGrid(pool);
    } catch (e) {
      state.error = e && e.message ? e.message : String(e);
      renderMeta();
    } finally {
      refreshBtn.disabled = false;
    }
  });
}

async function boot() {
  wire();
  try {
    state.feed = await loadFeed();
    state.error = "";
  } catch (e) {
    state.error =
      (e && e.message ? e.message : String(e)) +
      " — start the Python server from BeverageTrendScout/python (python server.py).";
    state.feed = { opportunities: [], beverage_types: ["All types"] };
  } finally {
    state.loading = false;
    document.getElementById("loadingBlock").style.display = "none";
    document.getElementById("mainBlock").style.display = "block";
  }

  const types = (state.feed && state.feed.beverage_types) || ["All types"];
  const sel = document.getElementById("type");
  sel.innerHTML = types.map((t) => `<option value="${esc(t)}">${esc(t)}</option>`).join("");
  sel.value = state.beverageType;

  const pool = filteredOpps();
  renderMeta();
  renderKpis(pool);
  renderTop(pool);
  renderGrid(pool);
}

document.addEventListener("DOMContentLoaded", boot);
