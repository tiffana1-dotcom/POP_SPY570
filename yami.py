from playwright.sync_api import sync_playwright
from collections import Counter
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import json
import re

HEADLESS = False

# Start from the full beverage category, page 1
SEED_URL = "https://www.yami.com/en/c/beverage/310?page=1&cat_id=310"

STOPWORDS = {
    "the", "and", "for", "with", "from", "new", "sale", "shop", "home",
    "sign", "login", "sign up", "cart", "categories", "show", "only",
    "best", "sellers", "arrivals", "brands", "subscribe", "services",
    "fulfilled", "skip", "main", "content", "search", "filter",
    "cookie", "consent", "accept", "reject", "privacy",
    "rating", "stars", "sold", "options", "pack", "value", "choice",
    "price", "usd", "oz", "ml", "g", "kg", "lb", "count", "ct"
}


def debug(msg: str):
    print(f"[DEBUG] {msg}", flush=True)


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def dismiss_cookie_banner(page):
    selectors = [
        "button:has-text('Accept All')",
        "button:has-text('Accept')",
        "button:has-text('I Agree')",
        "button:has-text('Agree')",
        "button:has-text('Got it')",
        "button:has-text('Allow all')",
    ]

    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible(timeout=1200):
                btn.click(timeout=3000, force=True)
                page.wait_for_timeout(1200)
                debug(f"Clicked cookie button: {sel}")
                return True
        except:
            pass

    debug("No cookie banner clicked")
    return False


def auto_scroll(page, rounds=8, pause_ms=1200):
    last_height = 0

    for i in range(rounds):
        try:
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(pause_ms)

            new_height = page.evaluate("document.body.scrollHeight")
            debug(f"Scroll {i+1}/{rounds}, height={new_height}")

            if new_height == last_height and i >= 2:
                break
            last_height = new_height
        except:
            pass


def is_bad_title(text: str) -> bool:
    low = text.lower()

    junk_substrings = [
        "cookie", "consent", "privacy", "accept", "reject",
        "powered by", "doubleclick", "tiktok analytics",
        "visitor_info1_live", "clarity", "google",
        "english", "简体中文", "繁體中文", "한국어", "日本語",
        "sell products on yami", "supply to yami", "contact us",
        "feedback", "let’s keep in touch", "let's keep in touch",
        "used to", "description is currently not available",
        "no description available", "revisit consent button",
        "necessary always active", "always active",
        "category", "hours", "months", "days", "minute", "minutes",
        "year", "years", "expires", "less than a minute",
        "app内嵌状态栏高度"
    ]

    if any(j in low for j in junk_substrings):
        return True

    if len(text) < 4 or len(text) > 220:
        return True

    return False


def looks_like_product_title(text: str) -> bool:
    if not text:
        return False

    if is_bad_title(text):
        return False

    low = text.lower()

    # product titles usually have at least 2 words or a size/count
    if len(text.split()) >= 2:
        return True

    if any(ch.isdigit() for ch in text):
        return True

    product_hints = [
        "tea", "drink", "beverage", "juice", "coffee", "milk",
        "water", "soda", "sparkling", "matcha", "latte",
        "herbal", "powder", "coconut", "soy", "jelly"
    ]
    if any(h in low for h in product_hints):
        return True

    return False


def extract_titles_from_dom(page) -> list[str]:
    """
    Prefer real product image alts / product links from the rendered page
    instead of scraping the entire HTML text.
    """
    titles = []
    seen = set()

    selectors = [
        # best case: product images with alt text inside product links
        "a[href*='/p/'] img[alt]",
        "a[href*='/product/'] img[alt]",
        "a img[alt]",

        # fallbacks if Yami structure differs
        "[data-testid*='product'] img[alt]",
        "[class*='product'] img[alt]",
        "[class*='goods'] img[alt]",
    ]

    for sel in selectors:
        try:
            loc = page.locator(sel)
            count = loc.count()
            debug(f"Selector {sel} -> {count} matches")

            for i in range(count):
                try:
                    alt = loc.nth(i).get_attribute("alt") or ""
                    alt = clean_text(alt)

                    if not looks_like_product_title(alt):
                        continue

                    low = alt.lower()
                    if low not in seen:
                        seen.add(low)
                        titles.append(alt)
                except:
                    pass

            if titles:
                debug(f"Collected {len(titles)} titles from selector: {sel}")
                return titles

        except:
            pass

    # fallback: visible anchors that look like product titles
    try:
        loc = page.locator("a")
        count = loc.count()
        debug(f"Fallback anchor scan -> {count} anchors")

        for i in range(count):
            try:
                text = clean_text(loc.nth(i).inner_text(timeout=500))
                href = loc.nth(i).get_attribute("href") or ""

                if not href:
                    continue

                # keep likely product-ish links
                if "/p/" not in href and "/product/" not in href:
                    continue

                if not looks_like_product_title(text):
                    continue

                low = text.lower()
                if low not in seen:
                    seen.add(low)
                    titles.append(text)
            except:
                pass

    except:
        pass

    debug(f"Fallback anchor extraction found {len(titles)} titles")
    return titles


def extract_keywords_and_phrases(lines: list[str]):
    words = []
    phrases = []

    for line in lines:
        cleaned = re.sub(r"[^a-zA-Z0-9\s\-\+]", " ", line.lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        tokens = cleaned.split()

        filtered = []
        for token in tokens:
            if len(token) < 3:
                continue
            if token in STOPWORDS:
                continue
            if token.isdigit():
                continue
            filtered.append(token)
            words.append(token)

        for i in range(len(filtered) - 1):
            phrases.append(f"{filtered[i]} {filtered[i+1]}")

        for i in range(len(filtered) - 2):
            phrases.append(f"{filtered[i]} {filtered[i+1]} {filtered[i+2]}")

    word_counts = Counter(words)
    phrase_counts = Counter(phrases)

    all_words = sorted(
        [{"term": term, "count": count} for term, count in word_counts.items()],
        key=lambda x: (-x["count"], x["term"])
    )

    all_phrases = sorted(
        [{"term": term, "count": count} for term, count in phrase_counts.items()],
        key=lambda x: (-x["count"], x["term"])
    )

    return all_words, all_phrases


def get_page_signature(page) -> str:
    """
    Signature based on extracted product titles, not whole page text.
    """
    try:
        titles = extract_titles_from_dom(page)
        return " | ".join(titles[:12]).lower()
    except:
        return ""


def wait_for_page_change(page, old_sig: str, timeout_loops=20) -> bool:
    for _ in range(timeout_loops):
        page.wait_for_timeout(800)
        new_sig = get_page_signature(page)
        if new_sig and new_sig != old_sig:
            return True
    return False


def get_current_page_number(page):
    candidates = [
        "[aria-current='page']",
        ".active",
        ".is-active",
        ".current",
        "li.active",
        "a.active",
        "button.active",
    ]

    for sel in candidates:
        try:
            loc = page.locator(sel)
            count = loc.count()

            for i in range(count):
                try:
                    txt = clean_text(loc.nth(i).inner_text(timeout=500))
                    if txt.isdigit():
                        return int(txt)
                except:
                    pass
        except:
            pass

    # fallback: parse from URL
    try:
        parsed = urlparse(page.url)
        qs = parse_qs(parsed.query)
        if "page" in qs:
            return int(qs["page"][0])
    except:
        pass

    return None


def increment_page_in_url(url: str):
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)

        if "page" not in qs:
            qs["page"] = ["2"]
        else:
            current = int(qs["page"][0])
            qs["page"] = [str(current + 1)]

        new_query = urlencode(qs, doseq=True)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
    except:
        return None


def click_direct_page_number(page, target_num: int, old_sig: str) -> bool:
    target = str(target_num)

    selectors = [
        f"a:has-text('{target}')",
        f"button:has-text('{target}')",
        f"text='{target}'",
    ]

    for sel in selectors:
        try:
            loc = page.locator(sel)
            count = loc.count()

            for i in range(count):
                btn = loc.nth(i)

                try:
                    txt = clean_text(btn.inner_text(timeout=500))
                except:
                    continue

                if txt != target:
                    continue

                try:
                    if not btn.is_visible(timeout=500):
                        continue
                except:
                    continue

                try:
                    btn.scroll_into_view_if_needed(timeout=2000)
                except:
                    pass

                page.wait_for_timeout(400)
                debug(f"Trying direct page click: {target} via {sel}")
                btn.click(force=True, timeout=5000)

                if wait_for_page_change(page, old_sig):
                    debug(f"Moved directly to page {target}")
                    return True

        except:
            pass

    return False


def click_right_arrow(page, old_sig: str) -> bool:
    arrow_selectors = [
        "[aria-label='Next page']",
        "[aria-label='next page']",
        "[aria-label='Next']",
        "[aria-label='next']",
        "button[aria-label*='next' i]",
        "a[aria-label*='next' i]",
        "li[title='Next']",
        "button[title='Next']",
        "a[title='Next']",
        "text='>'",
        "text='→'",
        "text='›'",
        "text='»'",
    ]

    for sel in arrow_selectors:
        try:
            loc = page.locator(sel)
            count = loc.count()

            for i in range(count):
                el = loc.nth(i)

                try:
                    if not el.is_visible(timeout=500):
                        continue
                except:
                    continue

                try:
                    aria_disabled = el.get_attribute("aria-disabled")
                    disabled = el.get_attribute("disabled")
                    class_attr = (el.get_attribute("class") or "").lower()
                    if aria_disabled == "true" or disabled is not None or "disabled" in class_attr:
                        continue
                except:
                    pass

                try:
                    el.scroll_into_view_if_needed(timeout=2000)
                except:
                    pass

                page.wait_for_timeout(400)
                debug(f"Trying right-arrow selector: {sel}")
                el.click(force=True, timeout=5000)

                if wait_for_page_change(page, old_sig):
                    debug("Right arrow worked")
                    return True
        except:
            pass

    return False


def go_to_next_page(page) -> bool:
    old_sig = get_page_signature(page)
    current_page = get_current_page_number(page)
    debug(f"Detected current page: {current_page}")

    # 1) try clicking the next page number directly
    if current_page is not None:
        if click_direct_page_number(page, current_page + 1, old_sig):
            return True

    # 2) try a visible right-arrow / next control
    if click_right_arrow(page, old_sig):
        return True

    # 3) fallback: increment page in URL
    try:
        current_url = page.url
        next_url = increment_page_in_url(current_url)

        if next_url and next_url != current_url:
            debug(f"Trying URL increment fallback: {next_url}")
            page.goto(next_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)

            new_sig = get_page_signature(page)
            if new_sig and new_sig != old_sig:
                debug("URL increment worked")
                return True
    except Exception as e:
        debug(f"URL increment fallback failed: {e}")

    return False


def main():
    all_titles = []
    seen_titles = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=80)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        debug(f"Opening {SEED_URL}")
        page.goto(SEED_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        dismiss_cookie_banner(page)

        page_loop_index = 1

        while True:
            print(f"[SCRAPE LOOP {page_loop_index}]", flush=True)

            auto_scroll(page, rounds=8, pause_ms=1200)

            titles = extract_titles_from_dom(page)

            new_count = 0
            for title in titles:
                low = title.lower()
                if low not in seen_titles:
                    seen_titles.add(low)
                    all_titles.append(title)
                    new_count += 1

            current_page = get_current_page_number(page)
            print(f"  Website page: {current_page}", flush=True)
            print(f"  +{new_count} new titles", flush=True)
            print(f"  Total unique titles so far: {len(all_titles)}", flush=True)

            moved = go_to_next_page(page)
            if not moved:
                print("No more pages — stopping.", flush=True)
                break

            page_loop_index += 1

        browser.close()

    print(f"\nTotal unique titles collected: {len(all_titles)}", flush=True)

    with open("yami_titles.json", "w", encoding="utf-8") as f:
        json.dump(all_titles, f, indent=2, ensure_ascii=False)

    all_words, all_phrases = extract_keywords_and_phrases(all_titles)

    with open("yami_trend_candidates.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "all_words": all_words,
                "all_phrases": all_phrases
            },
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\nCollected titles (first 30 shown):", flush=True)
    for title in all_titles[:30]:
        print("-", title, flush=True)

    print("\nTop words (first 30 shown):", flush=True)
    for row in all_words[:30]:
        print(f'{row["term"]} -> {row["count"]}', flush=True)

    print("\nTop phrases (first 30 shown):", flush=True)
    for row in all_phrases[:30]:
        print(f'{row["term"]} -> {row["count"]}', flush=True)

    print("\nSaved files:", flush=True)
    print("- yami_titles.json", flush=True)
    print("- yami_trend_candidates.json", flush=True)


if __name__ == "__main__":
    main()
