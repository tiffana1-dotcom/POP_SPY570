import time
import requests
import pandas as pd
from pytrends.request import TrendReq
from tariff_filter import flag_trade_risk

RAINFOREST_KEY = "your_rainforest_api_key"
WALMART_KEY    = "your_walmart_consumer_id"

# ── 1. GOOGLE TRENDS ──────────────────────────────────────────────
def get_trend_scores(products: list[str]) -> dict:
    pytrends = TrendReq(hl='en-US', tz=360)
    scores = {}
    for i in range(0, len(products), 5):
        batch = products[i:i+5]
        pytrends.build_payload(batch, timeframe='today 12-m', geo='US')
        df = pytrends.interest_over_time()
        if not df.empty:
            for term in batch:
                if term in df.columns:
                    scores[term] = int(df[term].mean())
        time.sleep(1)
    return scores

# ── 2. REDDIT SIGNAL ──────────────────────────────────────────────
SUBREDDITS = ['asianeats', 'tea', 'casualuk', 'EatCheapAndHealthy', 'xxkpop']

def get_reddit_signal(product_name: str) -> dict:
    headers = {'User-Agent': 'arbitrage-engine/0.1'}
    mention_count = 0
    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/search.json"
        params = {'q': product_name, 'limit': 25, 'sort': 'new', 'restrict_sr': 1}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=5)
            mention_count += len(r.json()['data']['children'])
        except:
            pass
        time.sleep(0.5)
    return {
        'mentions': mention_count,
        'signal': 'high' if mention_count > 10 else 'med' if mention_count > 3 else 'low'
    }

# ── 3. WALMART GAP CHECK ──────────────────────────────────────────
def check_walmart_gap(product_name: str) -> dict:
    url = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2/search"
    headers = {'WM_SEC.KEY_VERSION': '1', 'WM_CONSUMER.ID': WALMART_KEY}
    params = {'query': product_name, 'numItems': 5}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        items = r.json().get('items', [])
        count = len(items)
        return {
            'walmart_count': count,
            'gap': 'high' if count == 0 else 'med' if count < 3 else 'low'
        }
    except:
        return {'walmart_count': -1, 'gap': 'unknown'}

# ── 4. RAINFOREST API (Amazon) ────────────────────────────────────
def search_amazon_asin(query: str) -> str | None:
    """Step 4a: find the top ASIN for a product query"""
    params = {
        'api_key': RAINFOREST_KEY,
        'type': 'search',
        'amazon_domain': 'amazon.com',
        'search_term': query,
    }
    r = requests.get('https://api.rainforestapi.com/request', params=params)
    results = r.json().get('search_results', [])
    # skip sponsored results — they skew competition data
    organic = [x for x in results if not x.get('is_sponsored')]
    return organic[0].get('asin') if organic else None

def get_amazon_signals(asin: str) -> dict:
    """Step 4b: pull competition + demand data for that ASIN"""
    params = {
        'api_key': RAINFOREST_KEY,
        'type': 'product',
        'amazon_domain': 'amazon.com',
        'asin': asin,
    }
    r = requests.get('https://api.rainforestapi.com/request', params=params)
    p = r.json().get('product', {})

    bsr = None
    bsr_list = p.get('bestsellers_rank', [])
    if bsr_list:
        # use the most specific subcategory rank
        bsr = min(bsr_list, key=lambda x: x.get('rank', 9999999)).get('rank')

    seller_count = p.get('marketplace_sellers_count', 99)
    rating       = p.get('rating', 0)
    review_count = p.get('ratings_total', 0)
    price        = p.get('buybox_winner', {}).get('price', {}).get('value', 0)
    in_stock     = p.get('buybox_winner', {}).get('availability', {}).get('type') == 'in_stock'

    # Score the amazon signal 0–100:
    # Low sellers = good, high BSR rank (low number) = good, solid reviews = validated
    seller_score = max(0, 100 - (seller_count * 8))   # 0 sellers=100, 12+ sellers=0
    bsr_score    = max(0, 100 - (bsr / 500)) if bsr else 30  # BSR 1=100, 50000+=0
    review_score = min(rating * 15, 75) if review_count > 20 else 10  # proven but not saturated

    amazon_composite = round((seller_score * 0.5) + (bsr_score * 0.3) + (review_score * 0.2))

    return {
        'asin':             asin,
        'seller_count':     seller_count,
        'bsr':              bsr,
        'rating':           rating,
        'review_count':     review_count,
        'price':            price,
        'in_stock':         in_stock,
        'amazon_composite': amazon_composite,
    }

# ── 5. ARBITRAGE SCORE ────────────────────────────────────────────
def arbitrage_score(trend, reddit_signal, walmart_gap, amazon_composite) -> int:
    trend_pts   = min(trend, 100) * 0.35

    reddit_pts  = {'high': 100, 'med': 50, 'low': 10}.get(reddit_signal, 0) * 0.20

    walmart_pts = {'high': 100, 'med': 50, 'low': 10,
                   'unknown': 30}.get(walmart_gap, 0) * 0.15

    amazon_pts  = amazon_composite * 0.30

    return round(trend_pts + reddit_pts + walmart_pts + amazon_pts)

# ── 6. MAIN PIPELINE ──────────────────────────────────────────────
PRODUCTS = {
    "mala hotpot noodles":          "mala hotpot instant noodles",
    "WeiLong latiao snack":         "WeiLong latiao spicy gluten snack",
    "brown sugar ginger tea":       "brown sugar ginger tea instant granules",
    "tremella snow fungus powder":  "tremella snow fungus powder supplement",
    "salted egg fish skin crisps":  "salted egg fish skin chips Irvins",
    "collagen jelly stick drink":   "collagen jelly stick drink beauty",
    "sesame paste cold noodles":    "sesame paste dry noodles instant",
    "centella asiatica toner":      "centella asiatica toner Korean skincare",
    "chrysanthemum wolfberry tea":  "chrysanthemum wolfberry tea bags",
    "astragalus root slices":       "astragalus root slices huang qi",
}
# display name → amazon search query (keeps your 100 calls: 10 searches + 10 products = 20 total)

def run_pipeline():
    print("Fetching Google Trends...")
    trends = get_trend_scores(list(PRODUCTS.keys()))

    results = []
    for display_name, amazon_query in PRODUCTS.items():
        print(f"\nAnalyzing: {display_name}")

        trend   = trends.get(display_name, 0)
        reddit  = get_reddit_signal(display_name)
        walmart = check_walmart_gap(display_name)

        # Amazon: 2 API calls per product (search + product detail)
        asin = search_amazon_asin(amazon_query)
        if asin:
            amazon = get_amazon_signals(asin)
            print(f"  ASIN: {asin} | Sellers: {amazon['seller_count']} | BSR: {amazon['bsr']}")
        else:
            amazon = {'asin': None, 'seller_count': 99, 'bsr': None,
                      'rating': 0, 'review_count': 0, 'price': 0,
                      'in_stock': False, 'amazon_composite': 70}

     # --- 1. Base Score ---
        score = arbitrage_score(trend, reddit['signal'], walmart['gap'], amazon['amazon_composite'])

        # --- 2. Check the trade risk ---
        trade_risk = flag_trade_risk(
            product_name=display_name,
            country_of_origin='China', # Default for the demo
            product_category=None      
        )

        # --- 3. Apply the China Override ---
        if trade_risk['tier'] == 3:
            trade_risk['block'] = False  

        # --- 4. Apply the Business Penalties ---
        if trade_risk['tier'] == 4:
            score = 0  
        elif trade_risk['tier'] == 3:
            score = round(score * 0.80)  # 20% Tariff Penalty
        elif trade_risk['tier'] == 2:
            score = round(score * 0.85)  # 15% Inspection Penalty

        # --- 5. Save everything (INCLUDING THE RISK LABELS!) ---
        results.append({
            'product':          display_name,
            'arbitrage_score':  score,
            'trend_score':      trend,
            'reddit_signal':    reddit['signal'],
            'reddit_mentions':  reddit['mentions'],
            'walmart_gap':      walmart['gap'],
            'amazon_sellers':   amazon['seller_count'],
            'amazon_bsr':       amazon['bsr'],
            'amazon_rating':    amazon['rating'],
            'amazon_reviews':   amazon['review_count'],
            'price_usd':        amazon['price'],
            'asin':             amazon['asin'],
            'trade_tier':       trade_risk['tier'],          # <-- THIS SAVES THE DATA
            'trade_label':      trade_risk['tier_label'],    # <-- THIS SAVES THE DATA
            'trade_flags':      trade_risk['product_flags']  # <-- THIS SAVES THE DATA
        })
        time.sleep(1)

    df = pd.DataFrame(results).sort_values('arbitrage_score', ascending=False)
    df.to_csv('arbitrage_results.csv', index=False)
    print("\n── FINAL RANKINGS ──")
    print(df[['product', 'arbitrage_score', 'amazon_sellers', 'amazon_bsr', 'walmart_gap']].to_string(index=False))
    return df

if __name__ == "__main__":
    run_pipeline()
