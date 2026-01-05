import feedparser
import json
import datetime
from pathlib import Path

OUTPUT = Path("news/raw_news.json")

RSS_FEEDS = [
    ("Hürriyet", "https://www.hurriyet.com.tr/rss/gundem"),
    ("CNN Türk", "https://www.cnnturk.com/feed/rss/all/news"),
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
]

LOCAL_KEYWORDS = [
    "belediye","valilik","kaymakam",
    "istanbul","ankara","izmir",
    "bursa","kocaeli","sakarya","yalova"
]

CATEGORY_KEYWORDS = {
    "yerel": LOCAL_KEYWORDS,
    "gundem": ["bakan","meclis","cumhurbaşkanı","seçim"],
    "dunya": ["ukraine","israel","gaza","usa","china","russia"],
    "spor": ["maç","transfer","gol","lig"],
    "ekonomi": ["enflasyon","dolar","borsa","faiz"],
    "teknoloji": ["yapay zeka","ai","apple","google","tesla"],
}

def detect_category(title):
    t = title.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        for k in keys:
            if k in t:
                return cat
    return "gundem"

def is_local(title):
    t = title.lower()
    return any(k in t for k in LOCAL_KEYWORDS)

articles = []

for source, url in RSS_FEEDS:
    feed = feedparser.parse(url)
    for e in feed.entries[:30]:
        title = e.get("title", "").strip()
        link = e.get("link", "")
        published = e.get("published", "")

        category = detect_category(title)
        if is_local(title):
            category = "yerel"

        articles.append({
            "title": title,
            "url": link,
            "source": source,
            "published_at": published,
            "category": category,
            "source_type": "tr" if source != "BBC" and source != "Al Jazeera" else "intl"
        })

OUTPUT.parent.mkdir(exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
