import json
from pathlib import Path
from datetime import datetime

RAW = Path("news/raw_news.json")
OUT = Path("news/latest.json")

MAX_ARTICLES = 50  # 🔴 Performans için limit

with open(RAW, "r", encoding="utf-8") as f:
    raw = json.load(f)

articles = raw.get("articles", [])

def parse_date(item):
    d = item.get("published_at", "")
    try:
        return datetime.fromisoformat(d)
    except Exception:
        return datetime.min

# 🔽 En yeni haberler üstte
articles = sorted(
    articles,
    key=parse_date,
    reverse=True
)

# 🔽 SADECE İLK 50 HABER
articles = articles[:MAX_ARTICLES]

OUT.parent.mkdir(exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(
        {
            "updated_at": raw.get("generated_at"),
            "articles": articles
        },
        f,
        ensure_ascii=False,
        indent=2
    )
