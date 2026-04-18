import json
import re
from pathlib import Path
from collections import defaultdict

INPUT_FILE = "yami_titles.json"
TOP_OUTPUT_FILE = "tea_trend_signals_clean_top150.json"
ALL_FILE = "tea_trend_signals_clean_all.json"

TOP_K = 150
MAX_NGRAM = 4
MIN_WORD_LEN = 3

# Core tea / herbal anchors
TEA_ANCHORS = {
    "tea", "matcha", "oolong", "green tea", "black tea", "white tea",
    "herbal tea", "herbal", "jasmine", "chrysanthemum", "hojicha",
    "genmaicha", "pu erh", "pu-erh", "longjing", "tieguanyin",
    "barley tea", "buckwheat tea", "milk tea", "tea latte", "latte",
    "thai tea"
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
    "loquat flower", "tangerine peel", "green citrus", "gold cassia",
    "mugicha", "thai tea"
}

# Regional/style words that should be allowed in tea concepts
STYLE_WORDS = {
    "thai", "hong", "kong", "japanese", "kyoto", "uji", "oriental",
    "royal", "ceylon", "assam", "nanyang"
}

# Useful only inside longer anchored phrases, not alone
MODIFIERS = {
    "sugar free", "low sugar", "unsweetened", "low calorie", "0 sugar",
    "0 calories", "zero sugar", "zero calorie", "caffeine free"
}

REMOVABLE_MODIFIER_TOKENS = {
    "unsweetened", "free", "low", "calorie", "calories",
    "zero", "caffeine", "fat", "light", "reduced",
    "healthy", "refreshing"
}

REMOVABLE_MODIFIER_PHRASES = {
    "sugar free",
    "low sugar",
    "unsweetened",
    "low calorie",
    "zero sugar",
    "zero calorie",
    "caffeine free",
    "low calories",
    "0 sugar",
    "0 calories",
}

# Treat these as removable noise words for concept extraction / display
REMOVABLE_NOISE_TOKENS = {
    "sugar",  # so "sugar ginger tea" collapses to "ginger tea"
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "with", "in", "on", "to", "by",
    "from", "at", "as", "is", "are", "into", "over", "under", "may", "vary",
    "packaging", "pack", "value", "set", "combo", "boxes", "box", "bottle",
    "bottles", "bags", "bag", "cups", "cup", "can", "cans", "pc", "pcs",
    "oz", "fl", "ml", "l", "g", "kg", "lb", "x", "new", "drink", "beverage",
    "flavor", "flavored", "refreshing", "healthy", "sweet", "creamy", "premium",
    "special", "classic", "original", "natural", "fresh", "instant", "soft",
    "rich", "style", "mixed", "contains", "real", "juice", "water", "soda",
    "carbonated", "non", "fat", "calories", "added", "pack", "packs"
}

BAD_SUBSTRINGS = {
    "cookie", "consent", "privacy", "powered by", "feedback", "contact us",
    "doubleclick", "google", "tiktok analytics", "visitor_info1_live"
}

MARKETING = {
    "trending", "tiktok", "exclusive", "limited", "gift", "value",
    "summer", "selected", "favorite", "pick", "anime", "finds", "combo",
    "seasonal", "yami", "exclusive"
}

PACKAGING = {
    "pack", "bottle", "box", "can", "bag", "cup", "jar", "pouch", "bags",
    "boxes", "cans", "cups", "pcs", "piece", "pieces"
}

WEAK_ADJECTIVES = {
    "fresh", "natural", "premium", "classic", "original", "healthy", "rich", "sweet"
}

GENERIC_SINGLETONS = {
    "tea", "matcha", "oolong", "jasmine", "green", "black", "white",
    "herbal", "barley", "honey", "ginger", "peach", "lemon", "sugar"
}

ALIASES = {
    "mugicha": "barley tea",
    "genmaicha": "brown rice tea",
    "hojicha": "roasted green tea",
    "tieguanyin": "oolong tea",
}

UNITS_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(oz|fl|ml|l|g|kg|lb|bags?|pcs?|pack|packs|cans?|cups?)\b",
    re.IGNORECASE
)
NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")
BAD_CHARS_PATTERN = re.compile(r"[^a-z0-9\s\-+&]")


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(text: str) -> str:
    text = clean_text(text).lower()
    text = UNITS_PATTERN.sub(" ", text)
    text = NUMBER_PATTERN.sub(" ", text)
    text = BAD_CHARS_PATTERN.sub(" ", text)
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


def title_has_anchor(title: str) -> bool:
    return any(anchor in title for anchor in TEA_ANCHORS)


def filtered_tokens_for_title(title: str) -> list[str]:
    toks = tokenize(title)
    out = []

    for tok in toks:
        if tok in STOPWORDS:
            continue
        if tok in MARKETING:
            continue
        if tok in PACKAGING:
            continue
        if tok in REMOVABLE_NOISE_TOKENS:
            continue
        if tok.isdigit():
            continue
        if len(tok) < MIN_WORD_LEN:
            continue
        out.append(tok)

    return out


def ngrams(tokens: list[str], max_n: int = 4):
    for n in range(1, max_n + 1):
        for i in range(len(tokens) - n + 1):
            yield " ".join(tokens[i:i+n])


def apply_aliases(text: str) -> str:
    t = text
    for src, dst in ALIASES.items():
        t = re.sub(rf"\b{re.escape(src)}\b", dst, t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def phrase_has_anchor(term: str) -> bool:
    term = apply_aliases(term)
    return any(anchor in term for anchor in TEA_ANCHORS)


def phrase_has_known_ingredient(term: str) -> bool:
    term = apply_aliases(term)
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
    term = apply_aliases(term)
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

    genericish = {
        "sugar", "free", "low", "calorie", "calories", "healthy",
        "refreshing", "drink", "beverage", "unsweetened"
    }
    if sum(t in genericish for t in tokens) >= len(tokens) - 1:
        return False

    return True


def phrase_is_only_modifier(term: str) -> bool:
    return apply_aliases(term) in MODIFIERS


def phrase_is_bad(term: str) -> bool:
    toks = apply_aliases(term).split()
    if any(tok in MARKETING for tok in toks):
        return True
    if any(tok in PACKAGING for tok in toks):
        return True
    if NUMBER_PATTERN.search(term):
        return True
    return False


def phrase_looks_like_full_title(term: str, title: str) -> bool:
    """
    Reject phrases that are basically long title fragments.
    """
    term_tokens = apply_aliases(term).split()
    title_tokens = filtered_tokens_for_title(title)

    if len(term_tokens) >= 5:
        return True
    if len(term_tokens) >= max(1, len(title_tokens) - 1):
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
            if phrase_looks_like_full_title(term, title):
                continue
            term_to_titles[term].add(title)

    return term_to_titles


def repetition_bonus(match_count: int) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    if match_count >= 50:
        score += 3
        reasons.append(f"strong repetition in tea titles ({match_count})")
    elif match_count >= 20:
        score += 2
        reasons.append(f"moderate repetition in tea titles ({match_count})")
    elif match_count >= 10:
        score += 1
        reasons.append(f"light repetition in tea titles ({match_count})")

    return score, reasons


def is_style_tea_phrase(term: str) -> bool:
    toks = apply_aliases(term).split()
    if "tea" not in toks:
        return False
    if len(toks) < 2:
        return False

    before_tea = toks[:toks.index("tea")]
    if not before_tea:
        return False

    return any(tok in STYLE_WORDS for tok in before_tea)


def is_style_ingredient_tea_phrase(term: str) -> bool:
    toks = apply_aliases(term).split()
    if "tea" not in toks:
        return False
    if len(toks) < 3:
        return False

    before_tea = toks[:toks.index("tea")]
    if not before_tea:
        return False

    has_style = any(tok in STYLE_WORDS for tok in before_tea)
    has_ingredient = any(tok in INGREDIENT_LIKE for tok in before_tea)

    return has_style and has_ingredient


def classify_term_type(term: str) -> str:
    aliased = apply_aliases(term)

    if phrase_has_anchor(aliased):
        if "latte" in aliased or "milk tea" in aliased:
            return "format"
        if "tea" in aliased or "matcha" in aliased or "oolong" in aliased or "herbal" in aliased:
            return "tea_phrase"

    if phrase_has_known_ingredient(aliased) or looks_like_ingredient_phrase(aliased):
        return "ingredient_phrase"

    return "other"


def concept_key(term: str, term_type: str) -> str:
    """
    Collapse variants like:
    - unsweetened barley tea -> barley tea
    - barley tea caffeine free -> barley tea
    - low sugar jasmine tea -> jasmine tea
    - sugar ginger tea -> ginger tea
    - mugicha unsweetened barley tea -> barley tea
    - thai lime tea -> thai lime tea
    - thai tea -> thai tea
    """
    t = apply_aliases(term)

    for phrase in sorted(REMOVABLE_MODIFIER_PHRASES, key=len, reverse=True):
        t = t.replace(phrase, " ")

    toks = [
        tok for tok in t.split()
        if tok not in REMOVABLE_MODIFIER_TOKENS
        and tok not in REMOVABLE_NOISE_TOKENS
        and tok not in WEAK_ADJECTIVES
    ]

    joined = " ".join(toks)

    if "milk tea" in joined:
        before = joined.split("milk tea")[0].strip().split()
        if before:
            return " ".join(before[-2:] + ["milk tea"])
        return "milk tea"

    if "tea latte" in joined:
        before = joined.split("tea latte")[0].strip().split()
        if before:
            return " ".join(before[-2:] + ["tea latte"])
        return "tea latte"

    if "tea" in toks:
        tea_idx = toks.index("tea")
        before = toks[:tea_idx]
        if before:
            core = before[-2:] + ["tea"]
            return " ".join(core)
        return "tea"

    return " ".join(toks[:2]).strip() or apply_aliases(term)


def score_term(term: str, match_count: int):
    score = 0
    reasons = []
    term_type = classify_term_type(term)
    aliased = apply_aliases(term)
    toks = aliased.split()

    if phrase_is_only_modifier(aliased):
        score -= 6
        reasons.append("modifier alone")

    if phrase_is_bad(aliased):
        score -= 6
        reasons.append("marketing/packaging noise")

    if phrase_has_anchor(aliased):
        score += 3
        reasons.append("contains tea anchor")

    if phrase_has_known_ingredient(aliased):
        score += 3
        reasons.append("known ingredient-like concept")
    elif looks_like_ingredient_phrase(aliased):
        score += 2
        reasons.append("unknown but noun-like ingredient phrase")

    if len(toks) == 2:
        score += 2
        reasons.append("compact specific phrase")
    elif len(toks) == 3:
        score += 2
        reasons.append("specific 3-word phrase")
    elif len(toks) == 4:
        score += 1
        reasons.append("longer phrase")

    if is_style_tea_phrase(aliased):
        score += 2
        reasons.append("style-based tea phrase")

    if is_style_ingredient_tea_phrase(aliased):
        score += 2
        reasons.append("style + ingredient + tea phrase")

    if match_count == 1 and len(toks) >= 2 and (
        phrase_has_anchor(aliased) or
        phrase_has_known_ingredient(aliased) or
        looks_like_ingredient_phrase(aliased)
    ):
        score += 2
        reasons.append("rare but specific tea-context concept")

    rep_score, rep_reasons = repetition_bonus(match_count)
    score += rep_score
    reasons.extend(rep_reasons)

    if len(toks) == 1 and aliased in GENERIC_SINGLETONS:
        score -= 3
        reasons.append("overly broad singleton")

    if len(toks) == 1 and match_count >= 10:
        score -= 1
        reasons.append("singleton repetition is less distinctive")

    if any(mod in aliased for mod in MODIFIERS) and len(toks) >= 3 and phrase_has_anchor(aliased):
        score += 1
        reasons.append("modifier attached to tea phrase")

    return score, reasons, term_type


def keep_candidate(term: str, score: int, term_type: str, match_count: int) -> bool:
    aliased = apply_aliases(term)
    toks = aliased.split()

    if phrase_is_only_modifier(aliased):
        return False

    if is_style_tea_phrase(aliased) and score >= 4:
        return True

    if is_style_ingredient_tea_phrase(aliased) and score >= 5:
        return True

    if len(toks) == 1 and aliased not in INGREDIENT_LIKE and aliased not in {"matcha"}:
        return False

    if term_type == "format" and score >= 5:
        return True

    if term_type == "tea_phrase" and score >= 5:
        return True

    if term_type == "ingredient_phrase" and len(toks) >= 2 and score >= 5:
        return True

    if len(toks) == 1 and aliased in INGREDIENT_LIKE and match_count >= 3 and score >= 4:
        return True

    return False


def term_cleanliness(term: str) -> int:
    aliased = apply_aliases(term)
    toks = aliased.split()
    penalty = 0

    for tok in toks:
        if tok in REMOVABLE_MODIFIER_TOKENS:
            penalty += 2
        if tok in REMOVABLE_NOISE_TOKENS:
            penalty += 2
        if tok in WEAK_ADJECTIVES:
            penalty += 1
        if tok in MARKETING:
            penalty += 2
        if tok in PACKAGING:
            penalty += 2

    if "tea" in toks and toks.count("tea") > 1:
        penalty += 3
    if "barley" in toks and toks.count("barley") > 1:
        penalty += 2

    penalty += max(0, len(toks) - 3)
    return -penalty


def choose_better(existing: dict, new: dict) -> dict:
    key_existing = (
        existing["score"],
        term_cleanliness(existing["term"]),
        -abs(len(apply_aliases(existing["term"]).split()) - 3),
        existing["title_match_count"],
    )
    key_new = (
        new["score"],
        term_cleanliness(new["term"]),
        -abs(len(apply_aliases(new["term"]).split()) - 3),
        new["title_match_count"],
    )

    return new if key_new > key_existing else existing


def family_dedupe(candidates: list[dict]) -> list[dict]:
    best_by_family = {}

    for cand in candidates:
        key = concept_key(cand["term"], cand["term_type"])
        cand["concept_key"] = key

        if key not in best_by_family:
            best_by_family[key] = cand
        else:
            best_by_family[key] = choose_better(best_by_family[key], cand)

    out = list(best_by_family.values())
    out.sort(key=lambda x: (-x["score"], x["title_match_count"], -len(apply_aliases(x["term"]).split()), x["term"]))
    return out


def balanced_top_k(candidates: list[dict], k: int = TOP_K) -> list[dict]:
    buckets = {
        "format": [],
        "tea_phrase": [],
        "ingredient_phrase": [],
        "other": [],
    }

    for c in candidates:
        buckets[c["term_type"]].append(c)

    for key in buckets:
        buckets[key].sort(key=lambda x: (-x["score"], x["title_match_count"], -len(apply_aliases(x["term"]).split()), x["term"]))

    targets = {
        "format": 20,
        "tea_phrase": 60,
        "ingredient_phrase": 70,
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

    leftovers.sort(key=lambda x: (-x["score"], x["title_match_count"], -len(apply_aliases(x["term"]).split()), x["term"]))

    for c in leftovers:
        if len(final) >= k:
            break
        final.append(c)
        used.add(c["term"])

    final.sort(key=lambda x: (-x["score"], x["title_match_count"], -len(apply_aliases(x["term"]).split()), x["term"]))
    return final[:k]


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

        cleaned_term = concept_key(term, term_type)

        payload = {
            "term": cleaned_term,
            "original_term": term,
            "term_type": term_type,
            "concept_key": concept_key(term, term_type),
            "title_match_count": match_count,
            "score": score,
            "reasons": reasons,
            "example_titles": sorted(list(matched_titles))[:5],
        }
        all_candidates.append(payload)

    all_candidates.sort(key=lambda x: (-x["score"], x["title_match_count"], -len(apply_aliases(x["term"]).split()), x["term"]))
    deduped = family_dedupe(all_candidates)
    topk = balanced_top_k(deduped, TOP_K)

    with open(ALL_FILE, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)

    with open(TOP_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(topk, f, indent=2, ensure_ascii=False)

    print("Done.")
    print(f"Titles used: {len(titles)}")
    print(f"All kept candidates: {len(deduped)}")
    print(f"Top {TOP_K} saved: {len(topk)}")
    print(f"Saved: {ALL_FILE}")
    print(f"Saved: {TOP_OUTPUT_FILE}")
    print("\nTop 30:")
    for row in topk[:30]:
        print(
            f"- {row['term']} | type={row['term_type']} | "
            f"family={row['concept_key']} | titles={row['title_match_count']} | score={row['score']}"
        )


if __name__ == "__main__":
    main()
