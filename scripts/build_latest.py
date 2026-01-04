import json
import os
from datetime import datetime

SOURCE_FILE = "news/latest.json"
TARGET_FILE = "latest.json"
MAX_ITEMS = 200

REQUIRED_FIELDS = [
    "id",
    "title",
    "summary_tr",
    "url",
    "category",
    "source",
    "published_at"
]

def is_valid(article):
    for field in REQUIRED_FIELDS:
        if field not in article or not article[field]:
            return False
    return True

def optimize(article):
    return {
        "id": article["id"],
        "title": article["title_tr"],
        "summary": article["summary_tr_long"],
        "category": article["category"],
        "source": article["source"],
        "url": article["url"],
        "published_at": article["published_at"],
        "why_important": article.get("why_important", []),
        "background": article.get("background", []),
        "possible_impacts": article.get("possible_impacts", [])
    }

def main():
    if not os.path.exists(SOURCE_FILE):
        print("Kaynak JSON yok:", SOURCE_FILE)
        exit(1)

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    clean = []

    for a in articles:
        if is_valid(a):
            clean.append(optimize(a))
        if len(clean) >= MAX_ITEMS:
            break

    if not clean:
        print("Geçerli haber bulunamadı.")
        exit(1)

    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "count": len(clean),
        "articles": clean
    }

    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"{len(clean)} haber yayınlandı.")

if __name__ == "__main__":
    main()
