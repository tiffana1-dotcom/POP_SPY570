from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from collections import Counter
import json
import re

SEED_URL = "https://www.yami.com/en"
HEADLESS = False

RELEVANT_KEYWORDS = [
    "tea", "matcha", "ginger", "herbal", "ginseng",
    "drink", "beverage", "jelly", "collagen", "mushroom",
    "wolfberry", "chrysanthemum", "jujube", "brown sugar",
    "granule", "powder", "instant", "supplement", "tonic",
    "kombucha", "gut health", "adaptogen", "probiotic",
    "oolong", "konjac", "goji", "longan", "latte",
    "fruit tea", "milk tea", "white fungus", "snow fungus",
    "bird's nest", "osmanthus", "throat candy"
]

STOPWORDS = [
    "the", "and", "for", "with", "from", "new", "sale", "shop", "home",
    "sign", "login", "sign up", "cart", "categories", "show", "only",
    "best", "sellers", "arrivals", "brands", "subscribe", "services",
    "fulfilled", "skip", "main", "content", "search", "filter",
    "keyboard", "shortcuts", "use", "keys", "navigate", "privacy",
    "cookie", "cookies", "consent", "reject", "accept", "customise",
    "powered", "necessary", "active", "description", "available",
    "view", "more", "shop", "all", "rating", "stars", "sold", "options"
]


def debug(msg: str):
    print(f"[DEBUG] {msg}", flush=True)


def dismiss_cookie_banner(page):
    selectors = [
        "button:has-text('Accept All')",
        "button:has-text('Accept')",
        "button:has-text('I Agree')",
        "button:has-text('Got it')",
        "button:has-text('Allow all')",
    ]

    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1500):
                btn.click(timeout=2000, force=True)
                page.wait_for_timeout(1500)
                debug(f"Clicked cookie button: {sel}")
                return True
        except:
            pass

    debug("No cookie button clicked")
    return False


def looks_relevant(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in RELEVANT_KEYWORDS)


def clean_visible_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)   # collapse spaces only
    text = re.sub(r"\n+", "\n", text)     # preserve line breaks
    return text.strip()


def extract_content_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # Remove obvious junk sections first
    for tag in soup.find_all([
        "nav", "header", "footer", "form", "style", "script",
        "meta", "noscript", "svg"
    ]):
        try:
            tag.decompose()
        except:
            pass

    # Remove modal / cookie / banner-ish elements safely
    for tag in soup.find_all(True):
        try:
            attrs = getattr(tag, "attrs", {}) or {}

            tag_id = str(attrs.get("id", ""))
            tag_class = attrs.get("class", [])
            if isinstance(tag_class, list):
                tag_class = " ".join(tag_class)
            else:
                tag_class = str(tag_class)

            aria_label = str(attrs.get("aria-label", ""))

            attrs_text = " ".join([tag_id, tag_class, aria_label]).lower()

            if any(x in attrs_text for x in [
                "cookie", "consent", "privacy", "modal", "dialog", "popup", "banner"
            ]):
                tag.decompose()
        except:
            pass

    text_content = soup.get_text(separator="\n", strip=True)
    return clean_visible_text(text_content)


def extract_relevant_lines(text: str) -> list[str]:
    raw_lines = [line.strip() for line in text.split("\n")]
    raw_lines = [line for line in raw_lines if len(line) >= 4]

    filtered = []
    seen = set()

    for line in raw_lines:
        low = line.lower()

        # skip obvious junk
        if any(j in low for j in [
            "we value your privacy",
            "cookie",
            "consent",
            "accept all",
            "reject all",
            "sign in / sign up",
            "download the yami app",
            "feedback",
            "chat with us",
            "app store",
            "google play",
            "live chat",
            "shop on the go",
            "sale price alerts",
            "exclusive discounts",
            "faster & more secure checkout",
            "easy order tracking",
            "main content",
            "skip banner",
            "keyboard shortcuts",
            "show/hide shortcuts"
        ]):
            continue

        # keep anything POP-relevant
        if not looks_relevant(low):
            continue

        if low in seen:
            continue
        seen.add(low)

        filtered.append(line)

    return filtered


def extract_keywords_and_phrases(lines: list[str]):
    words = []
    phrases = []

    for line in lines:
        cleaned = re.sub(r"[^a-zA-Z0-9\s\-\+]", " ", line.lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        tokens = cleaned.split()

        for token in tokens:
            if len(token) < 4:
                continue
            if token in STOPWORDS:
                continue
            words.append(token)

        for i in range(len(tokens) - 1):
            phrase = f"{tokens[i]} {tokens[i+1]}"
            if any(part in STOPWORDS for part in phrase.split()):
                continue
            phrases.append(phrase)

    word_counts = Counter(words)
    phrase_counts = Counter(phrases)

    top_words = [
        {"term": term, "count": count}
        for term, count in word_counts.most_common(100)
        if looks_relevant(term)
    ]

    top_phrases = [
        {"term": term, "count": count}
        for term, count in phrase_counts.most_common(100)
        if looks_relevant(term)
    ]

    return top_words, top_phrases


def main():
    debug("Launching browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=150)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        debug(f"Opening {SEED_URL}")
        page.goto(SEED_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)

        dismiss_cookie_banner(page)

        for i in range(4):
            debug(f"Scrolling {i+1}/4")
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(1000)

        debug("Capturing rendered HTML...")
        html = page.content()

        debug("Closing browser...")
        browser.close()

    debug("Extracting cleaned text with BeautifulSoup...")
    full_text = extract_content_text_from_html(html)
    debug(f"Extracted text length: {len(full_text)}")

    debug("Saving yami_content.txt...")
    with open("yami_content.txt", "w", encoding="utf-8") as f:
        f.write(full_text)

    debug("Extracting relevant lines...")
    relevant_lines = extract_relevant_lines(full_text)
    debug(f"relevant_lines count: {len(relevant_lines)}")
    debug(f"first 20 relevant lines: {relevant_lines[:20]}")

    with open("yami_relevant_lines.json", "w", encoding="utf-8") as f:
        json.dump(relevant_lines, f, indent=2, ensure_ascii=False)

    debug("Extracting keywords and phrases...")
    top_words, top_phrases = extract_keywords_and_phrases(relevant_lines)
    debug(f"top_words count: {len(top_words)}")
    debug(f"top_phrases count: {len(top_phrases)}")

    with open("yami_trend_candidates.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "top_words": top_words[:30],
                "top_phrases": top_phrases[:30]
            },
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\nTop relevant lines:", flush=True)
    for line in relevant_lines[:20]:
        print("-", line, flush=True)

    print("\nTop words:", flush=True)
    for row in top_words[:15]:
        print(row["term"], "->", row["count"], flush=True)

    print("\nTop phrases:", flush=True)
    for row in top_phrases[:15]:
        print(row["term"], "->", row["count"], flush=True)

    print("\nSaved files:", flush=True)
    print("- yami_content.txt", flush=True)
    print("- yami_relevant_lines.json", flush=True)
    print("- yami_trend_candidates.json", flush=True)


if __name__ == "__main__":
    main()
