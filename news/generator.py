import feedparser
import json
import hashlib
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse

# --- AYARLAR ---
OUTPUT_FILE = "news/latest.json"
MAX_ARTICLES = 300
TIMEOUT = 12
HEADERS = {
    "User-Agent": "HaberRobotuBot/1.0 (+https://newest-resu.github.io)"
}

# --- RSS KAYNAKLARI ---
RSS_SOURCES = [
    ("https://www.trthaber.com/rss/anasayfa.xml", "TRT Haber"),
    ("https://www.aa.com.tr/tr/rss/default?cat=guncel", "Anadolu Ajansı"),
    ("https://www.cnnturk.com/feed/rss/all/news", "CNN Türk"),
    ("https://www.ntv.com.tr/rss", "NTV"),
    ("https://www.istanbul.gov.tr/rss", "İstanbul Valiliği"),
    ("https://feeds.bbci.co.uk/news/rss.xml", "BBC"),
    ("https://rss.cnn.com/rss/edition.rss", "CNN Intl"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
    ("https://feeds.reuters.com/reuters/topNews", "Reuters"),
]

# --- KATEGORİ ANAHTAR KELİMELERİ ---
CATEGORY_KEYWORDS = {
    "yerel": ["belediye", "valilik", "kaymakam", "şehr", "ilçe", "il "],
    "finans": ["borsa", "hisse", "bitcoin", "kripto", "altın", "dolar", "euro", "borsada", "bist", "nasdaq", "endeks"],
    "ekonomi": ["ekonomi", "enflasyon", "bütçe", "faiz", "vergi", "asgari", "maaş", "piyasa", "ithalat", "ihracat"],
    "spor": ["spor", "maç", "lig", "gol", "transfer", "futbol", "basketbol", "voleybol", "tenis"],
    "teknoloji": ["teknoloji", "yapay zeka", "android", "ios", "robot", "çip", "chip", "uygulama", "app"],
    "saglik": ["sağlık", "saglik", "hastane", "doktor", "ilaç", "virus", "aşı", "asi"],
    "bilim": ["bilim", "araştırma", "evren", "nasa", "fizik", "kimya", "biyoloji"],
    "magazin": ["magazin", "ünlü", "film", "dizi", "konser"],
    "savunma": ["savunma", "ordu", "asker", "füze", "nato"],
    "oyun": ["oyun", "playstation", "xbox", "steam", "espor"],
    "otomobil": ["otomobil", "araba", "araç", "trafik"]
}

# --- YARDIMCILAR ---
def domain_of(url):
    try:
        return urlparse(url).hostname.lower()
    except:
        return ""

def classify_source(url):
    d = domain_of(url)
    if not d:
        return {"label": "Bilinmeyen", "type": "intl"}
    return {"label": d, "type": "tr" if d.endswith(".tr") else "intl"}

def find_best_category(text, url):
    lower = text.lower()

    # Yerel domain + içerik
    dom = domain_of(url)
    if dom.endswith(".tr"):
        for w in CATEGORY_KEYWORDS["yerel"]:
            if w in lower:
                return "yerel"

    # Keyword skoru
    best_cat, best_score = None, 0
    for cat, keys in CATEGORY_KEYWORDS.items():
        score = sum(k in lower for k in keys)
        if score > best_score:
            best_cat, best_score = cat, score

    if best_cat and best_score > 0:
        return best_cat

    # Fallback
    return "dunya" if not dom.endswith(".tr") else "gundem"

def make_long_summary(summary):
    if not summary or len(summary) < 120:
        return summary
    return summary.strip() + " Bu gelişme kamuoyu ve ilgili sektörler açısından kritik öneme sahiptir."

def why_important_text(cat):
    base = {
        "finans": ["Piyasa hareketlerinde etkili olabilir.", "Yatırımcı davranışını tetikleyebilir."],
        "ekonomi": ["Vatandaşın finansal durumunu etkileyebilir.", "Ekonomik denge üzerinde rol oynayabilir."],
        "yerel": ["Yerel halkı doğrudan ilgilendirir.", "Yerel yönetim kararlarını etkileyebilir."]
    }
    return base.get(cat, ["Kamuoyunu ilgilendiren bir gelişmedir."])

# --- ÜRETİM ---
def generate_news():
    articles = []
    seen = set()

    for feed_url, source in RSS_SOURCES:
        try:
            r = requests.get(feed_url, headers=HEADERS, timeout=TIMEOUT)
            feed = feedparser.parse(r.content)
        except Exception:
            continue

        for entry in feed.entries:
            link = getattr(entry, "link", "")
            if not link:
                continue

            uid = hashlib.md5(link.encode()).hexdigest()
            if uid in seen:
                continue
            seen.add(uid)

            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "").strip()

            text = f"{title} {summary}"

            cat = find_best_category(text, link)
            src_info = classify_source(link)

            article = {
                "id": uid,
                "title": title,
                "title_tr": title,
                "summary_tr": summary[:300],
                "summary_tr_long": make_long_summary(summary[:300]),
                "url": link,
                "image": "",
                "source": source,
                "published_at": getattr(entry, "published", ""),
                "category": cat,
                "why_important": why_important_text(cat),
                "background": ["Haber Robotu tarafından RSS ile otomatik derlenmiştir."],
                "possible_impacts": ["Bu haberin ilgili taraflara etkileri olabilir."]
            }

            articles.append(article)
            if len(articles) >= MAX_ARTICLES:
                break

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"{len(articles)} haber başarıyla üretildi.")

if __name__ == "__main__":
    generate_news()
