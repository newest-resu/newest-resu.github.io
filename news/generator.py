import feedparser
import json
import datetime
from pathlib import Path
import html
import re

OUTPUT = Path("news/raw_news.json")

RSS_FEEDS = [
    ("Hürriyet", "https://www.hurriyet.com.tr/rss/gundem"),
    ("CNN Türk", "https://www.cnnturk.com/feed/rss/all/news"),
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
]

LOCAL_KEYWORDS = [
    "belediye", "valilik", "kaymakam",
    "istanbul", "bursa", "kocaeli", "sakarya", "yalova"
]

CATEGORY_KEYWORDS = {
    "yerel": LOCAL_KEYWORDS,
    "gundem": ["bakan", "meclis", "cumhurbaşkanı", "seçim"],
    "dunya": ["ukraine", "israel", "gaza", "usa", "china", "russia"],
    "spor": ["maç", "transfer", "gol", "lig"],
    "ekonomi": ["enflasyon", "dolar", "borsa", "faiz"],
    "teknoloji": ["yapay zeka", "ai", "apple", "google", "tesla"],
}

def clean_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r"<[^>]+>", "", text).strip()

def normalize_summary(summary, title, source_type):
    if summary and len(summary) > 80:
        return summary

    if source_type == "intl":
        return f"{title} başlıklı haber yabancı kaynaklardan derlenmiştir. Ayrıntılar haber içeriğinde yer almaktadır."

    return f"{title} ile ilgili gelişmeler haber detaylarında yer alıyor."

def detect_category(text):
    t = text.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if any(k in t for k in keys):
            return cat
    return "gundem"

def is_local(text):
    t = text.lower()
    return any(k in t for k in LOCAL_KEYWORDS)

def extract_image(entry):
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key)
        if isinstance(media, list) and media:
            return media[0].get("url", "")

    for e in entry.get("enclosures", []):
        if e.get("type", "").startswith("image"):
            return e.get("href", "")

    return ""

articles = []

for source, url in RSS_FEEDS:
    feed = feedparser.parse(url)
    source_type = "intl" if source in ("BBC", "Al Jazeera") else "tr"

    for e in feed.entries[:30]:
        title = clean_html(e.get("title", ""))
        link = e.get("link", "")
        published = e.get("published", "")

        raw_summary = clean_html(
            e.get("summary") or
            e.get("description") or
            ""
        )

        summary = normalize_summary(raw_summary, title, source_type)
        image = extract_image(e)
        combined = f"{title} {summary}"

        if source_type == "intl":
            category = "yabanci"
        else:
            category = detect_category(combined)
            if is_local(combined):
                category = "yerel"

        articles.append({
            "title": title,
            "summary": summary,
            "url": link,
            "image": image,
            "source": source,
            "published_at": published,
            "category": category,
            "source_type": source_type
        })

OUTPUT.parent.mkdir(exist_ok=True)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
