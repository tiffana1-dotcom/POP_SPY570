from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import sync_playwright

# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

HEADLESS = True
AMAZON_DOMAIN = "https://www.amazon.com"

INPUT_TERMS_FILE = BASE_DIR / "terms_list.json"
OUTPUT_FILE = BASE_DIR / "amazon_products.json"
ERROR_FILE = BASE_DIR / "amazon_errors.json"
DEBUG_FILE = BASE_DIR / "amazon_debug.json"
DEBUG_DUMPS_DIR = BASE_DIR / "amazon_debug_dumps"

MAX_TERMS = 150
MAX_PRODUCTS_PER_QUERY = 10

SEARCH_TIMEOUT_MS = 18000
PRODUCT_TIMEOUT_MS = 22000
SEARCH_WAIT_MS = 700
PRODUCT_WAIT_MS = 1200

SLEEP_BETWEEN_QUERIES = 0.15
SLEEP_BETWEEN_PRODUCTS = 0.05

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

ITEM_DETAIL_KEYS = [
    "Brand Name",
    "Primary Supplement Type",
    "Item Form",
    "Flavor",
    "Tea Variety",
    "Unit Count",
    "Diet Type",
    "Number of Items",
    "Container Type",
    "Specialty",
    "Region of Origin",
    "Recommended Uses For Product",
    "Allergen Information",
    "Special Ingredients",
    "Product Shelf Life",
    "Product Benefits",
    "Manufacturer",
    "Global Trade Identification Number",
    "Caffeine Content Description",
    "UPC",
    "Model Number",
    "Part Number",
    "Age Range Description",
    "Sweetness Description",
    "Item Type Name",
    "Item Weight",
    "Item Dimensions",
    "Item Volume",
    "Each Unit Count",
    "Best Sellers Rank",
    "ASIN",
    "Customer Reviews",
]

IMPORTANT_INFO_KEYS = [
    "Safety Information",
    "Directions",
    "Legal Disclaimer",
]

PRODUCT_DETAIL_KEYS = [
    "Is Discontinued By Manufacturer",
    "Product Dimensions",
    "Item model number",
    "Date First Available",
    "UPC",
    "Manufacturer",
    "ASIN",
    "Units",
    "Best Sellers Rank",
    "Customer Reviews",
]

# =========================================================
# HELPERS
# =========================================================

def debug(msg: str) -> None:
    print(f"[DEBUG] {msg}", flush=True)


def clean_inline_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("\u200e", "")
    text = text.replace("\u200f", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def clean_multiline_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("\u200e", "")
    text = text.replace("\u200f", "")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def slugify(text: str) -> str:
    text = clean_inline_text(text).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:80] or "untitled"


def save_json_atomic(data: Any, path: Path) -> None:
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp_path.replace(path)


def load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        debug(f"Could not read {path}: {e}")
        return []


def load_terms(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        terms = json.load(f)

    if not isinstance(terms, list):
        raise ValueError("terms_list.json must contain a JSON list")

    cleaned: list[str] = []
    seen: set[str] = set()

    terms = terms[0:50]
    for term in terms:
        t = clean_inline_text(str(term))
        if t and t not in seen:
            seen.add(t)
            cleaned.append(t)

    return cleaned


def upsert_by_keys(rows: list[dict[str, Any]], new_row: dict[str, Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    new_key = tuple(clean_inline_text(str(new_row.get(k, ""))) for k in keys)
    out: list[dict[str, Any]] = []
    replaced = False

    for row in rows:
        key = tuple(clean_inline_text(str(row.get(k, ""))) for k in keys)
        if key == new_key:
            if not replaced:
                out.append(new_row)
                replaced = True
        else:
            out.append(row)

    if not replaced:
        out.append(new_row)

    return out


def remove_rows_for_query(rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    q = clean_inline_text(query)
    return [r for r in rows if clean_inline_text(str(r.get("query", ""))) != q]


def close_safely(*objs) -> None:
    for obj in objs:
        try:
            if obj:
                obj.close()
        except Exception:
            pass


def get_body_text(page, timeout: int = 1200) -> str:
    try:
        return clean_multiline_text(page.locator("body").first.inner_text(timeout=timeout))
    except Exception:
        return ""


def is_likely_block_page_text(text: str) -> bool:
    low = text.lower()
    signals = [
        "enter the characters you see below",
        "sorry, we just need to make sure you're not a robot",
        "type the characters you see in this image",
        "api-services-support@amazon.com",
        "automated access to amazon data",
    ]
    return any(sig in low for sig in signals)


def looks_like_product_href(href: str) -> bool:
    if not href:
        return False

    low = href.lower()
    if any(x in low for x in [
        "/help/",
        "/gp/help/",
        "/customer-preferences/",
        "/hz/",
        "/cart",
        "/ap/signin",
        "/s?",
        "/search/",
        "javascript:",
        "#",
    ]):
        return False

    return any(x in low for x in [
        "/dp/",
        "/gp/product/",
        "/gp/aw/d/",
    ])


def looks_like_price_text(text: str) -> bool:
    text = clean_inline_text(text)
    return bool(text and re.fullmatch(r"\$?\d[\d,\s\.]*", text))


# =========================================================
# PAGE ACTIONS
# =========================================================

def dismiss_amazon_popups(page) -> None:
    selectors = [
        "button:has-text('Continue shopping')",
        "input[data-action-type='DISMISS']",
        "button:has-text('No thanks')",
        "button:has-text('Dismiss')",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible(timeout=500):
                btn.click(force=True, timeout=1000)
                page.wait_for_timeout(250)
        except Exception:
            pass


def wait_for_product_ready(page) -> None:
    start = time.time()
    while time.time() - start < 8:
        body = get_body_text(page, timeout=1000).lower()

        if not body:
            page.wait_for_timeout(300)
            continue

        if is_likely_block_page_text(body):
            return

        try:
            if page.locator("#productTitle").count() > 0:
                return
        except Exception:
            pass

        page.wait_for_timeout(350)


def open_item_details_dropdown(page) -> None:
    selectors = [
        "text=Item details",
        "button:has-text('Item details')",
        "span:has-text('Item details')",
        "div:has-text('Item details')",
        "[aria-label*='Item details']",
    ]

    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            if not loc.is_visible(timeout=700):
                continue

            for _ in range(4):
                try:
                    loc.click(force=True, timeout=1200)
                except Exception:
                    pass
                page.wait_for_timeout(700)

                body = get_body_text(page, timeout=1000).lower()
                if (
                    "special ingredients" in body
                    or "product shelf life" in body
                    or "product benefits" in body
                    or ("item details" in body and "loading content" not in body)
                ):
                    return
        except Exception:
            pass


def wait_for_item_details_ready(page) -> None:
    start = time.time()
    while time.time() - start < 10:
        body = get_body_text(page, timeout=1000).lower()
        if not body:
            page.wait_for_timeout(400)
            continue

        has_item_details = "item details" in body
        still_loading = "item details loading content" in body or "loading content." in body
        has_target_labels = (
            "special ingredients" in body
            or "product shelf life" in body
            or "product benefits" in body
            or "brand name" in body
            or "item form" in body
        )

        if has_target_labels:
            return

        if has_item_details and not still_loading:
            return

        page.wait_for_timeout(400)


# =========================================================
# SEARCH
# =========================================================

def collect_search_debug(page) -> dict[str, Any]:
    body = get_body_text(page)

    data = {
        "url": None,
        "title": None,
        "body_snippet": body[:1200] if body else None,
        "search_result_count_primary": None,
        "search_result_count_alt": None,
        "block_page_detected": is_likely_block_page_text(body) if body else False,
    }

    try:
        data["url"] = page.url
    except Exception:
        pass

    try:
        data["title"] = page.title()
    except Exception:
        pass

    try:
        data["search_result_count_primary"] = page.locator("div[data-component-type='s-search-result']").count()
    except Exception:
        pass

    try:
        data["search_result_count_alt"] = page.locator("[data-cel-widget^='search_result_']").count()
    except Exception:
        pass

    return data


def extract_search_candidates(page, max_candidates: int) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    base_selectors = [
        "div[data-component-type='s-search-result']",
        "[data-cel-widget^='search_result_']",
    ]
    title_anchor_selectors = [
        "h2 a",
        "[data-cy='title-recipe'] a",
        "a:has(h2)",
    ]

    for base_sel in base_selectors:
        try:
            cards = page.locator(base_sel)
            count = min(cards.count(), 100)

            for i in range(count):
                if len(results) >= max_candidates:
                    return results

                try:
                    card = cards.nth(i)
                    card_text = clean_multiline_text(card.inner_text(timeout=500))
                    if "sponsored" in card_text[:300].lower():
                        continue

                    href = None
                    title_text = None

                    for sel in title_anchor_selectors:
                        try:
                            a = card.locator(sel).first
                            if a.count() == 0:
                                continue

                            raw_href = a.get_attribute("href", timeout=600)
                            if not raw_href:
                                continue

                            full_href = raw_href if raw_href.startswith("http") else urljoin(AMAZON_DOMAIN, raw_href)
                            if not looks_like_product_href(full_href):
                                continue

                            txt = clean_inline_text(a.inner_text(timeout=600))
                            if not txt or looks_like_price_text(txt):
                                continue

                            href = full_href
                            title_text = txt
                            break
                        except Exception:
                            pass

                    if not href or not title_text or href in seen_urls:
                        continue

                    seen_urls.add(href)
                    results.append({"title": title_text, "href": href})
                except Exception:
                    continue
        except Exception:
            pass

        if results:
            break

    return results


def search_amazon(page, query: str, max_candidates: int) -> tuple[list[dict[str, str]], dict[str, Any]]:
    url = f"{AMAZON_DOMAIN}/s?k={quote_plus(query)}"
    debug(f"Searching: {query}")
    page.goto(url, wait_until="domcontentloaded", timeout=SEARCH_TIMEOUT_MS)
    page.wait_for_timeout(SEARCH_WAIT_MS)
    dismiss_amazon_popups(page)

    dbg = collect_search_debug(page)
    if dbg["block_page_detected"]:
        raise RuntimeError("Amazon block / captcha page detected on search page")

    candidates = extract_search_candidates(page, max_candidates=max_candidates)
    return candidates, dbg


# =========================================================
# PRODUCT FIELD EXTRACTION
# =========================================================

def extract_title(page) -> str | None:
    for sel in ["#productTitle", "span#productTitle"]:
        try:
            txt = clean_inline_text(page.locator(sel).first.inner_text(timeout=1000))
            if txt:
                return txt
        except Exception:
            pass
    return None


def extract_price(page) -> str | None:
    selectors = [
        "span.a-price span.a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#corePrice_feature_div span.a-offscreen",
    ]
    for sel in selectors:
        try:
            txt = clean_inline_text(page.locator(sel).first.inner_text(timeout=1000))
            if txt:
                return txt
        except Exception:
            pass
    return None


def extract_rating(page) -> float | None:
    selectors = [
        "span[data-hook='rating-out-of-text']",
        "#acrPopover",
        "i[data-hook='average-star-rating'] span",
    ]
    for sel in selectors:
        try:
            txt = clean_inline_text(page.locator(sel).first.inner_text(timeout=1000))
            if txt:
                m = re.search(r"(\d+(?:\.\d+)?)", txt)
                if m:
                    return float(m.group(1))
        except Exception:
            pass
    return None


def extract_review_count(page) -> int | None:
    selectors = [
        "#acrCustomerReviewText",
        "span[data-hook='total-review-count']",
    ]
    for sel in selectors:
        try:
            txt = clean_inline_text(page.locator(sel).first.inner_text(timeout=1000))
            if txt:
                m = re.search(r"([\d,]+)", txt)
                if m:
                    return int(m.group(1).replace(",", ""))
        except Exception:
            pass
    return None


def extract_asin(url: str, body_text: str) -> str | None:
    m = re.search(r"/dp/([A-Z0-9]{10})", url)
    if m:
        return m.group(1)

    m = re.search(r"\bASIN\b\s*([A-Z0-9]{10})", body_text, flags=re.IGNORECASE)
    if m:
        return m.group(1)

    return None


def extract_bullets(page) -> list[str]:
    bullets: list[str] = []
    for sel in ["#feature-bullets ul li", "#feature-bullets li"]:
        try:
            loc = page.locator(sel)
            count = min(loc.count(), 20)
            for i in range(count):
                txt = clean_inline_text(loc.nth(i).inner_text(timeout=700))
                if txt and txt not in bullets:
                    bullets.append(txt)
            if bullets:
                return bullets
        except Exception:
            pass
    return bullets


# =========================================================
# SECTION PARSERS
# =========================================================

def extract_detail_rows_from_text(body_text: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    lines = [clean_inline_text(x) for x in body_text.splitlines() if clean_inline_text(x)]

    for i, line in enumerate(lines):
        for label in PRODUCT_DETAIL_KEYS:
            if line == label:
                if i + 1 < len(lines):
                    rows[label] = lines[i + 1]
            elif line.startswith(label + " "):
                rows[label] = clean_inline_text(line[len(label):])

    return rows


def get_item_details_text(page, body_text: str) -> str:
    candidate_selectors = [
        "#productFactsDesktopExpander",
        "#productOverview_feature_div",
        "[id*='productFacts']",
        "#ppd",
        "body",
    ]

    chunks: list[str] = []
    for sel in candidate_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            txt = clean_multiline_text(loc.inner_text(timeout=1200))
            if txt and "item details" in txt.lower():
                chunks.append(txt)
        except Exception:
            pass

    return "\n".join(chunks) if chunks else body_text


def parse_item_details_from_text(text: str) -> dict[str, str]:
    """
    Improved Regex-based parser that handles mashed text (e.g. 'Special IngredientsRose')
    and invisible Left-to-Right markings (\u200e).
    """
    details: dict[str, str] = {}
    if not text:
        return details

    # Flatten text to one line and remove invisible artifacts
    flat_text = " ".join(text.splitlines())
    flat_text = flat_text.replace('\u200e', '').replace('\u200f', '').replace('\xa0', ' ')
    
    # Sort keys by length descending to match 'Special Ingredients' before 'Ingredients'
    sorted_keys = sorted(ITEM_DETAIL_KEYS, key=len, reverse=True)
    pattern = "|".join(re.escape(k) for k in sorted_keys)
    
    # Locate all keys in the mashed string
    matches = list(re.finditer(pattern, flat_text))
    
    for i in range(len(matches)):
        current_key = matches[i].group()
        start_index = matches[i].end()
        
        # Next boundary is the start of the next key OR the end of the text
        end_index = matches[i+1].start() if i + 1 < len(matches) else len(flat_text)
        
        raw_value = flat_text[start_index:end_index].strip()
        
        # Clean value: remove leading colons and strip trailing noise/breaks
        clean_val = raw_value.lstrip(":").strip()
        
        # Truncate if major UI sections leaked in
        stop_signals = ["About this item", "Product Description", "Customer reviews", "Small Business"]
        for signal in stop_signals:
            if signal in clean_val:
                clean_val = clean_val.split(signal)[0].strip()

        if clean_val and "loading content" not in clean_val.lower():
            details[current_key] = clean_val

    return details


def extract_important_information_from_text(body_text: str) -> dict[str, str | None]:
    result: dict[str, str | None] = {
        "Safety Information": None,
        "Directions": None,
        "Legal Disclaimer": None,
    }

    lines = [clean_inline_text(x) for x in body_text.splitlines() if clean_inline_text(x)]
    key_set = set(IMPORTANT_INFO_KEYS)
    stop_labels_lower = {
        "product description",
        "product details",
        "top",
        "similar",
        "customer reviews",
        "back to top",
    }

    i = 0
    while i < len(lines):
        line = lines[i]
        if line in key_set:
            collected: list[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt in key_set or nxt.lower() in stop_labels_lower:
                    break
                collected.append(nxt)
                j += 1

            value = clean_inline_text(" ".join(collected))
            result[line] = value or None
            i = j
        else:
            i += 1

    return result


# =========================================================
# DEBUG DUMP
# =========================================================

def maybe_write_debug_dump(
    query: str,
    rank: int,
    title: str | None,
    url: str,
    body_text: str,
    item_details_text: str,
    row: dict[str, Any],
) -> str | None:
    if row["Special Ingredients"] or row["Product Shelf Life"] or row["Product Benefits"]:
        return None

    DEBUG_DUMPS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{slugify(query)}_{rank:02d}_{slugify(title or 'no_title')}.txt"
    path = DEBUG_DUMPS_DIR / filename

    content = (
        f"QUERY: {query}\n"
        f"RANK: {rank}\n"
        f"TITLE: {title}\n"
        f"URL: {url}\n\n"
        f"=== ITEM DETAILS TEXT ===\n{item_details_text}\n\n"
        f"=== BODY TEXT ===\n{body_text}\n"
    )
    path.write_text(content, encoding="utf-8")
    return str(path)


# =========================================================
# PRODUCT PARSE
# =========================================================

def parse_product_page(page, query: str, rank: int, url: str, body_text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    title = extract_title(page)
    price = extract_price(page)
    rating = extract_rating(page)
    review_count = extract_review_count(page)
    asin = extract_asin(url, body_text)
    bullets = extract_bullets(page)

    item_details_text = get_item_details_text(page, body_text)
    item_details = parse_item_details_from_text(item_details_text)
    detail_rows = extract_detail_rows_from_text(body_text)
    important_information = extract_important_information_from_text(body_text)

    row = {
        "asin": asin,
        "amazon_title": title,
        "price": price,
        "rating": rating,
        "review_count": review_count,
        "detail_rows": detail_rows,
        "item_details": item_details,
        "bullets": bullets,
        "important_information": important_information,
        "Special Ingredients": item_details.get("Special Ingredients"),
        "Product Shelf Life": item_details.get("Product Shelf Life"),
        "Product Benefits": item_details.get("Product Benefits"),
        "Region of Origin": item_details.get("Region of Origin"),
        "url": url,
    }

    debug_dump_path = maybe_write_debug_dump(
        query=query,
        rank=rank,
        title=title,
        url=url,
        body_text=body_text,
        item_details_text=item_details_text,
        row=row,
    )

    debug_row = {
        "query": query,
        "url": url,
        "title": title,
        "has_special_ingredients_text": "special ingredients" in body_text.lower(),
        "has_product_shelf_life_text": "product shelf life" in body_text.lower(),
        "has_product_benefits_text": "product benefits" in body_text.lower(),
        "has_legal_disclaimer_text": "legal disclaimer" in body_text.lower(),
        "item_details_text_preview": item_details_text[:2500],
        "item_detail_keys_preview": list(item_details.keys())[:40],
        "important_information_preview": important_information,
        "debug_dump_path": debug_dump_path,
    }

    return row, debug_row


# =========================================================
# QUERY SCRAPE
# =========================================================

def scrape_query(context, query: str, max_products: int, success_rows, error_rows, debug_rows):
    query_start = time.time()

    search_page = context.new_page()
    try:
        candidates, search_debug = search_amazon(search_page, query, max_candidates=max_products)
    finally:
        close_safely(search_page)

    if not candidates:
        err = {
            "query": query,
            "status": "error",
            "error": f"No product cards detected. Search debug: {json.dumps(search_debug, ensure_ascii=False)}",
            "elapsed_seconds": None,
        }
        error_rows = upsert_by_keys(error_rows, err, ("query", "status"))
        debug_rows = upsert_by_keys(debug_rows, {"query": query, "url": "", **search_debug}, ("query", "url"))
        save_json_atomic(error_rows, ERROR_FILE)
        save_json_atomic(debug_rows, DEBUG_FILE)
        return success_rows, error_rows, debug_rows

    for rank, candidate in enumerate(candidates, start=1):
        product_url = candidate["href"]
        search_title = candidate["title"]

        page = context.new_page()
        try:
            debug(f"Opening product {rank}/{len(candidates)} for '{query}': {search_title}")
            page.goto(product_url, wait_until="domcontentloaded", timeout=PRODUCT_TIMEOUT_MS)
            dismiss_amazon_popups(page)
            wait_for_product_ready(page)
            open_item_details_dropdown(page)
            wait_for_item_details_ready(page)
            page.wait_for_timeout(PRODUCT_WAIT_MS)

            body_text = get_body_text(page, timeout=1200)

            if is_likely_block_page_text(body_text):
                raise RuntimeError("Blocked / captcha-like content detected in product page")

            product_row, product_debug = parse_product_page(page, query, rank, product_url, body_text)
            product_debug["fetch_method"] = "playwright"

            row = {
                "query": query,
                "status": "ok",
                "search_result_title": search_title,
                "search_result_rank_used": rank,
                "fetch_method": "playwright",
                "elapsed_seconds": round(time.time() - query_start, 2),
                **product_row,
            }

            success_rows = upsert_by_keys(success_rows, row, ("query", "url"))
            debug_rows = upsert_by_keys(debug_rows, product_debug, ("query", "url"))

            save_json_atomic(success_rows, OUTPUT_FILE)
            save_json_atomic(debug_rows, DEBUG_FILE)

        except Exception as e:
            err = {
                "query": query,
                "product_url": product_url,
                "search_result_title": search_title,
                "search_result_rank_used": rank,
                "status": "error",
                "error": str(e),
                "elapsed_seconds": None,
            }
            error_rows = upsert_by_keys(error_rows, err, ("query", "product_url"))
            save_json_atomic(error_rows, ERROR_FILE)
        finally:
            close_safely(page)

        time.sleep(SLEEP_BETWEEN_PRODUCTS)

    return success_rows, error_rows, debug_rows


# =========================================================
# MAIN
# =========================================================

def main():
    print("RUNNING REGEX-BASED ITEM DETAILS VERSION", flush=True)
    print(f"Saving products to: {OUTPUT_FILE}", flush=True)
    print(f"Saving errors to: {ERROR_FILE}", flush=True)
    print(f"Saving debug to: {DEBUG_FILE}", flush=True)
    print(f"Saving debug dumps to: {DEBUG_DUMPS_DIR}", flush=True)

    if not INPUT_TERMS_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_TERMS_FILE}")

    terms = load_terms(INPUT_TERMS_FILE)[:MAX_TERMS]

    success_rows = load_json_list(OUTPUT_FILE)
    error_rows = load_json_list(ERROR_FILE)
    debug_rows = load_json_list(DEBUG_FILE)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=0)
        context = browser.new_context(
            viewport={"width": 1365, "height": 900},
            user_agent=USER_AGENT,
        )

        try:
            total = len(terms)

            for idx, query in enumerate(terms, start=1):
                print(f"[{idx}/{total}] {query}", flush=True)

                success_rows = remove_rows_for_query(success_rows, query)
                error_rows = remove_rows_for_query(error_rows, query)
                debug_rows = remove_rows_for_query(debug_rows, query)

                save_json_atomic(success_rows, OUTPUT_FILE)
                save_json_atomic(error_rows, ERROR_FILE)
                save_json_atomic(debug_rows, DEBUG_FILE)

                try:
                    success_rows, error_rows, debug_rows = scrape_query(
                        context=context,
                        query=query,
                        max_products=MAX_PRODUCTS_PER_QUERY,
                        success_rows=success_rows,
                        error_rows=error_rows,
                        debug_rows=debug_rows,
                    )
                except Exception as e:
                    err = {
                        "query": query,
                        "status": "error",
                        "error": str(e),
                        "elapsed_seconds": None,
                    }
                    error_rows = upsert_by_keys(error_rows, err, ("query", "status"))
                    save_json_atomic(error_rows, ERROR_FILE)
                    debug(f"Saved top-level ERROR for '{query}': {e}")

                time.sleep(SLEEP_BETWEEN_QUERIES)

        finally:
            close_safely(context, browser)

    print(f"\nSaved {len(success_rows)} rows to {OUTPUT_FILE}", flush=True)
    print(f"Saved {len(error_rows)} rows to {ERROR_FILE}", flush=True)
    print(f"Saved {len(debug_rows)} rows to {DEBUG_FILE}", flush=True)


if __name__ == "__main__":
    main()
