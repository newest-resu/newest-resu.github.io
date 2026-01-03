import json, datetime

with open("news/raw.json", encoding="utf-8") as f:
    raw = json.load(f)

def categorize(a):
    t = (a["title_tr"] + " " + a["summary_tr"]).lower()

    if any(k in t for k in ["borsa","faiz","enflasyon","dolar","bitcoin","kripto"]):
        return "finans"
    if any(k in t for k in ["yalova","çınarcık","altınova"]):
        return "yerel"
    if any(k in t for k in ["maç","gol","transfer"]):
        return "spor"
    if any(k in t for k in ["dizi","film","ünlü"]):
        return "magazin"
    if any(k in t for k in ["yapay zeka","teknoloji","iphone"]):
        return "teknoloji"
    return "gundem"

for a in raw:
    a["category"] = categorize(a)

latest = {
    "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "articles": raw[:120]
}

with open("news/latest.json", "w", encoding="utf-8") as f:
    json.dump(latest, f, ensure_ascii=False, indent=2)
