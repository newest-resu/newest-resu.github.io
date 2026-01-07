import json
from pathlib import Path

RAW = Path("news/raw_news.json")
OUT = Path("news/latest.json")

MAX_ARTICLES = 50  # Performans limiti

with open(RAW, "r", encoding="utf-8") as f:
    raw = json.load(f)

articles = raw.get("articles", [])

def sort_key(item):
    # ISO tarih string’i varsa onu kullan
    return item.get("published_at") or ""

# 🔽 EN YENİ HABERLER ÜSTTE (STRING SORT)
articles = sorted(
    articles,
    key=sort_key,
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
