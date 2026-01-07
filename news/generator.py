import feedparser
import json
import datetime
from pathlib import Path
import html
import re
import requests

OUTPUT = Path("news/raw_news.json")

RSS_FEEDS = [
    ("NTV", "https://www.ntv.com.tr/gundem.rss"),
    ("Habertürk", "https://www.haberturk.com/rss"),

    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),

    ("Anadolu Ajansı Yerel", "https://www.aa.com.tr/tr/rss/default?cat=yerel"),
    ("TRT Haber", "https://www.trthaber.com/rss/turkiye.rss"),
    ("Bursa Hakimiyet", "https://www.bursahakimiyet.com.tr/rss"),
    ("Yalova Gazetesi", "https://www.yalovagazetesi.com/rss"),

    ("ESPN", "https://www.espn.com/espn/rss/news"),
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml"),

    ("Webtekno", "https://www.webtekno.com/rss.xml"),
    ("ShiftDelete", "https://shiftdelete.net/feed"),

    ("Sağlık Bakanlığı", "https://www.saglik.gov.tr/TR/rss"),
    ("Medimagazin", "https://www.medimagazin.com.tr/rss"),

    ("Dünya Gazetesi", "https://www.dunya.com/rss"),
    ("Bloomberg HT", "https://www.bloomberght.com/rss"),

    ("Investing TR", "https://tr.investing.com/rss/news_25.rss"),
    ("Foreks", "https://www.foreks.com/rss"),

    ("Onedio", "https://onedio.com/rss"),
    ("Elle", "https://www.elle.com/rss/all.xml"),

    ("Popular Science", "https://www.popsci.com/feed"),
    ("Science Daily", "https://www.sciencedaily.com/rss/all.xml"),

    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
    ("Breaking Defense", "https://breakingdefense.com/feed/"),

    ("IGN", "https://feeds.ign.com/ign/all"),
    ("GameSpot", "https://www.gamespot.com/feeds/news/"),

    ("Motor1", "https://tr.motor1.com/rss/news/all/"),
    ("Autocar", "https://www.autocar.co.uk/rss"),
]

INTL_CATEGORY_KEYWORDS = {
    "dunya": ["war", "conflict", "attack", "peace", "border", "un", "nato"],
    "ekonomi": ["economy", "inflation", "market", "bank", "oil", "gas"],
    "savunma": ["military", "army", "defense", "missile", "weapon"],
    "teknoloji": ["ai", "artificial intelligence", "tech", "google", "apple"],
    "spor": ["match", "goal", "league", "tournament"]
}

INTL_LABELS_TR = {
    "savunma": "Savunma",
    "ekonomi": "Ekonomi",
    "teknoloji": "Teknoloji",
    "spor": "Spor",
    "dunya": "Dünya"
}

def translate_en_to_tr(text):
    if not text or len(text.strip()) < 10:
        return text
    try:
        r = requests.post(
            "https://libretranslate.de/translate",
            data={"q": text, "source": "en", "target": "tr", "format": "text"},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("translatedText", text)
    except Exception:
        pass
    return text

def clean_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r"<[^>]+>", "", text).strip()

def detect_intl_category(text):
    t = text.lower()
    for cat in INTL_CATEGORY_KEYWORDS:
        if any(k in t for k in INTL_CATEGORY_KEYWORDS[cat]):
            return cat
    return "dunya"

def detect_category(text):
    t = text.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if any(k in t for k in keys):
            return cat
    return "gundem"

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
    source_type = "intl" if source in ("BBC World", "Al Jazeera") else "tr"

    for e in feed.entries[:30]:
        title = clean_html(e.get("title", ""))
        link = e.get("link", "")
        published = e.get("published", "")
        summary = clean_html(e.get("summary") or e.get("description") or "")
        summary = summary or f"{title} ile ilgili gelişmeler aktarıldı."

        if source_type == "intl":
            title = translate_en_to_tr(title)
            summary = translate_en_to_tr(summary)

        combined = f"{title} {summary}"
        image = extract_image(e)

        if source_type == "intl":
            intl_category = detect_intl_category(combined)
            category = "dunya"
            label_tr = f"Dünya • {INTL_LABELS_TR[intl_category]}"
        else:
            intl_category = None
            category = detect_category(combined)
            label_tr = category.capitalize()

        articles.append({
            "title": title,
            "summary": summary,
            "url": link,
            "image": image,
            "source": source,
            "published_at": published,
            "category": category,
            "intl_category": intl_category,
            "label_tr": label_tr,
            "source_type": source_type
        })

OUTPUT.parent.mkdir(exist_ok=True)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
