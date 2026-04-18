# product_development.py
# Classifies trending products as "Distribute Existing" or "Develop New PoP Product"
# Maps trending ingredients to PoP's ginger/ginseng/Tiger Balm lines

POP_INGREDIENT_MAP = {
    # GINGER-compatible trends
    "kombucha":         {"base": "ginger", "concept": "Ginger Kombucha Chew", "format": "chew / soft candy", "rationale": "Kombucha's probiotic positioning aligns with ginger's digestive benefits. Extends ginger chew line.", "pop_line": "Ginger Chews"},
    "probiotic":        {"base": "ginger", "concept": "Probiotic Ginger Digestive Chew", "format": "chew / soft candy", "rationale": "Probiotics + ginger is a natural digestive health pairing. Extends existing ginger chew SKU.", "pop_line": "Ginger Chews"},
    "turmeric":         {"base": "ginger", "concept": "Ginger-Turmeric Anti-Inflammatory Tea", "format": "tea bag / instant powder", "rationale": "Ginger and turmeric are both anti-inflammatory. High search overlap. Natural line extension.", "pop_line": "Herbal Teas"},
    "collagen":         {"base": "ginger", "concept": "Ginger Collagen Beauty Tea", "format": "instant tea sachet", "rationale": "Beauty-from-within trend. Ginger's antioxidant profile complements collagen.", "pop_line": "Herbal Teas"},
    "prebiotic":        {"base": "ginger", "concept": "Prebiotic Ginger Gut Health Chew", "format": "chew / soft candy", "rationale": "Prebiotic fiber + ginger targets the growing gut health category.", "pop_line": "Ginger Chews"},
    "electrolyte":      {"base": "ginger", "concept": "Ginger Electrolyte Hydration Stick", "format": "powder stick pack", "rationale": "Sports/recovery trend. Ginger's anti-nausea properties appeal to athletes.", "pop_line": "Functional Beverages"},
    "matcha":           {"base": "ginger", "concept": "Ginger Matcha Energy Tea", "format": "tea bag / latte sachet", "rationale": "Matcha + ginger is an established cafe trend moving into retail.", "pop_line": "Herbal Teas"},
    "mango":            {"base": "ginger", "concept": "Mango Ginger Chew", "format": "chew / soft candy", "rationale": "Tropical flavor extensions are proven in the chew category. Low R&D lift.", "pop_line": "Ginger Chews"},
    "lemon":            {"base": "ginger", "concept": "Lemon Ginger Honey Tea Sachet", "format": "instant tea sachet", "rationale": "Lemon-ginger is the #1 searched herbal tea combination. Immune positioning.", "pop_line": "Herbal Teas"},
    "honey":            {"base": "ginger", "concept": "Ginger Honey Throat Soothing Chew", "format": "chew / lozenge", "rationale": "Honey-ginger is a classic remedy pairing for throat/cold care.", "pop_line": "Ginger Chews"},
    "mushroom":         {"base": "ginger", "concept": "Ginger-Reishi Adaptogen Wellness Tea", "format": "tea bag", "rationale": "Functional mushrooms are the fastest growing wellness ingredient. Ginger grounds the flavor.", "pop_line": "Herbal Teas"},
    "cacao":            {"base": "ginger", "concept": "Dark Chocolate Ginger Chew", "format": "chew / confection", "rationale": "Chocolate-ginger is a proven premium confection. Strong gifting SKU.", "pop_line": "Ginger Chews"},
    "spicy":            {"base": "ginger", "concept": "Extra Spicy Ginger Fire Chew", "format": "chew / soft candy", "rationale": "Heat/spice food trend driven by Gen Z. Intensity variant on existing chew line.", "pop_line": "Ginger Chews"},
    "immune":           {"base": "ginger", "concept": "Ginger-Elderberry Immune Defense Tea", "format": "tea bag / instant sachet", "rationale": "Immune health is the #1 functional claim category post-pandemic.", "pop_line": "Herbal Teas"},
    "sleep":            {"base": "ginger", "concept": "Ginger Chamomile Calm & Sleep Tea", "format": "tea bag", "rationale": "Sleep wellness is top-5 health concern for US adults.", "pop_line": "Herbal Teas"},

    # GINSENG-compatible trends
    "adaptogen":        {"base": "ginseng", "concept": "Ginseng Multi-Adaptogen Energy Capsule", "format": "capsule / softgel", "rationale": "Ginseng IS an adaptogen — PoP can lead this conversation, not follow it.", "pop_line": "Ginseng Supplements"},
    "nootropic":        {"base": "ginseng", "concept": "Ginseng Cognitive Focus Shot", "format": "liquid shot (2oz)", "rationale": "Nootropic/brain health trend driven by remote work culture. High-margin format.", "pop_line": "Ginseng Supplements"},
    "energy":           {"base": "ginseng", "concept": "Ginseng Natural Energy Shot (No Caffeine)", "format": "liquid shot (2oz)", "rationale": "Clean energy without caffeine is a white space. Differentiates from 5-Hour Energy.", "pop_line": "Ginseng Supplements"},
    "testosterone":     {"base": "ginseng", "concept": "Red Ginseng Men's Vitality Supplement", "format": "capsule / tea", "rationale": "Men's health supplement category growing 18% YoY. Red ginseng has established traditional use.", "pop_line": "Ginseng Supplements"},
    "stress":           {"base": "ginseng", "concept": "Ginseng-Ashwagandha Stress Balance Tea", "format": "tea bag / capsule", "rationale": "Stress/cortisol management is top wellness concern. Strong search volume.", "pop_line": "Ginseng Supplements"},
    "longevity":        {"base": "ginseng", "concept": "Aged Red Ginseng Longevity Extract", "format": "liquid extract / tincture", "rationale": "Longevity trend driven by aging Boomers. Premium aged ginseng commands 3-5x margin.", "pop_line": "Ginseng Supplements"},
    "keto":             {"base": "ginseng", "concept": "Keto Ginseng MCT Energy Capsule", "format": "capsule", "rationale": "Keto community is large and brand-loyal. Ginseng + MCT for metabolic energy is novel.", "pop_line": "Ginseng Supplements"},
    "functional beverage": {"base": "ginseng", "concept": "Sparkling Ginseng Wellness Water", "format": "RTD beverage", "rationale": "Functional RTD is the fastest growing beverage subcategory.", "pop_line": "Functional Beverages"},
    "beauty":           {"base": "ginseng", "concept": "Ginseng Brightening Beauty Supplement", "format": "capsule / beauty tea", "rationale": "Ingestible beauty is a $4B and growing category. K-beauty halo effect.", "pop_line": "Ginseng Supplements"},
    "weight loss":      {"base": "ginseng", "concept": "Ginseng Metabolism Support Tea", "format": "tea bag / sachet", "rationale": "Weight management is the largest supplement category.", "pop_line": "Herbal Teas"},

    # TIGER BALM-compatible trends
    "pain relief":      {"base": "tiger balm", "concept": "Tiger Balm Sport Recovery Patch", "format": "topical patch", "rationale": "Topical pain patches growing 22% YoY. Modernizes Tiger Balm for athletic recovery.", "pop_line": "Tiger Balm"},
    "cbd":              {"base": "tiger balm", "concept": "Tiger Balm Botanical Relief Cream (CBD-free)", "format": "topical cream", "rationale": "CBD topicals created appetite for botanical pain relief. PoP captures this without CBD complexity.", "pop_line": "Tiger Balm"},
    "cooling":          {"base": "tiger balm", "concept": "Tiger Balm Ice Sport Cooling Spray", "format": "spray", "rationale": "Cooling sprays are the fastest growing sports recovery format.", "pop_line": "Tiger Balm"},
}


def classify_opportunity(product: dict, amazon_data: dict) -> dict:
    name        = product.get('name', '').lower()
    category    = product.get('category', '').lower()
    trend_score = product.get('trend_score', 0)

    seller_count = amazon_data.get('seller_count', 99)
    bsr          = amazon_data.get('bsr') or 999999
    review_count = amazon_data.get('review_count', 0)

    pop_match = None
    matched_keyword = None
    for keyword, concept_data in POP_INGREDIENT_MAP.items():
        if keyword in name or keyword in category:
            pop_match = concept_data
            matched_keyword = keyword
            break

    saturation = _score_saturation(seller_count, bsr, review_count)

    if saturation == "saturated":
        flag = "MONITOR"
        action = "Market is well-established. Monitor for price or niche variant opportunity."
        pop_concept = None

    elif saturation == "open" and pop_match:
        flag = "DEVELOP NEW POP PRODUCT"
        action = (
            f"Trending ingredient with limited shelf competition. "
            f"Recommend developing: '{pop_match['concept']}' "
            f"({pop_match['format']}) extending PoP's {pop_match['pop_line']} line. "
            f"{pop_match['rationale']}"
        )
        pop_concept = pop_match

    elif saturation == "moderate" and pop_match:
        flag = "DEVELOP NEW POP PRODUCT"
        action = (
            f"Early movers exist but no dominant brand yet. "
            f"PoP can differentiate via '{pop_match['concept']}'. "
            f"{pop_match['rationale']}"
        )
        pop_concept = pop_match

    elif saturation in ("open", "moderate") and not pop_match:
        flag = "DISTRIBUTE EXISTING PRODUCT"
        action = (
            f"Proven demand with limited mainstream distribution. "
            f"Source an existing manufacturer and distribute through PoP's retail network. "
            f"Evaluate for white-label potential."
        )
        pop_concept = None

    else:
        flag = "MONITOR"
        action = "Insufficient signal strength. Re-evaluate in 60 days."
        pop_concept = None

    return {
        "opportunity_flag": flag,
        "action":           action,
        "saturation":       saturation,
        "pop_concept":      pop_concept,
        "matched_keyword":  matched_keyword,
        "margin_tier":      _estimate_margin(amazon_data.get('price', 0), seller_count, category),
        "priority":         _priority_score(flag, trend_score, saturation),
    }


def _score_saturation(seller_count: int, bsr: int, review_count: int) -> str:
    if seller_count > 15 or review_count > 5000:
        return "saturated"
    elif seller_count > 4 or review_count > 500:
        return "moderate"
    else:
        return "open"


def _estimate_margin(price: float, seller_count: int, category: str) -> str:
    high_margin_cats = {"supplements", "beauty", "personal care", "ginseng"}
    if price > 25 and seller_count < 5:
        return "HIGH (>40%)"
    elif price > 15 or category in high_margin_cats:
        return "MEDIUM (20-40%)"
    else:
        return "LOW (<20%)"


def _priority_score(flag: str, trend_score: int, saturation: str) -> int:
    base = {"DEVELOP NEW POP PRODUCT": 100, "DISTRIBUTE EXISTING PRODUCT": 60, "MONITOR": 20}.get(flag, 0)
    trend_bonus = trend_score * 0.3
    saturation_bonus = {"open": 20, "moderate": 10, "saturated": 0}.get(saturation, 0)
    return round(base + trend_bonus + saturation_bonus)
