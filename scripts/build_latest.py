import json
import feedparser
from datetime import datetime, timezone
from pathlib import Path

# RSS kaynakları NEREDEYSE oradan aynen alıyoruz
# RSS’lere kesinlikle dokunmuyoruz
from news.generator import FEEDS

OUTPUT_FILE = Path("news/latest.json")

MAX_PER_FEED = 10
MAX_TOTAL = 300


def parse_feed_safe(url: str):
    """RSS parse eder, hata varsa None döner"""
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            return None
        return feed
    except Exception:
        return None


def normalize(entry, category, source):
    """RSS entry -> standart haber objesi"""
    return {
        "title": (entry.get("title") or "").strip(),
        "link": entry.get("link", ""),
        "summary": (entry.get("summary") or "")[:600],
        "published": entry.get("published", ""),
        "category": category,
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    news = []

    for category, sources in FEEDS.items():
        for source_name, urls in sources.items():
            for url in urls:
                feed = parse_feed_safe(url)

                if not feed or not getattr(feed, "entries", None):
                    print(f"RSS atlandı: {url}")
                    continue

                for entry in feed.entries[:MAX_PER_FEED]:
                    try:
                        item = normalize(entry, category, source_name)

                        if item["title"] and item["link"]:
                            news.append(item)

                    except Exception as e:
                        print(f"Haber hatası ({url}): {e}")
                        continue

    # Limit uygula
    news = news[:MAX_TOTAL]

    # Dosyayı garanti yaz
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)

    print(f"✔ {len(news)} haber yazıldı -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
