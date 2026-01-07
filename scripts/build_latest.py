import json
from pathlib import Path
from datetime import datetime

RAW = Path("news/raw_news.json")
OUT = Path("news/latest.json")
MAX_ARTICLES = 300

with open(RAW, "r", encoding="utf-8") as f:
    raw = json.load(f)

articles = raw.get("articles", [])

def parse_date(a):
    try:
        return datetime.fromisoformat(a.get("published_at", "").replace("Z", "+00:00"))
    except Exception:
        return datetime.min

articles = sorted(articles, key=parse_date, reverse=True)
articles = articles[:MAX_ARTICLES]

OUT.parent.mkdir(exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(
        {
            "updated_at": raw.get("generated_at"),
            "articles": articles,
        },
        f,
        ensure_ascii=False,
        indent=2,
    )
