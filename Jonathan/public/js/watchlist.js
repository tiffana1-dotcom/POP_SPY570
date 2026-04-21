/* global document, loadFeed, esc, recClass, fmtMoney, fmtNum, readWatchlist */

async function boot() {
  const body = document.getElementById("wlBody");
  let feed;
  try {
    feed = await loadFeed();
  } catch (e) {
    body.innerHTML = `<tr><td colspan="5">${esc(e && e.message ? e.message : String(e))}</td></tr>`;
    return;
  }

  const byId = new Map((feed.opportunities || []).map((p) => [String(p.id), p]));
  const ids = readWatchlist();
  const rows = ids.map((id) => byId.get(String(id))).filter(Boolean);

  document.getElementById("wlMeta").textContent =
    `Tracking ${(feed.opportunities || []).length} cached SKUs · ${ids.length} watchlist slots`;

  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="5" style="padding:2rem;text-align:center;color:#64748b">
      No watchlist rows yet. Add products from the radar cards or detail page.
    </td></tr>`;
    return;
  }

  body.innerHTML = rows
    .map((p) => {
      const amz = p.amazon || {};
      return `<tr>
        <td style="padding:0.75rem 1rem">
          <div style="font-weight:600"><a href="detail.html?id=${encodeURIComponent(p.id)}">${esc(
            p.title || "",
          )}</a></div>
          <div style="font-size:0.75rem;color:#64748b;margin-top:0.25rem">${esc(p.beverage_type || "")}</div>
        </td>
        <td style="padding:0.75rem 1rem;font-variant-numeric:tabular-nums;font-weight:700">${esc(
          String(p.opportunity_score ?? ""),
        )}</td>
        <td style="padding:0.75rem 1rem;font-size:0.8125rem;color:#334155">${esc(
          amz.bsr ? "#" + fmtNum(amz.bsr) : "—",
        )}</td>
        <td style="padding:0.75rem 1rem"><span class="rec ${recClass(p.recommendation)}">${esc(
          p.recommendation || "",
        )}</span></td>
        <td style="padding:0.75rem 1rem;font-size:0.8125rem;color:#334155">${esc(
          (p.risk && p.risk.level) || "",
        )}</td>
      </tr>`;
    })
    .join("");
}

document.addEventListener("DOMContentLoaded", boot);
