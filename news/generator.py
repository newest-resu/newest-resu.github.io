import feedparser
import json
import datetime
from pathlib import Path
import html
import re

OUTPUT = Path("news/latest.json")

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
    "dunya": ["ukraine", "israel", "gaza", "usa", "china", "russia", "europe"],
    "spor": ["match", "goal", "transfer", "league", "maç", "gol", "lig"],
    "ekonomi": ["inflation", "dolar", "borsa", "faiz", "economy"],
    "teknoloji": ["ai", "artificial intelligence", "apple", "google", "tesla"],
    "finans": ["bank", "stock", "market"],
}

def clean_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r"<[^>]+>", "", text).strip()

def detect_category(text):
    t = text.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if any(k in t for k in keys):
            return cat
    return "gundem"

def extract_image(entry):
    for key in ("media_content", "media_thumbnail"):
        if key in entry:
            m = entry[key]
            if isinstance(m, list) and m:
                return m[0].get("url", "")
    for e in entry.get("enclosures", []):
        if e.get("type", "").startswith("image"):
            return e.get("href", "")
    return ""

def build_long_summary(title, summary):
    base = summary if len(summary) > 120 else f"{title}. {summary}"
    return base.strip()

def build_bullets(summary):
    sentences = re.split(r'(?<=[.!?])\s+', summary)
    return [s.strip() for s in sentences[:3] if len(s.strip()) > 30]

articles = []

for source, url in RSS_FEEDS:
    feed = feedparser.parse(url)
    source_type = "intl" if source in ("BBC", "Al Jazeera") else "tr"

    for e in feed.entries[:25]:
        title = clean_html(e.get("title", ""))
        summary_raw = clean_html(e.get("summary") or e.get("description") or "")
        summary = summary_raw or f"{title} ile ilgili gelişmeler bildirildi."
        combined = f"{title} {summary}"

        category = detect_category(combined)
        if source_type == "tr" and any(k in combined.lower() for k in LOCAL_KEYWORDS):
            category = "yerel"

        articles.append({
            "title": title,
            "summary": summary,
            "long_summary": build_long_summary(title, summary),
            "why": [f"Haber, {category} kategorisi kapsamında önem taşıyor."],
            "background": build_bullets(summary),
            "impacts": build_bullets(summary),
            "url": e.get("link", ""),
            "image": extract_image(e),
            "source": source,
            "published_at": e.get("published", ""),
            "category": category,
            "source_type": source_type
        })

OUTPUT.parent.mkdir(exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
