/* global document, loadFeed, esc, recClass, fmtMoney, fmtNum, toggleWatch, isWatched */

function qs(name) {
  const u = new URL(window.location.href);
  return u.searchParams.get(name);
}

function riskClass(level) {
  const l = String(level || "").toLowerCase();
  if (l === "high") return "high";
  if (l === "low") return "low";
  return "medium";
}

async function boot() {
  const id = qs("id");
  const root = document.getElementById("root");
  if (!id) {
    root.innerHTML = '<div class="panel pad"><p class="page-sub">Missing product id.</p></div>';
    return;
  }

  let feed;
  try {
    feed = await loadFeed();
  } catch (e) {
    root.innerHTML = `<div class="banner">${esc(e && e.message ? e.message : String(e))}</div>`;
    return;
  }

  const p = (feed.opportunities || []).find((x) => String(x.id) === String(id));
  if (!p) {
    root.innerHTML = `<div class="panel pad">
      <p>Product not found in cache.</p>
      <p style="margin-top:0.75rem"><a href="index.html">Back to radar</a></p>
    </div>`;
    return;
  }

  const amz = p.amazon || {};
  const gt = p.google_trends || {};
  const rd = p.reddit || {};
  const risk = p.risk || {};
  const buyer = p.buyer || {};

  const img = p.image
    ? `<img src="${esc(p.image)}" alt="" style="width:100%;height:100%;object-fit:cover" />`
    : "";

  const watched = isWatched(p.id);

  root.innerHTML = `
    <div class="crumb">
      <a href="index.html">Live radar</a>
      <span style="color:#cbd5e1">/</span>
      <span style="color:#0f172a;font-weight:600;max-width:52rem" class="line-clamp">${esc(p.title)}</span>
    </div>

    <div class="alert"><span style="font-weight:700">Buyer alert: </span>${esc(p.headline_reason || "")}</div>

    <div class="layout-2">
      <div class="space" style="display:flex;flex-direction:column;gap:1rem">
        <div class="panel" style="overflow:hidden">
          <div class="aspect-square" style="aspect-ratio:1/1;background:#f8fafc">${img}</div>
          <div class="panel pad">
            <h1>${esc(p.title)}</h1>
            <div class="mono">ASIN · ${esc(p.asin || p.id)}</div>
            <div style="margin-top:0.35rem;font-size:0.875rem;color:#64748b">${esc(p.beverage_type || "")}</div>
            <dl class="dl">
              <div>
                <dt>Amazon price</dt>
                <dd>${esc(fmtMoney(amz.price))}</dd>
              </div>
              <div>
                <dt>Rating</dt>
                <dd>${amz.rating != null ? esc(String(Number(amz.rating).toFixed(1))) + " ★" : esc("—")}</dd>
              </div>
              <div>
                <dt>Reviews</dt>
                <dd>${esc(fmtNum(amz.reviews))}</dd>
              </div>
              <div>
                <dt>Best BSR</dt>
                <dd>${amz.bsr ? esc("#" + fmtNum(amz.bsr)) : esc("—")}</dd>
              </div>
              <div style="grid-column:1/-1">
                <dt>Opportunity score</dt>
                <dd style="display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;margin-top:0.35rem">
                  <span style="font-size:1.75rem;font-weight:800;font-variant-numeric:tabular-nums">${esc(
                    String(p.opportunity_score ?? ""),
                  )}</span>
                  <span class="rec ${recClass(p.recommendation)}">${esc(p.recommendation || "")}</span>
                </dd>
              </div>
            </dl>
            <div style="margin-top:1rem;display:flex;gap:0.5rem;flex-wrap:wrap">
              <button type="button" class="btn btn-ghost" id="watchToggle">${watched ? "Remove from watchlist" : "Add to watchlist"}</button>
              <a class="btn btn-primary" style="display:inline-flex;align-items:center;justify-content:center;text-decoration:none" href="${esc(
                amz.url || "#",
              )}" target="_blank" rel="noreferrer">Open Amazon</a>
            </div>
          </div>
        </div>
      </div>

      <div style="display:flex;flex-direction:column;gap:1rem">
        <section class="panel pad">
          <h2 class="section-title" style="margin:0">Full description</h2>
          <p style="margin:0.75rem 0 0;font-size:0.9375rem;color:#334155;line-height:1.6">${esc(
            p.description || "",
          )}</p>
        </section>

        <section class="panel pad">
          <h2 class="section-title" style="margin:0">Trend outlook</h2>
          <p style="margin:0.75rem 0 0;font-size:0.9375rem;color:#334155;line-height:1.6">${esc(
            p.trend_outlook || "",
          )}</p>
        </section>

        <section class="panel pad">
          <h2 class="section-title" style="margin:0">Forward risk</h2>
          <p style="margin:0.75rem 0 0;font-size:0.875rem;color:#64748b">
            Risk summarizes how aggressive we’d be stocking or listing this SKU given Amazon competitiveness and signal quality.
          </p>
          <div style="margin-top:0.75rem;display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap">
            <span class="risk ${riskClass(risk.level)}">${esc(risk.level || "Unknown")}</span>
            <span style="font-size:0.8125rem;color:#64748b">Buyer view: <strong>${esc(
              buyer.risk_level || risk.level || "",
            )}</strong></span>
          </div>
          <ul class="bullets">
            ${(risk.factors || [])
              .map((f) => `<li>${esc(f)}</li>`)
              .join("")}
          </ul>
        </section>

        <section class="panel pad">
          <h2 class="section-title" style="margin:0">Google Trends (US beverage keyword)</h2>
          <div class="table-wrap">
            <table class="simple">
              <thead><tr><th>Keyword</th><th>Interest index</th><th>Note</th></tr></thead>
              <tbody>
                <tr>
                  <td>${esc(gt.keyword || "")}</td>
                  <td>${esc(String(gt.interest_index ?? ""))}</td>
                  <td>${esc(gt.change_note || "")}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="panel pad">
          <h2 class="section-title" style="margin:0">Reddit signals (target subreddits)</h2>
          <p style="margin:0.5rem 0 0;font-size:0.875rem;color:#334155">
            Post hits (sum of r/sub search results): <strong>${esc(String(rd.mentions ?? ""))}</strong>
            · Signal: <strong>${esc(rd.signal || "")}</strong>
            · ${esc(rd.velocity_label || "")}
          </p>
          <p style="margin:0.35rem 0 0;font-size:0.8125rem;color:#64748b">
            Subs checked: ${esc((rd.subreddits_checked || []).join(", ") || "configure REDDIT_SUBREDDITS")}
          </p>
          <ul class="bullets">
            ${(rd.sample_titles || []).map((t) => `<li>${esc(t)}</li>`).join("")}
          </ul>
        </section>

        <section class="panel pad">
          <h2 class="section-title" style="margin:0">Why it scores this way</h2>
          <ul class="bullets">
            ${(p.explanation_bullets || []).map((b) => `<li>${esc(b)}</li>`).join("")}
          </ul>
        </section>

        <section class="panel pad">
          <h2 class="section-title" style="margin:0">Buyer action</h2>
          <dl class="dl" style="grid-template-columns:1fr">
            <div>
              <dt>Suggested sourcing strategy</dt>
              <dd style="font-weight:500;color:#334155">${esc(buyer.sourcing_strategy || "")}</dd>
            </div>
            <div>
              <dt>Suggested price range</dt>
              <dd>${esc(buyer.suggested_price_range || "")}</dd>
            </div>
            <div>
              <dt>Target channels</dt>
              <dd style="font-weight:500;color:#334155">${esc((buyer.target_channels || []).join(" · "))}</dd>
            </div>
          </dl>
        </section>
      </div>
    </div>
  `;

  document.getElementById("watchToggle").addEventListener("click", () => {
    const on = toggleWatch(p.id);
    document.getElementById("watchToggle").textContent = on ? "Remove from watchlist" : "Add to watchlist";
  });
}

document.addEventListener("DOMContentLoaded", boot);
