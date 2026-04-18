import json
import re
from pathlib import Path
from collections import defaultdict

INPUT_FILE = "yami_titles.json"
TOP100_FILE = "tea_trend_signals_top100.json"
ALL_CANDIDATES_FILE = "tea_trend_signals_all_candidates.json"

TOP_K = 100
MAX_NGRAM = 4
MIN_WORD_LEN = 3

# Core tea / herbal anchors
TEA_ANCHORS = {
    "tea", "matcha", "oolong", "green tea", "black tea", "white tea",
    "herbal tea", "herbal", "jasmine", "chrysanthemum", "hojicha",
    "genmaicha", "pu erh", "pu-erh", "longjing", "tieguanyin",
    "barley tea", "buckwheat tea", "milk tea", "tea latte", "latte"
}

# Known ingredient-like concepts
INGREDIENT_LIKE = {
    "ginger", "ginseng", "honey", "osmanthus", "goji", "jujube", "longan",
    "buckwheat", "tartary", "tartary buckwheat",
    "aloe", "vera", "aloe vera",
    "lychee", "yuzu", "peach", "white peach", "grapefruit", "pomelo",
    "lemon", "lime", "mango", "melon", "apple", "pear", "grape",
    "strawberry", "blueberry", "pineapple", "coconut", "barley",
    "rice", "corn", "brown sugar", "black sugar", "citron", "kumquat",
    "loquat", "rose", "lavender", "hibiscus", "mint", "gardenia",
    "cassia", "hawthorn", "plum", "apricot", "red date", "coix seed",
    "honeysuckle", "wolfberry", "calamansi", "pomegranate", "mai dong",
    "loquat flower", "tangerine peel", "green citrus", "gold cassia"
}

# Useful only when attached to tea phrases, not alone
MODIFIERS = {
    "sugar free", "low sugar", "unsweetened", "low calorie", "0 sugar",
    "0 calories", "zero sugar", "zero calorie", "caffeine free"
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "with", "in", "on", "to", "by",
    "from", "at", "as", "is", "are", "into", "over", "under", "may", "vary",
    "packaging", "pack", "value", "set", "combo", "boxes", "box", "bottle",
    "bottles", "bags", "bag", "cups", "cup", "can", "cans", "pc", "pcs",
    "oz", "fl", "ml", "l", "g", "kg", "lb", "x", "new", "drink", "beverage",
    "flavor", "flavored", "refreshing", "healthy", "sweet", "creamy", "premium",
    "special", "classic", "original", "natural", "fresh", "instant", "soft",
    "rich", "style", "mixed", "pack", "value", "vary", "contains", "real",
    "juice", "water", "soda", "carbonated", "non", "fat", "calories", "added"
}

BAD_SUBSTRINGS = {
    "cookie", "consent", "privacy", "powered by", "feedback", "contact us",
    "doubleclick", "google", "tiktok analytics", "visitor_info1_live"
}

MARKETING = {
    "trending", "tiktok", "exclusive", "limited", "gift", "value",
    "summer", "selected", "favorite", "pick", "anime", "finds", "pack",
    "combo", "seasonal"
}

PACKAGING = {
    "pack", "bottle", "box", "can", "bag", "cup", "jar", "pouch", "bags",
    "boxes", "cans", "cups", "pcs", "piece", "pieces"
}

WEAK_ADJECTIVES = {"fresh", "natural", "premium", "classic", "original", "healthy", "rich", "sweet"}


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9\s\-+&]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return normalize_text(text).split()


def title_is_usable(title: str) -> bool:
    t = normalize_text(title)
    if not t or len(t) < 4:
        return False
    if any(bad in t for bad in BAD_SUBSTRINGS):
        return False
    return True


def load_titles(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    cleaned = []
    seen = set()

    for item in raw:
        title = clean_text(str(item))
        if not title_is_usable(title):
            continue
        norm = normalize_text(title)
        if norm not in seen:
            seen.add(norm)
            cleaned.append(norm)

    return cleaned


def filtered_tokens_for_title(title: str) -> list[str]:
    toks = tokenize(title)
    out = []
    for tok in toks:
        if tok in STOPWORDS:
            continue
        if tok.isdigit():
            continue
        if len(tok) < MIN_WORD_LEN:
            continue
        out.append(tok)
    return out


def title_has_anchor(title: str) -> bool:
    t = normalize_text(title)
    return any(anchor in t for anchor in TEA_ANCHORS)


def ngrams(tokens: list[str], max_n: int = 4):
    for n in range(1, max_n + 1):
        for i in range(len(tokens) - n + 1):
            yield " ".join(tokens[i:i+n])


def phrase_has_anchor(term: str) -> bool:
    return any(anchor in term for anchor in TEA_ANCHORS)


def phrase_has_known_ingredient(term: str) -> bool:
    if term in INGREDIENT_LIKE:
        return True
    toks = term.split()
    for i, tok in enumerate(toks):
        if tok in INGREDIENT_LIKE:
            return True
        if i < len(toks) - 1:
            bg = f"{toks[i]} {toks[i+1]}"
            if bg in INGREDIENT_LIKE:
                return True
    return False


def looks_like_ingredient_phrase(term: str) -> bool:
    """
    Fallback for unknown ingredients not in INGREDIENT_LIKE.
    """
    tokens = term.split()

    if len(tokens) < 2:
        return False

    if all(t in STOPWORDS for t in tokens):
        return False

    if any(t in PACKAGING for t in tokens):
        return False

    if any(t in MARKETING for t in tokens):
        return False

    if tokens[0] in WEAK_ADJECTIVES:
        return False

    # too many weak generic tokens = probably not a real ingredient phrase
    genericish = {"sugar", "free", "low", "calorie", "calories", "healthy", "refreshing", "drink", "beverage"}
    if sum(t in genericish for t in tokens) >= len(tokens) - 1:
        return False

    return True


def phrase_is_only_modifier(term: str) -> bool:
    return term in MODIFIERS


def phrase_is_bad(term: str) -> bool:
    toks = term.split()
    if any(tok in MARKETING for tok in toks):
        return True
    if any(tok in PACKAGING for tok in toks):
        return True
    return False


def build_candidates_from_titles(titles: list[str]):
    """
    Build candidates only from tea-anchored titles.
    """
    term_to_titles = defaultdict(set)

    for title in titles:
        if not title_has_anchor(title):
            continue

        toks = filtered_tokens_for_title(title)
        if not toks:
            continue

        for term in ngrams(toks, MAX_NGRAM):
            if len(term) < 3:
                continue
            if phrase_is_bad(term):
                continue
            term_to_titles[term].add(title)

    return term_to_titles


def repetition_bonus(match_count: int) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    if match_count >= 50:
        score += 4
        reasons.append(f"strong repetition in tea titles ({match_count})")
    elif match_count >= 20:
        score += 3
        reasons.append(f"moderate repetition in tea titles ({match_count})")
    elif match_count >= 10:
        score += 2
        reasons.append(f"light repetition in tea titles ({match_count})")
    elif match_count >= 3:
        score += 1
        reasons.append(f"limited repetition in tea titles ({match_count})")

    return score, reasons


def classify_term_type(term: str) -> str:
    if phrase_has_anchor(term):
        if "latte" in term or "milk tea" in term:
            return "format"
        if "tea" in term or "matcha" in term or "oolong" in term or "herbal" in term:
            return "tea_phrase"

    if phrase_has_known_ingredient(term) or looks_like_ingredient_phrase(term):
        return "ingredient_phrase"

    return "other"


def score_term(term: str, match_count: int):
    score = 0
    reasons = []
    term_type = classify_term_type(term)
    toks = term.split()

    if phrase_is_only_modifier(term):
        score -= 5
        reasons.append("modifier alone")

    if phrase_is_bad(term):
        score -= 5
        reasons.append("marketing/packaging noise")

    if phrase_has_anchor(term):
        score += 4
        reasons.append("contains tea anchor")

    if phrase_has_known_ingredient(term):
        score += 3
        reasons.append("known ingredient-like concept")
    elif looks_like_ingredient_phrase(term):
        score += 2
        reasons.append("unknown but noun-like ingredient phrase")

    if len(toks) >= 2:
        score += 2
        reasons.append("multi-word specific phrase")

    if len(toks) >= 3:
        score += 1
        reasons.append("higher specificity")

    if match_count == 1 and len(toks) >= 2 and (phrase_has_anchor(term) or phrase_has_known_ingredient(term) or looks_like_ingredient_phrase(term)):
        score += 2
        reasons.append("rare but specific tea-context concept")

    rep_score, rep_reasons = repetition_bonus(match_count)
    score += rep_score
    reasons.extend(rep_reasons)

    if any(mod in term for mod in MODIFIERS) and len(toks) >= 3 and phrase_has_anchor(term):
        score += 1
        reasons.append("modifier attached to tea phrase")

    if len(toks) == 1 and not phrase_has_anchor(term) and term not in INGREDIENT_LIKE:
        score -= 2
        reasons.append("weak singleton")

    return score, reasons, term_type


def keep_candidate(term: str, score: int, term_type: str, match_count: int) -> bool:
    toks = term.split()

    if phrase_is_only_modifier(term):
        return False

    if term_type in {"format", "tea_phrase"} and score >= 5:
        return True

    if len(toks) >= 2 and (phrase_has_known_ingredient(term) or looks_like_ingredient_phrase(term)) and score >= 5:
        return True

    if len(toks) == 1 and term in INGREDIENT_LIKE and match_count >= 3 and score >= 4:
        return True

    return False


def overlap_ratio(a: str, b: str) -> float:
    sa = set(a.split())
    sb = set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def choose_better(existing: dict, new: dict) -> dict:
    key_existing = (existing["score"], len(existing["term"].split()), existing["title_match_count"])
    key_new = (new["score"], len(new["term"].split()), new["title_match_count"])
    return new if key_new > key_existing else existing


def dedupe_candidates(candidates: list[dict]) -> list[dict]:
    kept = []

    for cand in candidates:
        replaced = False
        for i, prev in enumerate(kept):
            t1 = cand["term"]
            t2 = prev["term"]

            if (
                t1 == t2
                or t1 in t2
                or t2 in t1
                or overlap_ratio(t1, t2) >= 0.8
            ):
                kept[i] = choose_better(prev, cand)
                replaced = True
                break

        if not replaced:
            kept.append(cand)

    kept.sort(key=lambda x: (-x["score"], -x["title_match_count"], -len(x["term"].split()), x["term"]))
    return kept


def balanced_top_100(candidates: list[dict]) -> list[dict]:
    buckets = {
        "format": [],
        "tea_phrase": [],
        "ingredient_phrase": [],
        "other": [],
    }

    for c in candidates:
        buckets[c["term_type"]].append(c)

    for k in buckets:
        buckets[k].sort(key=lambda x: (-x["score"], -x["title_match_count"], -len(x["term"].split()), x["term"]))

    targets = {
        "format": 20,
        "tea_phrase": 35,
        "ingredient_phrase": 45,
        "other": 0,
    }

    final = []
    used = set()

    for bucket, target in targets.items():
        count = 0
        for c in buckets[bucket]:
            if count >= target:
                break
            if c["term"] not in used:
                final.append(c)
                used.add(c["term"])
                count += 1

    leftovers = []
    for bucket in buckets:
        for c in buckets[bucket]:
            if c["term"] not in used:
                leftovers.append(c)

    leftovers.sort(key=lambda x: (-x["score"], -x["title_match_count"], -len(x["term"].split()), x["term"]))

    for c in leftovers:
        if len(final) >= TOP_K:
            break
        final.append(c)
        used.add(c["term"])

    final.sort(key=lambda x: (-x["score"], -x["title_match_count"], -len(x["term"].split()), x["term"]))
    return final[:TOP_K]


def main():
    if not Path(INPUT_FILE).exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")

    titles = load_titles(INPUT_FILE)
    term_to_titles = build_candidates_from_titles(titles)

    all_candidates = []
    for term, matched_titles in term_to_titles.items():
        match_count = len(matched_titles)
        score, reasons, term_type = score_term(term, match_count)

        if not keep_candidate(term, score, term_type, match_count):
            continue

        payload = {
            "term": term,
            "term_type": term_type,
            "title_match_count": match_count,
            "score": score,
            "reasons": reasons,
            "example_titles": sorted(list(matched_titles))[:5],
        }
        all_candidates.append(payload)

    all_candidates.sort(key=lambda x: (-x["score"], -x["title_match_count"], -len(x["term"].split()), x["term"]))
    deduped = dedupe_candidates(all_candidates)
    top100 = balanced_top_100(deduped)

    with open(ALL_CANDIDATES_FILE, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)

    with open(TOP100_FILE, "w", encoding="utf-8") as f:
        json.dump(top100, f, indent=2, ensure_ascii=False)

    print("Done.")
    print(f"Titles used: {len(titles)}")
    print(f"All kept candidates: {len(deduped)}")
    print(f"Top 100 saved: {len(top100)}")
    print(f"Saved: {ALL_CANDIDATES_FILE}")
    print(f"Saved: {TOP100_FILE}")
    print("\nTop 30:")
    for row in top100[:30]:
        print(
            f"- {row['term']} | type={row['term_type']} | "
            f"titles={row['title_match_count']} | score={row['score']}"
        )


if __name__ == "__main__":
    main()
