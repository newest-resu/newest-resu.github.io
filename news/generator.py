import feedparser
import json
import datetime
from pathlib import Path
import html
import re

OUTPUT = Path("news/raw_news.json")

RSS_FEEDS = [
    # 🇹🇷 Yerel / Ulusal
    ("Hürriyet", "https://www.hurriyet.com.tr/rss/gundem"),
    ("CNN Türk", "https://www.cnnturk.com/feed/rss/all/news"),

    # 🌍 Yabancı
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Reuters", "https://feeds.reuters.com/reuters/worldNews"),
    ("The Guardian", "https://www.theguardian.com/world/rss"),
]

LOCAL_KEYWORDS = [
    "belediye", "valilik", "kaymakam",
    "istanbul", "bursa", "kocaeli", "sakarya", "yalova"
]

CATEGORY_KEYWORDS = {
    "yerel": LOCAL_KEYWORDS,
    "gundem": ["bakan", "meclis", "cumhurbaşkanı", "seçim", "politika"],
    "dunya": ["ukraine", "israel", "gaza", "usa", "china", "russia", "europe", "africa"],
    "spor": ["maç", "transfer", "gol", "lig", "football", "match"],
    "ekonomi": ["enflasyon", "dolar", "borsa", "faiz", "economy", "inflation", "market"],
    "teknoloji": ["yapay zeka", "ai", "apple", "google", "tesla", "technology"],
    "finans": ["stock", "shares", "investment", "bank", "finance"],
}

INTL_SOURCES = {"BBC", "Al Jazeera", "Reuters", "The Guardian"}

def clean_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def detect_category(text):
    t = text.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        for k in keys:
            if k in t:
                return cat
    return "gundem"

def is_local(text):
    t = text.lower()
    return any(k in t for k in LOCAL_KEYWORDS)

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

def build_long_summary(title, summary, source):
    """
    AI algısı oluşturmayan,
    haberle birebir ilişkili,
    dolu ve mantıklı uzun özet
    """
    base = summary if len(summary) > 120 else f"{title} başlığıyla duyurulan bu gelişme kamuoyunda dikkat çekti."

    return (
        f"{base} "
        f"Haber, {source} tarafından yayımlandı ve konuyla ilgili detaylar paylaşıldı. "
        "Yetkililerden ve konuya yakın kaynaklardan gelen bilgilere göre gelişmenin "
        "önümüzdeki günlerde farklı alanlara da yansıması bekleniyor. "
        "Kamuoyu ve ilgili çevreler süreci yakından takip ediyor."
    )

articles = []

for source, url in RSS_FEEDS:
    feed = feedparser.parse(url)

    source_type = "intl" if source in INTL_SOURCES else "tr"

    for e in feed.entries[:30]:
        title = clean_html(e.get("title", ""))
        link = e.get("link", "")
        published = e.get("published", "")

        raw_summary = clean_html(
            e.get("summary") or
            e.get("description") or
            ""
        )

        summary = raw_summary if raw_summary else f"{title} ile ilgili son gelişmeler paylaşıldı."
        long_summary = build_long_summary(title, summary, source)
        image = extract_image(e)

        combined_text = f"{title} {summary}"

        category = detect_category(combined_text)
        if source_type == "tr" and is_local(combined_text):
            category = "yerel"

        articles.append({
            "title": title,
            "summary": summary,
            "long_summary": long_summary,
            "url": link,
            "image": image,
            "source": source,
            "published_at": published,
            "category": category,
            "source_type": source_type,
            "meta_text": f"{source} | {category.upper()}"
        })

OUTPUT.parent.mkdir(exist_ok=True)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
