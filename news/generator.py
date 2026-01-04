import feedparser
import hashlib
import datetime
import json

try:
    # Çeviri için
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source="auto", target="tr")
except:
    translator = None

# ===== DEĞİŞTİRME ❗
# Burada RSS listesi değişmezz!
FEEDS = [
    # SENİN RAW DOSYANDAN GELEN URL LİSTESİ
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.cnn.com/rss/edition.rss",
    "https://www.reuters.com/rssFeed/worldNews",
    "https://www.hurriyet.com.tr/rss/anasayfa",
    "https://www.milliyet.com.tr/rss/rssnew/gundemrss.xml",
    "https://www.sozcu.com.tr/feed/",
    "https://www.ntv.com.tr/son-dakika.rss",
    "https://www.trthaber.com/rss/sondakika.rss",
    "https://www.haberturk.com/rss",
    "https://www.tgrthaber.com.tr/rss",
    # Ekonomi/Finans (TR)
    "https://www.hurriyet.com.tr/rss/ekonomi",
    "https://www.trthaber.com/rss/ekonomi.rss",

    # Spor (TR)
    "https://www.trthaber.com/rss/spor.rss",
    "https://www.ntv.com.tr/sporskor.rss",

    # Teknoloji/Bilim (TR)
    "https://www.ntv.com.tr/teknoloji.rss",
    "https://www.trthaber.com/rss/bilim-teknoloji.rss",

    # Sağlık (TR)
    "https://www.trthaber.com/rss/saglik.rss",

    # Magazin (TR)
    "https://www.ntv.com.tr/yasam.rss",

    # CNN Türk (sende vardı, korudum)
    "https://www.cnnturk.com/feed/rss/all/news",
    "https://www.cnnturk.com/feed/rss/ekonomi/news",
    "https://www.cnnturk.com/feed/rss/spor/news",
    "https://www.cnnturk.com/feed/rss/bilim-teknoloji/news",
    "https://www.cnnturk.com/feed/rss/magazin/news",
    "https://www.cnnturk.com/feed/rss/otomobil/news",
    "https://www.cnnturk.com/feed/rss/yasam/news",

    # =========================
    # DOĞRUDAN RSS (INTL) – Çeşitlilik
    # =========================
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "https://feeds.bbci.co.uk/news/health/rss.xml",
    # The Guardian RSS (genel/tech/business)
    "https://www.theguardian.com/world/rss",
    "https://www.theguardian.com/technology/rss",
    "https://www.theguardian.com/business/rss",

    # Al Jazeera (English)
    "https://www.aljazeera.com/xml/rss/all.xml",

    # =========================
    # GOOGLE NEWS RSS – Asıl “kaynak arttırma” motoru
    # (çok site getirir, domain çeşitliliği burada garanti)
    # =========================

    # Genel TR gündem/dünya
    "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=d%C3%BCnya%20when:7d&hl=tr&gl=TR&ceid=TR:tr",

    # Finans TR (çoklu sorgu)
    "https://news.google.com/rss/search?q=(borsa%20OR%20BIST%20OR%20hisse%20OR%20temett%C3%BC)%20when:7d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(dolar%20OR%20euro%20OR%20alt%C4%B1n%20OR%20gram%20alt%C4%B1n)%20when:7d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(TCMB%20OR%20faiz%20OR%20enflasyon)%20when:7d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(kripto%20OR%20Bitcoin%20OR%20Ethereum)%20when:7d&hl=tr&gl=TR&ceid=TR:tr",

    # Finans INTL
    "https://news.google.com/rss/search?q=(stocks%20OR%20markets%20OR%20inflation%20OR%20interest%20rates)%20when:7d&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=(gold%20price%20OR%20oil%20prices%20OR%20dollar%20index)%20when:7d&hl=en&gl=US&ceid=US:en",

    # Spor / Teknoloji / Sağlık / Magazin / Oyun / Otomobil
    "https://news.google.com/rss/search?q=(s%C3%BCper%20lig%20OR%20transfer%20OR%20ma%C3%A7)%20when:7d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(yapay%20zeka%20OR%20teknoloji%20OR%20android%20OR%20ios)%20when:7d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(sa%C4%9Fl%C4%B1k%20OR%20hastane%20OR%20tedavi%20OR%20a%C5%9F%C4%B1)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(magazin%20OR%20%C3%BCnl%C3%BC%20OR%20dizi%20OR%20film)%20when:7d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(mobil%20oyun%20OR%20PlayStation%20OR%20Xbox%20OR%20Steam)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(otomobil%20OR%20Tesla%20OR%20TOGG%20OR%20muayene)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",

    # Yerel Yalova (çoklu)
    "https://news.google.com/rss/search?q=Yalova%20when:7d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(Yalova%20Belediyesi%20OR%20Yalova%20Valili%C4%9Fi)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(%C3%87%C4%B1narc%C4%B1k%20OR%20%C3%87iftlikk%C3%B6y%20OR%20Alt%C4%B1nova%20OR%20Termal%20OR%20Armutlu)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
        # Yerel Marmara (Yalova + çevre iller)
    "https://news.google.com/rss/search?q=(Marmara%20B%C3%B6lgesi)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(Kocaeli%20OR%20%C4%B0zmit%20OR%20Gebze)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(Sakarya%20OR%20Adapazar%C4%B1)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(Bursa%20OR%20Nil%C3%BCfer%20OR%20Osmangazi%20OR%20Y%C4%B1ld%C4%B1r%C4%B1m)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(Bal%C4%B1kesir%20OR%20Band%C4%B1rma%20OR%20Edremit)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(Tekirda%C4%9F%20OR%20%C3%87orlu%20OR%20%C3%87erkezk%C3%B6y)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(K%C4%B1rklareli%20OR%20L%C3%BCleburgaz)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(Edirne)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(%C4%B0stanbul%20trafik%20OR%20%C4%B0stanbul%20belediye%20OR%20%C4%B0BB)%20when:7d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(%C3%87anakkale%20OR%20Biga)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",
    "https://news.google.com/rss/search?q=(Bilecik)%20when:14d&hl=tr&gl=TR&ceid=TR:tr",

]


def translate_text(text):
    if not translator:
        return text
    try:
        return translator.translate(text[:3800])
    except Exception as e:
        return text


articles = []

for url in FEEDS:
    try:
        # Feedparser ile RSS parse et
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"RSS parse hatası: {url} -> {e}")
        continue

    # Eğer feed boşsa atla
    if not hasattr(feed, "entries"):
        continue

    for entry in feed.entries[:10]:
        link = entry.get("link", "")
        if not link:
            continue

        uid = hashlib.sha1(link.encode()).hexdigest()
        title = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))

        # Uzun özet ve neden önemli / etkiler
        title_tr = translate_text(title)
        summary_tr = translate_text(summary)
        long_summary = translate_text(title + " " + summary)

        articles.append({
            "id": uid,
            "url": link,
            "title": title,
            "title_tr": title_tr,
            "summary_tr": summary_tr,
            "summary_tr_long": long_summary,
            "why_important": translate_text("Bu içerik önemli çünkü güncel gelişmeleri öne çıkarır ve kullanıcıya bağlam sağlar."),
            "possible_impacts": translate_text("Bu haber kısa veya uzun vadede etkiler yaratabilir."),
            "published": entry.get("published", ""),
            "source_type": "intl",  # Tüm bu URL’ler yabancı
        })

# Sonuç yaz
output = {
    "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "articles": articles
}

with open("news/raw.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
