# ── tariff_filter.py ──────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1: COUNTRY RISK TIERS
# Based on: USTR tariff schedules, Section 301/232 actions, OFAC sanctions,
# CBP forced labor flags (UFLPA), and active trade restriction orders (2025)
# ─────────────────────────────────────────────────────────────────────────────

COUNTRY_RISK = {

    # ── CRITICAL (Tier 4) — Sanctions / near-total import blocks ─────────────
    # Do not source. Likely illegal or requires OFAC license.
    "Iran":             {"tier": 4, "reason": "OFAC comprehensive sanctions — imports prohibited"},
    "North Korea":      {"tier": 4, "reason": "OFAC comprehensive sanctions — imports prohibited"},
    "Cuba":             {"tier": 4, "reason": "OFAC embargo — most imports prohibited"},
    "Syria":            {"tier": 4, "reason": "OFAC sanctions — imports largely prohibited"},
    "Russia":           {"tier": 4, "reason": "Section 232 + broad trade restrictions post-2022"},
    "Belarus":          {"tier": 4, "reason": "OFAC sanctions aligned with Russia restrictions"},
    "Myanmar":          {"tier": 4, "reason": "OFAC sectoral sanctions, forced labor flags (UFLPA)"},

    # ── HIGH RISK (Tier 3) — Active tariffs + forced labor + political risk ───
    # Heavy Section 301 tariffs (25–145%), UFLPA enforcement, or active CBP blocks
    "China":            {"tier": 3, "reason": "Section 301 tariffs 25–145%, UFLPA forced labor risk, Xinjiang sourcing flags"},
    "Hong Kong":        {"tier": 3, "reason": "Lost preferential trade status 2020, treated as China for tariff purposes"},
    "Venezuela":        {"tier": 3, "reason": "OFAC sectoral sanctions, politically elevated risk"},
    "Nicaragua":        {"tier": 3, "reason": "CAFTA benefits suspended, elevated sanctions risk"},

    # ── ELEVATED RISK (Tier 2) — Targeted tariffs or specific product bans ───
    # Sourceable but requires due diligence. Specific product categories flagged.
    "India":            {"tier": 2, "reason": "GSP benefits lapsed, Section 232 steel/aluminum tariffs, MRL violations on spices (FDA import alerts)"},
    "Vietnam":          {"tier": 2, "reason": "Tariff increases under review, transshipment scrutiny for Chinese-origin goods"},
    "Cambodia":         {"tier": 2, "reason": "EBA benefits partially revoked by EU; US scrutiny increasing, labor concerns"},
    "Bangladesh":       {"tier": 2, "reason": "Labor concerns, GSP eligibility under review"},
    "Pakistan":         {"tier": 2, "reason": "Periodic FDA import alerts on food products, elevated inspection rates"},
    "Turkey":           {"tier": 2, "reason": "Section 232 steel tariffs, periodic agricultural trade disputes"},
    "Indonesia":        {"tier": 2, "reason": "Palm oil labor/deforestation restrictions, some GSP benefits lapsed"},
    "Malaysia":         {"tier": 2, "reason": "UFLPA forced labor flags on glove/electronics sector; food generally lower risk"},
    "Thailand":         {"tier": 2, "reason": "GSP benefits suspended on some categories, shrimp/seafood labor flags"},
    "Mexico":           {"tier": 2, "reason": "Section 232 steel/aluminum tariffs, periodic agricultural disputes, USMCA rules of origin scrutiny"},
    "Ecuador":          {"tier": 2, "reason": "Active trade agreement negotiations, banana/cocoa export restrictions"},
    "Ethiopia":         {"tier": 2, "reason": "AGOA benefits suspended 2022 due to human rights concerns"},
    "Uganda":           {"tier": 2, "reason": "AGOA benefits suspended 2023"},
    "Mali":             {"tier": 2, "reason": "AGOA benefits suspended, political instability"},
    "Guinea":           {"tier": 2, "reason": "AGOA benefits suspended 2022"},
    "Burkina Faso":     {"tier": 2, "reason": "AGOA benefits suspended, coup government"},
    "Central African Republic": {"tier": 2, "reason": "Conflict zone, AGOA suspended"},

    # ── WATCH LIST (Tier 1) — Monitor but generally okay ─────────────────────
    # No active major restrictions but geopolitical or compliance risks worth noting
    "Brazil":           {"tier": 1, "reason": "Periodic agricultural import disputes, deforestation trade pressure"},
    "Philippines":      {"tier": 1, "reason": "Some FDA import alerts on seafood; general trade stable"},
    "Sri Lanka":        {"tier": 1, "reason": "Post-economic crisis supply reliability risk"},
    "Nepal":            {"tier": 1, "reason": "Supply chain reliability, landlocked logistics risk"},
    "Bolivia":          {"tier": 1, "reason": "Nationalization risk, periodic export restrictions on quinoa/chia"},
    "Argentina":        {"tier": 1, "reason": "Currency controls, periodic export bans on agricultural products"},
    "Peru":             {"tier": 1, "reason": "Political instability, some agricultural export disruptions"},
    "Colombia":         {"tier": 1, "reason": "Drug precursor controls affect some botanical exports"},
    "Ghana":            {"tier": 1, "reason": "AGOA eligible but cocoa export policy shifts"},
    "Kenya":            {"tier": 1, "reason": "AGOA eligible, generally low risk; some tea MRL watch"},
    "Tanzania":         {"tier": 1, "reason": "AGOA eligible, export policy unpredictability on cloves/vanilla"},
    "Egypt":            {"tier": 1, "reason": "Currency devaluation, some food safety compliance gaps"},
    "Morocco":          {"tier": 1, "reason": "US FTA in place, generally low risk"},
    "Jordan":           {"tier": 1, "reason": "US FTA in place, generally low risk"},

    # ── LOW RISK (Tier 0) — Stable trade relationships ────────────────────────
    "Japan":            {"tier": 0, "reason": "US-Japan Trade Agreement, strong regulatory alignment"},
    "South Korea":      {"tier": 0, "reason": "KORUS FTA, strong regulatory alignment"},
    "Taiwan":           {"tier": 0, "reason": "Strong US trade relationship, high food safety standards"},
    "Singapore":        {"tier": 0, "reason": "US FTA, low tariff, strong compliance"},
    "Australia":        {"tier": 0, "reason": "AUSFTA FTA, zero tariff most goods"},
    "New Zealand":      {"tier": 0, "reason": "Strong trade relationship, high food safety standards"},
    "Canada":           {"tier": 0, "reason": "USMCA, generally zero tariff for compliant goods"},
    "Chile":            {"tier": 0, "reason": "US-Chile FTA, low agricultural tariffs"},
    "Costa Rica":       {"tier": 0, "reason": "CAFTA-DR, low tariff, stable"},
    "Germany":          {"tier": 0, "reason": "US-EU trade generally stable, high regulatory standards"},
    "France":           {"tier": 0, "reason": "US-EU trade generally stable"},
    "Italy":            {"tier": 0, "reason": "US-EU trade generally stable"},
    "Netherlands":      {"tier": 0, "reason": "US-EU trade generally stable, major re-export hub"},
    "Spain":            {"tier": 0, "reason": "US-EU trade generally stable"},
    "United Kingdom":   {"tier": 0, "reason": "Post-Brexit trade stable, active FTA negotiations"},
    "Israel":           {"tier": 0, "reason": "US-Israel FTA, zero tariff most goods"},
}

TIER_LABELS = {
    0: "Low risk",
    1: "Watch list",
    2: "Elevated risk",
    3: "High risk",
    4: "Critical — do not source",
}

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2: PRODUCT + COUNTRY SPECIFIC FLAGS
# Even if a country is Tier 1/2, certain product categories carry extra risk
# ─────────────────────────────────────────────────────────────────────────────

PRODUCT_COUNTRY_FLAGS = {
    # (product_category, country): specific_warning
    ("tea",         "China"):   "FDA import alert 99-33: elevated pesticide/MRL violations on Chinese tea",
    ("tea",         "India"):   "FDA import alert on some Darjeeling lots; verify MRL compliance",
    ("tea",         "Kenya"):   "Generally clean but monitor EU MRL rulings which often precede US action",
    ("spices",      "India"):   "FDA import alert 99-33: high rejection rate for filth, Salmonella, MRL issues",
    ("spices",      "Vietnam"): "Elevated inspection rate for pesticide residues",
    ("spices",      "China"):   "High rejection rate, Section 301 tariffs apply",
    ("ginger",      "China"):   "Section 301 tariffs apply; CBP forced labor scrutiny",
    ("ginger",      "India"):   "FDA MRL alerts; verify aflatoxin testing",
    ("ginseng",     "China"):   "Section 301 tariffs apply; verify non-Xinjiang origin",
    ("supplements", "China"):   "FTC/FDA scrutiny on label claims; Section 301 tariffs; UFLPA risk",
    ("honey",       "China"):   "CBP antidumping duties; adulteration/transshipment history",
    ("honey",       "Vietnam"): "CBP transshipment scrutiny — may be Chinese-origin honey re-routed",
    ("honey",       "India"):   "Adulteration concerns, elevated FDA sampling rate"),
    ("garlic",      "China"):   "Antidumping duties (CVD) apply; high rejection rate"),
    ("mushrooms",   "China"):   "Section 301 tariffs; elevated FDA inspection rate"),
    ("seafood",     "China"):   "UFLPA forced labor flags; elevated FDA detention rate"),
    ("seafood",     "India"):   "Antibiotic residue alerts (nitrofurans); elevated FDA rejection rate"),
    ("seafood",     "Vietnam"): "Antidumping duties on shrimp/catfish; antibiotic residue history"),
    ("seafood",     "Thailand"): "Labor/forced labor history; antibiotic residue flags"),
    ("palm oil",    "Malaysia"): "CBP Withhold Release Order (WRO) on some Malaysian palm producers"),
    ("cocoa",       "Ivory Coast"): "Child labor compliance risk; some EU import restrictions"),
    ("rice",        "China"):   "Section 301 tariffs; pesticide residue alerts"),
    ("noodles",     "China"):   "Section 301 tariffs apply; verify origin labeling"),
    ("candy",       "China"):   "Section 301 tariffs; some FDA colorant compliance issues"),
    ("personal care","China"):  "Section 301 tariffs; FDA OTC drug compliance if medicated"),
}

# ─────────────────────────────────────────────────────────────────────────────
# FILTER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def flag_trade_risk(product_name: str, country_of_origin: str,
                    product_category: str = None) -> dict:
    """
    Returns a risk assessment dict for a given product + origin country.

    Args:
        product_name:      e.g. "Chrysanthemum Tea Bags"
        country_of_origin: e.g. "China"
        product_category:  e.g. "tea" — optional but improves specificity

    Returns: {
        "product":        str,
        "country":        str,
        "tier":           int (0–4),
        "tier_label":     str,
        "country_reason": str,
        "product_flags":  list[str],
        "recommended_action": str,
        "block":          bool   ← True if tier >= 3 (should not source)
    }
    """
   country_data = COUNTRY_RISK.get(country_of_origin, {
    "tier": 0,
    "reason": "Country not in database — assumed US origin, standard due diligence applies"
})
    tier = country_data["tier"]
    country_reason = country_data["reason"]

    # Check product-specific flags
    product_flags = []
    if product_category:
        key = (product_category.lower(), country_of_origin)
        if key in PRODUCT_COUNTRY_FLAGS:
            product_flags.append(PRODUCT_COUNTRY_FLAGS[key])

    # Determine action
    if tier == 4:
        action = "DO NOT SOURCE — sanctions/prohibition apply. Consult legal."
    elif tier == 3:
        action = "HIGH CAUTION — major tariff exposure and/or forced labor risk. Requires legal + compliance review before proceeding."
    elif tier == 2:
        action = "ELEVATED — conduct supplier audit, verify origin documentation, check FDA import alerts, calculate landed cost with tariffs."
    elif tier == 1:
        action = "MONITOR — generally sourceable but watch for policy changes. Request COO documentation."
    else:
        action = "PROCEED — low risk. Standard due diligence applies."

    return {
        "product":            product_name,
        "country":            country_of_origin,
        "tier":               tier,
        "tier_label":         TIER_LABELS[tier],
        "country_reason":     country_reason,
        "product_flags":      product_flags,
        "recommended_action": action,
        "block":              tier >= 3,
    }


def filter_product_list(products: list[dict]) -> list[dict]:
    """
    Run the trade risk filter across a list of products.

    Each product dict must have:
      - 'name': str
      - 'country_of_origin': str
      - 'category': str (optional but recommended)

    Returns the same list with 'trade_risk' key added to each.
    """
    for p in products:
        p['trade_risk'] = flag_trade_risk(
            product_name=p.get('name', ''),
            country_of_origin=p.get('country_of_origin', 'Unknown'),
            product_category=p.get('category', None),
        )
    return sorted(products, key=lambda x: x['trade_risk']['tier'], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLE USAGE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_products = [
        {"name": "Chrysanthemum Tea Bags",      "country_of_origin": "China",       "category": "tea"},
        {"name": "Mala Hotpot Noodles",         "country_of_origin": "China",       "category": "noodles"},
        {"name": "Ginseng Extract Capsules",    "country_of_origin": "South Korea", "category": "supplements"},
        {"name": "Organic Ginger Chews",        "country_of_origin": "India",       "category": "ginger"},
        {"name": "Matcha Green Tea Powder",     "country_of_origin": "Japan",       "category": "tea"},
        {"name": "Salted Egg Fish Skin Crisps", "country_of_origin": "Singapore",   "category": "snacks"},
        {"name": "Latiao Spicy Gluten Snack",   "country_of_origin": "China",       "category": "candy"},
        {"name": "Tremella Mushroom Powder",    "country_of_origin": "China",       "category": "mushrooms"},
        {"name": "Raw Honey Sticks",            "country_of_origin": "Vietnam",     "category": "honey"},
        {"name": "Ashwagandha Root Powder",     "country_of_origin": "India",       "category": "supplements"},
    ]

    results = filter_product_list(test_products)

    for r in results:
        risk = r['trade_risk']
        print(f"\n{'='*60}")
        print(f"PRODUCT : {r['name']}")
        print(f"ORIGIN  : {r['country_of_origin']}")
        print(f"RISK    : [{risk['tier']}] {risk['tier_label']}")
        print(f"REASON  : {risk['country_reason']}")
        if risk['product_flags']:
            print(f"FLAGS   : {'; '.join(risk['product_flags'])}")
        print(f"ACTION  : {risk['recommended_action']}")
        if risk['block']:
            print(f"*** BLOCKED FROM PIPELINE ***")
