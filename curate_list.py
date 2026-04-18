import json

INPUT_FILE = "tea_trend_signals_clean_top150.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

terms = [item["term"] for item in data]

# remove duplicates while preserving order
seen = set()
terms_unique = []
for t in terms:
    if t not in seen:
        seen.add(t)
        terms_unique.append(t)

# print as ONE LINE
print("[" + ", ".join(f'"{t}"' for t in terms_unique) + "]")
