import feedparser
import hashlib
import datetime
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source="auto", target="tr")

def tr(txt):
    try:
        return translator.translate(txt[:3800])
    except:
        return txt

def enrich(title, summary):
    base = f"{title}. {summary}"
    return {
        "summary_tr_long": tr(base)[:1200],
        "why_important": tr("Bu gelişme ekonomi, siyaset veya toplum açısından dikkat çekici sonuçlar doğurabilir."),
        "possible_impacts": tr("Kısa vadede kamuoyu algısını, uzun vadede ise politika ve piyasa kararlarını etkileyebilir.")
    }

feeds = [
    {"url": "https://www.hurriyet.com.tr/rss/anasayfa", "hint": "gundem"},
    {"url": "https://www.milliyet.com.tr/rss/rssnew/gundemrss.xml", "hint": "gundem"},
    {"url": "https://www.sozcu.com.tr/feed/", "hint": "gundem"},
    {"url": "https://www.ntv.com.tr/son-dakika.rss", "hint": "gundem"},
    {"url": "https://www.trthaber.com/rss/sondakika.rss", "hint": "gundem"},
    {"url": "https://www.haberturk.com/rss", "hint": "gundem"},
    {"url": "https://www.tgrthaber.com.tr/rss", "hint": "gundem"},

    # Ekonomi/Finans (TR)
    {"url": "https://www.hurriyet.com.tr/rss/ekonomi", "hint": "ekonomi"},
    {"url": "https://www.trthaber.com/rss/ekonomi.rss", "hint": "ekonomi"},

    # Spor (TR)
    {"url": "https://www.trthaber.com/rss/spor.rss", "hint": "spor"},
    {"url": "https://www.ntv.com.tr/sporskor.rss", "hint": "spor"},

    # Teknoloji/Bilim (TR)
    {"url": "https://www.ntv.com.tr/teknoloji.rss", "hint": "teknoloji"},
    {"url": "https://www.trthaber.com/rss/bilim-teknoloji.rss", "hint": "teknoloji"},

    # Sağlık (TR)
    {"url": "https://www.trthaber.com/rss/saglik.rss", "hint": "saglik"},

    # Magazin (TR)
    {"url": "https://www.ntv.com.tr/yasam.rss", "hint": "yasam"},

    # CNN Türk (sende vardı, korudum)
    {"url": "https://www.cnnturk.com/feed/rss/all/news", "hint": "gundem"},
    {"url": "https://www.cnnturk.com/feed/rss/ekonomi/news", "hint": "ekonomi"},
    {"url": "https://www.cnnturk.com/feed/rss/spor/news", "hint": "spor"},
    {"url": "https://www.cnnturk.com/feed/rss/bilim-teknoloji/news", "hint": "teknoloji"},
    {"url": "https://www.cnnturk.com/feed/rss/magazin/news", "hint": "magazin"},
    {"url": "https://www.cnnturk.com/feed/rss/otomobil/news", "hint": "otomobil"},
    {"url": "https://www.cnnturk.com/feed/rss/yasam/news", "hint": "yasam"},

    # =========================
    # DOĞRUDAN RSS (INTL) – Çeşitlilik
    # =========================
    {"url": "https://feeds.bbci.co.uk/news/rss.xml", "hint": "dunya"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "hint": "dunya"},
    {"url": "https://feeds.bbci.co.uk/news/business/rss.xml", "hint": "finans"},
    {"url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "hint": "teknoloji"},
    {"url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "hint": "bilim"},
    {"url": "https://feeds.bbci.co.uk/news/health/rss.xml", "hint": "saglik"},

    # The Guardian RSS (genel/tech/business)
    {"url": "https://www.theguardian.com/world/rss", "hint": "dunya"},
    {"url": "https://www.theguardian.com/technology/rss", "hint": "teknoloji"},
    {"url": "https://www.theguardian.com/business/rss", "hint": "finans"},

    # Al Jazeera (English)
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "hint": "dunya"},

    # =========================
    # GOOGLE NEWS RSS – Asıl “kaynak arttırma” motoru
    # (çok site getirir, domain çeşitliliği burada garanti)
    # =========================

    # Genel TR gündem/dünya
    {"url": "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr", "hint": "gundem"},
    {"url": "https://news.google.com/rss/search?q=d%C3%BCnya%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "dunya"},

    # Finans TR (çoklu sorgu)
    {"url": "https://news.google.com/rss/search?q=(borsa%20OR%20BIST%20OR%20hisse%20OR%20temett%C3%BC)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(dolar%20OR%20euro%20OR%20alt%C4%B1n%20OR%20gram%20alt%C4%B1n)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(TCMB%20OR%20faiz%20OR%20enflasyon)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(kripto%20OR%20Bitcoin%20OR%20Ethereum)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "finans"},

    # Finans INTL
    {"url": "https://news.google.com/rss/search?q=(stocks%20OR%20markets%20OR%20inflation%20OR%20interest%20rates)%20when:7d&hl=en&gl=US&ceid=US:en", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(gold%20price%20OR%20oil%20prices%20OR%20dollar%20index)%20when:7d&hl=en&gl=US&ceid=US:en", "hint": "finans"},

    # Spor / Teknoloji / Sağlık / Magazin / Oyun / Otomobil
    {"url": "https://news.google.com/rss/search?q=(s%C3%BCper%20lig%20OR%20transfer%20OR%20ma%C3%A7)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "spor"},
    {"url": "https://news.google.com/rss/search?q=(yapay%20zeka%20OR%20teknoloji%20OR%20android%20OR%20ios)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "teknoloji"},
    {"url": "https://news.google.com/rss/search?q=(sa%C4%9Fl%C4%B1k%20OR%20hastane%20OR%20tedavi%20OR%20a%C5%9F%C4%B1)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "saglik"},
    {"url": "https://news.google.com/rss/search?q=(magazin%20OR%20%C3%BCnl%C3%BC%20OR%20dizi%20OR%20film)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "magazin"},
    {"url": "https://news.google.com/rss/search?q=(mobil%20oyun%20OR%20PlayStation%20OR%20Xbox%20OR%20Steam)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "oyun"},
    {"url": "https://news.google.com/rss/search?q=(otomobil%20OR%20Tesla%20OR%20TOGG%20OR%20muayene)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "otomobil"},

    # Yerel Yalova (çoklu)
    {"url": "https://news.google.com/rss/search?q=Yalova%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Yalova%20Belediyesi%20OR%20Yalova%20Valili%C4%9Fi)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(%C3%87%C4%B1narc%C4%B1k%20OR%20%C3%87iftlikk%C3%B6y%20OR%20Alt%C4%B1nova%20OR%20Termal%20OR%20Armutlu)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
        # Yerel Marmara (Yalova + çevre iller)
    {"url": "https://news.google.com/rss/search?q=(Marmara%20B%C3%B6lgesi)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Kocaeli%20OR%20%C4%B0zmit%20OR%20Gebze)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Sakarya%20OR%20Adapazar%C4%B1)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Bursa%20OR%20Nil%C3%BCfer%20OR%20Osmangazi%20OR%20Y%C4%B1ld%C4%B1r%C4%B1m)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Bal%C4%B1kesir%20OR%20Band%C4%B1rma%20OR%20Edremit)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Tekirda%C4%9F%20OR%20%C3%87orlu%20OR%20%C3%87erkezk%C3%B6y)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(K%C4%B1rklareli%20OR%20L%C3%BCleburgaz)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Edirne)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(%C4%B0stanbul%20trafik%20OR%20%C4%B0stanbul%20belediye%20OR%20%C4%B0BB)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(%C3%87anakkale%20OR%20Biga)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Bilecik)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
]

articles = []

for url in FEEDS:
    try:
        d = feedparser.parse(url)
    except Exception as e:
        print("RSS fetch error:", url, e)
        continue

    for entry in d.entries[:10]:
        link = entry.get("link", "")
        title = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))

        uid = hashlib.sha1(link.encode()).hexdigest()

        title_tr = tr(title)
        summary_tr = tr(summary)

        # Basit yerel “keyword”
        is_local = "yalova" in title_tr.lower() or "yalova" in summary_tr.lower()

        articles.append({
            "id": uid,
            "url": link,
            "title": title,
            "title_tr": title_tr,
            "summary_tr": summary_tr,
            "source_type": "intl",  # yabancı RSS olduğu için
            "is_local": is_local
        })

import json, os
os.makedirs("news", exist_ok=True)

with open("news/raw.json", "w", encoding="utf-8") as f:
    import json
    json.dump(articles, f, ensure_ascii=False, indent=2)
