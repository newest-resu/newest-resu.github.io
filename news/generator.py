import feedparser
import json
import datetime
from pathlib import Path
import html
import re

OUTPUT = Path("news/raw_news.json")

RSS_FEEDS = [
    # Yerel
    ("Anadolu Ajansı Yerel", "https://www.aa.com.tr/tr/rss/default?cat=yerel"),
    ("TRT Haber", "https://www.trthaber.com/rss/turkiye.rss"),
    ("Bursa Hakimiyet", "https://www.bursahakimiyet.com.tr/rss"),
    ("Yalova Gazetesi", "https://www.yalovagazetesi.com/rss"),

    # Spor
    ("NTV Spor", "https://www.ntvspor.net/rss"),
    ("TRT Spor", "https://www.trtspor.com.tr/rss/anasayfa.xml"),
    ("Fanatik", "https://www.fanatik.com.tr/rss"),

    # Dünya
    ("Reuters", "https://feeds.reuters.com/reuters/worldNews"),
    ("The Guardian", "https://www.theguardian.com/world/rss"),
    ("DW Türkçe", "https://rss.dw.com/rdf/rss-tr-all"),
    ("Euronews", "https://tr.euronews.com/rss"),
    
    ("Hürriyet", "https://www.hurriyet.com.tr/rss/gundem"),
    ("CNN Türk", "https://www.cnnturk.com/feed/rss/all/news"),
    ("NTV", "https://www.ntv.com.tr/gundem.rss"),
    ("Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=guncel"),
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Reuters", "https://feeds.reuters.com/reuters/worldNews"),
    ("DW Türkçe", "https://rss.dw.com/rdf/rss-tr-all"),

    # ================= EKONOMİ =================
    ("Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"),
    ("NTV Ekonomi", "https://www.ntv.com.tr/ekonomi.rss"),
    ("Dünya Gazetesi", "https://www.dunya.com/rss"),
    ("Bloomberg HT", "https://www.bloomberght.com/rss"),

    # ================= TEKNOLOJİ =================
    ("Webtekno", "https://www.webtekno.com/rss"),
    ("ShiftDelete.Net", "https://shiftdelete.net/feed"),
    ("DonanımHaber", "https://www.donanimhaber.com/rss"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),

    # ================= SAĞLIK =================
    ("Anadolu Ajansı Sağlık", "https://www.aa.com.tr/tr/rss/default?cat=saglik"),
    ("NTV Sağlık", "https://www.ntv.com.tr/saglik.rss"),
    ("Medical Xpress", "https://medicalxpress.com/rss-feed/"),
    ("Healthline", "https://www.healthline.com/rss"),

    # ================= FİNANS =================
    ("Investing Türkiye", "https://tr.investing.com/rss/news.rss"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),

    # ================= MAGAZİN =================
    ("Hürriyet Magazin", "https://www.hurriyet.com.tr/rss/magazin"),
    ("Milliyet Magazin", "https://www.milliyet.com.tr/rss/rssnew/magazinrss.xml"),
    ("People", "https://people.com/rss/"),
    ("TMZ", "https://www.tmz.com/rss.xml"),

    # ================= BİLİM =================
    ("AA Bilim Teknoloji", "https://www.aa.com.tr/tr/rss/default?cat=bilim-teknoloji"),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/all.xml"),
    ("Live Science", "https://www.livescience.com/feeds/all"),
    ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),

    # ================= SAVUNMA / ASKERİ =================
    ("AA Savunma", "https://www.aa.com.tr/tr/rss/default?cat=savunma"),
    ("Defence Blog", "https://defence-blog.com/feed/"),
    ("Breaking Defense", "https://breakingdefense.com/feed/"),
    ("Army Technology", "https://www.army-technology.com/feed/"),

    # ================= OYUN / DİJİTAL =================
    ("IGN", "https://feeds.ign.com/ign/all"),
    ("GameSpot", "https://www.gamespot.com/feeds/news/"),
    ("PC Gamer", "https://www.pcgamer.com/rss/"),
    ("Webtekno Oyun", "https://www.webtekno.com/rss"),

    # ================= OTOMOBİL =================
    ("Motor1 Türkiye", "https://tr.motor1.com/rss"),
    ("Auto Bild", "https://www.autobild.com/rss"),
    ("Carscoops", "https://www.carscoops.com/feed/"),
    ("TopGear", "https://www.topgear.com/rss"),

    # ================= YAŞAM =================
    ("Hürriyet Yaşam", "https://www.hurriyet.com.tr/rss/yasam"),
    ("NTV Yaşam", "https://www.ntv.com.tr/yasam.rss"),
    ("National Geographic", "https://www.nationalgeographic.com/content/natgeo/en_us/index.rss"),
    ("BBC Life", "https://feeds.bbci.co.uk/news/lifestyle/rss.xml"),
]

LOCAL_KEYWORDS = [
    "belediye", "valilik", "kaymakam","istanbul", "bursa", "kocaeli", "sakarya", "yalova"
]

CATEGORY_KEYWORDS = {
    "yerel": LOCAL_KEYWORDS,
    "gundem": ["bakan", "meclis", "cumhurbaşkanı", "seçim", "hükümet", "deprem", "sel", "fırtına"],
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
