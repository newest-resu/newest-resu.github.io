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
    ("NTV", "https://www.ntv.com.tr/gundem.rss"),
    ("Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=guncel"),
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Reuters", "https://feeds.reuters.com/reuters/worldNews"),
    ("DW Türkçe", "https://rss.dw.com/rdf/rss-tr-all"),
]

LOCAL_KEYWORDS = [
    "belediye", "valilik", "kaymakam",
    "istanbul", "bursa", "kocaeli", "sakarya", "yalova"
]

CATEGORY_KEYWORDS = {
    "yerel": LOCAL_KEYWORDS,
    "gundem": ["bakan", "meclis", "cumhurbaşkanı", "seçim", "hükümet"],
    "dunya": ["ukraine", "israel", "gaza", "usa", "china", "russia", "iran", "europe", "africa"],
    "spor": ["maç", "transfer", "gol", "lig", "şampiyon", "futbol", "basketbol"],
    "ekonomi": ["enflasyon", "dolar", "borsa", "faiz", "merkez bankası"],
    "teknoloji": ["yapay zeka", "ai", "apple", "google", "tesla", "microsoft"]
}

def clean_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def normalize_summary(summary, title):
    if not summary or len(summary) < 80:
        return f"{title} ile ilgili gelişmeler haber detaylarında ele alınıyor."
    return summary

def build_long_summary(title, summary, source):
    return (
        f"{title} başlığıyla paylaşılan bu haberde, {summary.lower()} "
        f"Haber, {source} kaynaklı olup gelişmelerin arka planına dair "
        f"temel bilgileri aktarmayı amaçlıyor."
    )

def detect_category(text):
    t = text.lower()

    if any(k in t for k in LOCAL_KEYWORDS):
        return "yerel"

    for cat, keys in CATEGORY_KEYWORDS.items():
        for k in keys:
            if k in t:
                return cat

    return "gundem"

def extract_image(entry):
    if "media_content" in entry:
        media = entry.media_content
        if isinstance(media, list) and media:
            return media[0].get("url")

    if "media_thumbnail" in entry:
        media = entry.media_thumbnail
        if isinstance(media, list) and media:
            return media[0].get("url")

    if "enclosures" in entry and entry.enclosures:
        for e in entry.enclosures:
            if e.get("type", "").startswith("image"):
                return e.get("href")

    return ""

articles = []

for source, url in RSS_FEEDS:
    feed = feedparser.parse(url)

    for e in feed.entries[:30]:
        title = clean_html(e.get("title", ""))
        link = e.get("link", "")
        published = e.get("published", "")

        raw_summary = clean_html(
            e.get("summary") or
            e.get("description") or
            ""
        )

        summary = normalize_summary(raw_summary, title)
        long_summary = build_long_summary(title, summary, source)
        image = extract_image(e)

        combined_text = f"{title} {summary}"
        category = detect_category(combined_text)

        articles.append({
            "title": title,
            "summary": summary,
            "long_summary": long_summary,
            "url": link,
            "image": image,
            "source": source,
            "published_at": published,
            "category": category,
            "source_type": "intl" if source in ["BBC", "Al Jazeera", "Reuters"] else "tr"
        })

OUTPUT.parent.mkdir(exist_ok=True)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
