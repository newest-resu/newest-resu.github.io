import json
from pathlib import Path

RAW = Path("news/raw_news.json")
OUT = Path("news/latest.json")

with open(RAW, "r", encoding="utf-8") as f:
    raw = json.load(f)

articles = raw.get("articles", [])

OUT.parent.mkdir(exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({
        "updated_at": raw.get("generated_at"),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
