import feedparser
import json
import hashlib
import time
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse

# ================== AYARLAR ==================
OUTPUT_FILE = "news/latest.json"
MAX_ARTICLES = 250
TIMEOUT = 15

HEADERS = {
    "User-Agent": "HaberRobotuBot/1.0 (+https://newest-resu.github.io)"
}

RSS_SOURCES = [
    # --- TÜRKİYE ---
    ("https://www.trthaber.com/rss/anasayfa.xml", "TRT Haber"),
    ("https://www.aa.com.tr/tr/rss/default?cat=guncel", "Anadolu Ajansı"),
    ("https://www.cnnturk.com/feed/rss/all/news", "CNN Türk"),
    ("https://www.ntv.com.tr/rss", "NTV"),

    # --- YEREL ---
    ("https://www.istanbul.gov.tr/rss", "İstanbul Valiliği"),

    # --- YABANCI ---
    ("https://feeds.bbci.co.uk/news/rss.xml", "BBC"),
    ("https://rss.cnn.com/rss/edition.rss", "CNN Intl"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
    ("https://feeds.reuters.com/reuters/topNews", "Reuters"),
]

# ================== KATEGORİ ==================
KEYWORDS = {
    "yerel": ["belediye", "valilik", "il ", "ilçe", "mahall", "yerel"],
    "finans": ["borsa", "bitcoin", "kripto", "altın", "dolar", "euro", "hisse", "bist", "nasdaq", "bank"],
    "ekonomi": ["ekonomi", "enflasyon", "faiz", "bütçe", "asgari", "vergi", "maaş"],
    "spor": ["spor", "maç", "lig", "transfer", "gol"],
    "teknoloji": ["teknoloji", "yapay zeka", "android", "ios", "çip", "robot"],
    "saglik": ["sağlık", "hastane", "doktor", "ilaç", "virüs"],
    "bilim": ["bilim", "araştırma", "uzay", "nasa", "deney"],
    "magazin": ["magazin", "ünlü", "dizi", "film", "oyuncu"],
}

# ================== YARDIMCI ==================
def domain(url):
    try:
        return urlparse(url).hostname or ""
    except:
        return ""

def classify(article):
    text = f"{article['title']} {article['summary']}".lower()
    dom = domain(article["url"])

    scores = {k: 0 for k in KEYWORDS}
    for cat, words in KEYWORDS.items():
        for w in words:
            if w in text:
                scores[cat] += 1

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best

    if dom.endswith(".tr"):
        return "gundem"
    return "dunya"

def make_long_summary(summary):
    if len(summary) < 120:
        return summary
    return summary + " Bu gelişme kamuoyu ve ilgili sektörler açısından yakından takip ediliyor."

def why_important(cat):
    base = {
        "finans": [
            "Piyasalarda fiyatlamaları etkileyebilir",
            "Yatırımcı davranışlarını değiştirebilir"
        ],
        "ekonomi": [
            "Vatandaşın alım gücünü doğrudan etkiler",
            "Makroekonomik dengeler açısından önemlidir"
        ],
        "yerel": [
            "Bölge halkını doğrudan ilgilendiriyor",
            "Yerel yönetim kararlarını etkileyebilir"
        ],
    }
    return base.get(cat, ["Kamuoyunu ilgilendiren bir gelişme"])

# ================== ANA ==================
def generate():
    articles = []
    seen = set()

    for feed_url, source in RSS_SOURCES:
        try:
            r = requests.get(feed_url, headers=HEADERS, timeout=TIMEOUT)
            feed = feedparser.parse(r.content)
        except Exception as e:
            print("RSS hata:", feed_url, e)
            continue

        for e in feed.entries:
            url = getattr(e, "link", "")
            if not url:
                continue

            uid = hashlib.md5(url.encode()).hexdigest()
            if uid in seen:
                continue
            seen.add(uid)

            title = getattr(e, "title", "").strip()
            summary = getattr(e, "summary", "").strip()

            article = {
                "id": uid,
                "title": title,
                "title_tr": title,
                "summary": summary[:350],
                "summary_tr": summary[:350],
                "summary_tr_long": make_long_summary(summary[:350]),
                "url": url,
                "image": "",
                "source": source,
                "published_at": getattr(e, "published", ""),
            }

            cat = classify(article)
            article["category"] = cat
            article["why_important"] = why_important(cat)
            article["background"] = ["Haber otomatik RSS taramasıyla derlenmiştir."]
            article["possible_impacts"] = ["Kamuoyu ve ilgili sektörler üzerinde etkiler yaratabilir."]

            articles.append(article)
            if len(articles) >= MAX_ARTICLES:
                break

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"{len(articles)} haber üretildi.")

if __name__ == "__main__":
    generate()
