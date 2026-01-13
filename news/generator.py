import feedparser
import json
import html
import re
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

OUTPUT = Path("news/raw_news.json")
CUTOFF_HOURS = 36
NOW = datetime.now(timezone.utc)
CUTOFF_TIME = NOW - timedelta(hours=CUTOFF_HOURS)

RSS_FEEDS = [
    ("NTV", "https://www.ntv.com.tr/gundem.rss"),
    ("Habertürk", "https://www.haberturk.com/rss"),

    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Reuters World", "https://feeds.reuters.com/Reuters/worldNews"),

    ("Anadolu Ajansı Yerel", "https://www.aa.com.tr/tr/rss/default?cat=yerel"),
    ("TRT Haber", "https://www.trthaber.com/rss/turkiye.rss"),
    ("Bursa Hakimiyet", "https://www.bursahakimiyet.com.tr/rss"),
    ("Yalova Gazetesi", "https://www.yalovagazetesi.com/rss"),

    ("Sky Sports", "https://www.skysports.com/rss/12040"),
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

SOURCE_CATEGORY_MAP = {
    # 🇹🇷 TÜRKİYE
    "NTV": ("Türkiye Kaynaklı", "Gündem"),
    "Habertürk": ("Türkiye Kaynaklı", "Gündem"),
    "TRT Haber": ("Türkiye Kaynaklı", "Gündem"),

    "Anadolu Ajansı Yerel": ("Türkiye Kaynaklı", "Yerel"),
    "Bursa Hakimiyet": ("Türkiye Kaynaklı", "Yerel"),
    "Yalova Gazetesi": ("Türkiye Kaynaklı", "Yerel"),

    # 🌍 DÜNYA
    "BBC World": ("Yabancı Kaynaklar", "Dünya"),
    "Reuters World": ("Yabancı Kaynaklar", "Dünya"),

    # ⚽ SPOR
    "Sky Sports": ("Yabancı Kaynaklar", "Spor"),
    "BBC Sport": ("Yabancı Kaynaklar", "Spor"),

    # 💻 TEKNOLOJİ
    "Webtekno": ("Türkiye Kaynaklı", "Teknoloji"),
    "ShiftDelete": ("Türkiye Kaynaklı", "Teknoloji"),

    # 🏥 SAĞLIK
    "Sağlık Bakanlığı": ("Türkiye Kaynaklı", "Sağlık"),
    "Medimagazin": ("Türkiye Kaynaklı", "Sağlık"),

    # 💰 EKONOMİ / FİNANS
    "Dünya Gazetesi": ("Türkiye Kaynaklı", "Ekonomi"),
    "Bloomberg HT": ("Türkiye Kaynaklı", "Finans"),
    "Investing TR": ("Türkiye Kaynaklı", "Finans"),
    "Foreks": ("Türkiye Kaynaklı", "Finans"),

    # 🎭 MAGAZİN
    "Onedio": ("Türkiye Kaynaklı", "Magazin"),
    "Elle": ("Yabancı Kaynaklar", "Magazin"),

    # 🔬 BİLİM
    "Popular Science": ("Yabancı Kaynaklar", "Bilim"),
    "Science Daily": ("Yabancı Kaynaklar", "Bilim"),

    # 🛡️ SAVUNMA
    "Defense News": ("Yabancı Kaynaklar", "Savunma / Askeri"),
    "Breaking Defense": ("Yabancı Kaynaklar", "Savunma / Askeri"),

    # 🎮 OYUN
    "IGN": ("Yabancı Kaynaklar", "Oyun / Dijital"),
    "GameSpot": ("Yabancı Kaynaklar", "Oyun / Dijital"),

    # 🚗 OTOMOBİL
    "Motor1": ("Türkiye Kaynaklı", "Otomobil"),
    "Autocar": ("Yabancı Kaynaklar", "Otomobil"),
}

INTL_CATEGORY_KEYWORDS = {

    "savunma": ["military", "army", "defense", "missile", "weapon","air force", "navy","defence", "defense ministry","missile", "drone", "air strike","terror attack", "terrorism",
    "intelligence agency", "spy","border security"],
    "ekonomi": ["economy", "inflation", "market", "bank", "oil", "gas","economy", "economic growth", "recession", "inflation","gdp", "interest rate", "central bank",
    "federal reserve", "ecb", "bank of england","unemployment", "jobs report", "labor market","trade", "export", "import", "tariff","oil price", "energy prices", "budget", "deficit", "public spending"],
    "teknoloji": ["ai", "artificial intelligence", "tech", "google", "apple","technology", "tech company", "startup","artificial intelligence", "machine learning","robot", "automation",
    "software", "hardware", "chip", "semiconductor","cybersecurity", "data breach", "hacker","microsoft", "amazon", "meta","tesla", "spacex","space", "nasa", "satellite"],
    "spor": ["match", "goal", "league", "tournament","football", "soccer", "champions league", "premier league","la liga", "serie a", "bundesliga","world cup", "euro 2024", "qualifier",
    "fixture","transfer", "contract", "injury","coach", "manager","nba", "formula 1", "grand prix","olympics", "athletics", "tennis"],
    "finans": ["stock market", "shares", "equities","dow jones", "nasdaq", "s&p 500","bond", "treasury", "yield","currency", "forex", "exchange rate","dollar", "euro", "pound",
    "crypto", "bitcoin", "ethereum","investment", "investor", "hedge fund","banking sector", "financial crisis"],
    "saglık": ["health", "hospital", "medical","disease", "virus", "outbreak", "pandemic","covid", "vaccine", "vaccination","mental health", "depression", "anxiety","doctor", "nurse", "healthcare system",
    "who", "world health organization"],
    "magazin": ["celebrity", "celebrities","actor", "actress", "film star","movie", "film", "cinema","tv series", "television series","netflix", "amazon prime", "disney+","hollywood", "bollywood",
    "award", "oscars", "grammy", "emmy","red carpet", "premiere","music", "album", "song", "tour","concert", "festival","fashion", "designer", "runway","royal family", "prince", "princess",
    "marriage", "wedding", "divorce"],
    "bilim": ["science", "scientists", "research","study shows", "study finds","experiment", "laboratory","scientific journal", "peer reviewed","discovery", "breakthrough","physics", "chemistry", "biology",
    "genetics", "dna", "gene","astronomy", "astrophysics","black hole", "galaxy", "telescope","nasa", "esa", "space agency","climate research", "ocean research"],
    "oyun/dijital": ["video game", "gaming", "gamer","console", "pc gaming","playstation", "ps5","xbox", "nintendo","steam", "epic games","game studio", "game developer","release date", "launch trailer",
    "esports", "e-sports","tournament", "championship","online multiplayer","mobile game", "app store","in-game", "update patch"],
    "otomobil": ["car", "vehicle", "automaker","auto industry", "automotive sector","electric vehicle", "ev","hybrid car","tesla", "ford", "bmw", "mercedes","toyota", "volkswagen","battery technology",
    "self-driving", "autonomous vehicle","car launch", "new model","concept car","recall", "safety recall","traffic", "transportation","fuel price", "charging station"],
    "yasam": ["lifestyle", "daily life","modern life", "living standards","quality of life","family life", "parenting","children", "childcare","relationships", "marriage","dating", "divorce",
    "work-life balance","remote work lifestyle","home life", "household","interior design", "home decor","minimalism", "simple living","well-being", "wellbeing","mental well-being",
    "happiness", "life satisfaction","self improvement", "personal growth","habits", "daily habits","sleep habits", "morning routine","nutrition habits", "diet culture","food culture", "cooking at home",
    "recipes", "home cooking","travel lifestyle", "digital nomad","urban life", "city life","rural life", "village life","social life", "community life","leisure time", "free time","hobbies", "personal interests"],
    "dunya": ["war", "conflict", "attack", "peace", "border", "un", "nato","president", "prime minister", "government", "parliament","election", "vote", "ballot", "campaign","minister", "cabinet", "opposition",
    "diplomacy", "foreign policy", "summit", "talks","protest", "demonstration", "riot","sanction", "embargo","war", "conflict", "ceasefire", "invasion","united nations", "nato", "eu", "brussels","human rights",
    "refugee", "asylum"],
    
}

TR_CATEGORY_KEYWORDS = {
    "gundem": ["son dakika", "açıklama", "karar", "gelişme", "olay","idari", "resmi", "bildiri", "toplantı", "basın açıklaması", "soruşturma", "inceleme", "gözaltı", "tutuklama",
        "kanun", "yasa", "meclis", "tbmm", "genelge"],
    "dunya": ["uluslararası", "dışişleri", "yabancı", "küresel","nato", "bm", "birleşmiş milletler", "avrupa birliği","abd", "rusya", "ukrayna", "çin", "orta doğu",
        "savaş", "çatışma", "ateşkes", "diplomasi","zirve", "ambargo", "yaptırım"],
    "yerel": ["belediye", "büyükşehir", "il", "ilçe", "valilik","kaymakamlık", "yerel", "mahalle", "köy","altyapı", "yol çalışması", "su kesintisi", "elektrik kesintisi","imar", "çevre düzenlemesi",
        "yalova", "bursa", "istanbul", "izmit", "kocaeli", "sakarya"],
    "ekonomi": ["enflasyon", "zam", "maaş", "asgari ücret","faiz", "merkez bankası", "tcmb","banka", "kredi", "borç", "vergi","dolar", "euro", "altın", "petrol","ihracat", "ithalat", "cari açık",
        "büyüme", "ekonomik veri"],
    "finans": ["borsa", "bist", "hisse", "senet","yatırım", "portföy", "fon","kripto", "bitcoin", "ethereum","tahvil", "bono","faiz kararı", "piyasa", "endeks","finansal rapor", "şirket bilançosu"],
    "spor": ["maç", "gol", "lig", "puan durumu","transfer", "teknik direktör", "derbi","futbol", "basketbol", "voleybol","milli takım", "şampiyona","hakem", "kart", "ceza","taraftar", "stadyum"],
    "saglik": ["sağlık", "hastane", "doktor", "hemşire","aşı", "salgın", "grip", "covid","virüs", "bulaşıcı","ameliyat", "tedavi", "ilaç","sağlık bakanlığı", "halk sağlığı","psikoloji", "ruh sağlığı"],
    "teknoloji": ["teknoloji", "yazılım", "donanım","uygulama", "mobil uygulama","yapay zeka", "ai", "otomasyon","siber", "siber güvenlik","internet", "veri", "sunucu","sosyal medya", "platform","güncelleme", "sistem"],
    "bilim": ["bilim", "bilimsel", "araştırma","deney", "çalışma", "rapor","üniversite", "akademik","uzay", "nasa", "tübitak","iklim", "çevre", "küresel ısınma","biyoloji", "fizik", "kimya"],
    "magazin": ["ünlü", "sanatçı", "oyuncu","dizi", "film", "sinema","televizyon", "program","evlilik", "boşanma","magazin", "sosyal medya paylaşımı","konser", "albüm", "şarkı","moda", "defile"],
    "yasam": ["hava durumu", "fırtına", "yağmur", "kar","trafik", "kaza", "yoğunluk","eğitim", "okul", "üniversite","tatil", "resmi tatil","yaşam", "günlük hayat","toplu taşıma", "metro", "otobüs","konut", "kira"],
    "otomobil": ["otomobil", "araç", "trafik","kaza", "ehliyet","otomotiv", "araç muayenesi","elektrikli araç", "hibrit","yakıt", "benzin", "motorin","otoyol", "hız sınırı","servis", "geri çağırma"],
    "oyun/dijital": ["oyun", "video oyun","mobil oyun", "bilgisayar oyunu","espor", "turnuva","playstation", "xbox", "pc","steam", "epic games","güncelleme", "yama","oyuncu", "oyun stüdyosu"],
    "savunma": ["savunma", "askeri","ordu", "silahlı kuvvetler","tsk", "msb","tatbikat", "operasyon","insansız hava aracı", "iha", "siha","füze", "silah sistemi","güvenlik", "sınır güvenliği","terör", "terörle mücadele"]
}

CATEGORY_DISPLAY_MAP = {
    "gundem": "Gündem",
    "dunya": "Dünya",
    "yerel": "Yerel",
    "spor": "Spor",
    "teknoloji": "Teknoloji",
    "saglik": "Sağlık",
    "ekonomi": "Ekonomi",
    "finans": "Finans",
    "magazin": "Magazin",
    "bilim": "Bilim",
    "oyun/dijital": "Oyun / Dijital",
    "otomobil": "Otomobil",
    "yasam": "Yaşam",
    "savunma": "Savunma / Askeri"
}

def determine_categories(source, title, summary):
    # 1️⃣ Kaynağa göre kesin karar
    if source in SOURCE_CATEGORY_MAP:
        return SOURCE_CATEGORY_MAP[source]

    text = f"{title} {summary}".lower()

    # 2️⃣ Türkiye keyword fallback
    for cat, keywords in TR_CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            return ("Türkiye Kaynaklı", CATEGORY_DISPLAY_MAP.get(cat, cat.capitalize()))

    # 3️⃣ En son çare
    return ("Türkiye Kaynaklı", "Gündem")

TRANSLATION_CACHE = {}

def clean_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r"<[^>]+>", "", text).strip()

def parse_entry_date(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return None

def translate_text_safe(text):
    if not text or len(text) < 5:
        return text
    if text in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[text]
    try:
        r = requests.post(
            "https://libretranslate.de/translate",
            data={"q": text, "source": "en", "target": "tr"},
            timeout=15
        )
        if r.status_code == 200:
            translated = r.json().get("translatedText", text)
            TRANSLATION_CACHE[text] = translated
            time.sleep(0.3)
            return translated
    except Exception:
        pass
    return text

def build_long_summary(summary):
    return summary[:500]

def build_why_important(category):
    return f"{category} alanında kamuoyunu yakından ilgilendiren bir gelişme."

def build_possible_impacts(category):
    impacts = {
        "Ekonomi": "Piyasalarda dalgalanmalara yol açabilir.",
        "Finans": "Yatırımcı davranışlarını ve piyasaları etkileyebilir.",
        "Spor": "Takımlar ve taraftarlar açısından sonuçlar doğurabilir.",
        "Sağlık": "Toplum sağlığı açısından dikkat edilmesi gerekebilir.",
        "Teknoloji": "Dijital dönüşüm süreçlerini etkileyebilir.",
        "Gündem": "Geniş kitleleri ilgilendiren sonuçlar doğurabilir.",
        "Yerel": "Bölgesel yaşamı ve yerel hizmetleri etkileyebilir."
    }
    return impacts.get(category, "Gelişmenin farklı alanlarda etkileri olabilir.")
articles = []

for source, url in RSS_FEEDS:
    feed = feedparser.parse(url)

    for e in feed.entries[:25]:
        published_dt = parse_entry_date(e)
        if published_dt and published_dt < CUTOFF_TIME:
            continue

        raw_title = clean_html(e.get("title", ""))
        raw_summary = clean_html(e.get("summary") or e.get("description") or raw_title)

        main_category, _ = determine_categories(source, raw_title, raw_summary)

        title = translate_text_safe(raw_title) if main_category == "Yabancı Kaynaklar" else raw_title
        summary = translate_text_safe(raw_summary) if main_category == "Yabancı Kaynaklar" else raw_summary

        main_category, sub_category = determine_categories(
            source,
            title,
            summary
        )

        articles.append({
            "title": title,
            "summary": summary,
            "long_summary": build_long_summary(summary),
            "why_important": build_why_important(sub_category),
            "possible_impacts": build_possible_impacts(sub_category),
            "main_category": main_category,
            "sub_category": sub_category,
            "source": source,
            "url": e.get("link", ""),
            "published_at": e.get("published", "")
        })

OUTPUT.parent.mkdir(exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
