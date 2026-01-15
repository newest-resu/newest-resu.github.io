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

SOURCE_SUBCATEGORY_MAP = {
    # 🇹🇷 TÜRKİYE
    "NTV": "Gündem",
    "Habertürk": "Gündem",
    "TRT Haber": "Gündem",

    "Anadolu Ajansı Yerel": "Yerel",
    "Bursa Hakimiyet": "Yerel",
    "Yalova Gazetesi": "Yerel",

    # 🌍 DÜNYA
    "BBC World": "Dünya",
    "Reuters World": "Dünya",

    # ⚽ SPOR
    "Sky Sports": "Spor",
    "BBC Sport": "Spor",

    # 💻 TEKNOLOJİ
    "Webtekno": "Teknoloji",
    "ShiftDelete": "Teknoloji",

    # 🏥 SAĞLIK
    "Sağlık Bakanlığı": "Sağlık",
    "Medimagazin": "Sağlık",

    # 💰 EKONOMİ / FİNANS
    "Dünya Gazetesi": "Ekonomi",
    "Bloomberg HT": "Finans",
    "Investing TR": "Finans",
    "Foreks": "Finans",

    # 🎭 MAGAZİN
    "Onedio": "Magazin",
    "Elle": "Magazin",

    # 🔬 BİLİM
    "Popular Science": "Bilim",
    "Science Daily": "Bilim",

    # 🛡️ SAVUNMA
    "Defense News": "Savunma / Askeri",
    "Breaking Defense": "Savunma / Askeri",

    # 🎮 OYUN
    "IGN": "Oyun / Dijital",
    "GameSpot": "Oyun / Dijital",

    # 🚗 OTOMOBİL
    "Motor1": "Otomobil",
    "Autocar": "Otomobil",
}

FOREIGN_SOURCES = {
    "BBC World",
    "Reuters World",
    "Sky Sports",
    "BBC Sport",
    "Elle",
    "Popular Science",
    "Science Daily",
    "Defense News",
    "Breaking Defense",
    "IGN",
    "GameSpot",
    "Autocar"
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

def determine_origin(source):
    return "yabanci" if source in FOREIGN_SOURCES else "turkiye"

def stable_pick(text, options):
    if not text or not options:
        return None
    index = sum(ord(c) for c in text) % len(options)
    return options[index]

def slugify_category(label: str) -> str:
    if not label:
        return ""

    replacements = {
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u"
    }

    for k, v in replacements.items():
        label = label.replace(k, v)

    label = label.lower()
    label = label.replace("/", " ")
    label = re.sub(r"\s+", "_", label)

    return label.strip("_")

def determine_subcategory(source, origin, title, summary):
    text = f"{title} {summary}".lower()
    # 1️⃣ Kaynak bazlı override (en güçlü kural)
    if source in SOURCE_SUBCATEGORY_MAP:
        return SOURCE_SUBCATEGORY_MAP[source]

    # 2️⃣ Keyword bazlı sınıflandırma
    keyword_map = (
        TR_CATEGORY_KEYWORDS
        if origin == "turkiye"
        else INTL_CATEGORY_KEYWORDS
    )

    for cat, keywords in keyword_map.items():
        if any(k in text for k in keywords):
            return CATEGORY_DISPLAY_MAP.get(cat, CATEGORY_DISPLAY_MAP.get(cat.lower(), cat))

    # 3️⃣ Fallback
    return "Gündem" if origin == "turkiye" else "Dünya"
def is_local_news(origin, category):
    return origin == "turkiye" and category == "Yerel"

def extract_image(entry, summary_html=""):
    # 1️⃣ media:content
    media_content = entry.get("media_content")
    if media_content and isinstance(media_content, list):
        for m in media_content:
            if isinstance(m, dict) and m.get("url"):
                return m["url"]

    # 2️⃣ media:thumbnail
    media_thumbnail = entry.get("media_thumbnail")
    if media_thumbnail and isinstance(media_thumbnail, list):
        for m in media_thumbnail:
            if isinstance(m, dict) and m.get("url"):
                return m["url"]

    # 3️⃣ enclosures
    enclosures = entry.get("enclosures")
    if enclosures and isinstance(enclosures, list):
        for enc in enclosures:
            if enc.get("type", "").startswith("image") and enc.get("href"):
                return enc["href"]

    # 4️⃣ summary / description içinden <img> yakala
    if summary_html:
        match = re.search(r'<img[^>]+src="([^">]+)"', summary_html)
        if match:
            return match.group(1)

    # 5️⃣ Hiç görsel yok
    return None
   
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

def normalize_published_at(entry):
    dt = parse_entry_date(entry)
    if dt:
        return dt.isoformat()
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
    return summary[:500].rsplit(" ", 1)[0]

def build_why_important(category):
    reasons = {
        # Türkiye / Gündem
        "Gündem": [
            "Toplumu doğrudan ilgilendiren bir gelişme olması",
            "Kamuoyunu etkileyebilecek kararlar içermesi",
            "Resmî kurumları ve politikaları ilgilendirmesi"
        ],

        # Yerel
        "Yerel": [
            "Bölge halkının günlük yaşamını etkilemesi",
            "Yerel yönetim kararlarını ilgilendirmesi",
            "Şehir ve ilçelerde doğrudan sonuçlar doğurması"
        ],

        # Dünya
        "Dünya": [
            "Uluslararası dengeleri ilgilendirmesi",
            "Küresel gelişmelerle bağlantılı olması",
            "Türkiye’yi dolaylı olarak etkileyebilecek sonuçlar doğurması"
        ],

        # Ekonomi
        "Ekonomi": [
            "Ekonomik göstergeleri ve piyasa beklentilerini etkilemesi",
            "Vatandaşların alım gücüyle doğrudan ilişkili olması",
            "Makro ekonomik dengeler açısından önem taşıması"
        ],

        # Finans
        "Finans": [
            "Yatırımcılar açısından risk ve fırsatlar barındırması",
            "Finansal piyasalar üzerinde etkili olması",
            "Para ve sermaye hareketlerini ilgilendirmesi"
        ],

        # Spor
        "Spor": [
            "Sportif rekabet ve sonuçları etkilemesi",
            "Takımlar ve sporcular açısından kritik olması",
            "Taraftarlar ve spor kamuoyu tarafından yakından takip edilmesi"
        ],

        # Sağlık
        "Sağlık": [
            "Toplum sağlığı açısından önem taşıması",
            "Sağlık hizmetleri ve politikalarıyla ilgili olması",
            "Halk sağlığına yönelik risk veya önlemler içermesi"
        ],

        # Teknoloji
        "Teknoloji": [
            "Dijital dönüşüm süreçlerini etkilemesi",
            "Yeni teknolojik gelişmeler içermesi",
            "Kullanıcı alışkanlıklarını ve sektörleri etkilemesi"
        ],

        # Magazin
        "Magazin": [
            "Kamuoyunun ve medyanın ilgisini çekmesi",
            "Popüler kültür ve sosyal gündemle bağlantılı olması",
            "Toplumsal etkileşim yaratması"
        ],

        # Yaşam
        "Yaşam": [
            "Günlük hayatı ve sosyal düzeni etkilemesi",
            "Toplumsal alışkanlıklarla doğrudan ilişkili olması",
            "Geniş kesimleri ilgilendiren bir konu olması"
        ],

        # Otomobil
        "Otomobil": [
            "Ulaşım ve araç kullanımını etkilemesi",
            "Trafik güvenliği veya araç piyasasıyla ilgili olması",
            "Sürücüleri ve tüketicileri ilgilendirmesi"
        ],

        # Bilim
        "Bilim": [
            "Bilimsel araştırmalar ve yeni bulgular içermesi",
            "Teknolojik ve akademik gelişmelere katkı sağlaması",
            "Geleceğe yönelik önemli veriler sunması"
        ],

        # Oyun / Dijital
        "Oyun / Dijital": [
            "Dijital eğlence sektörünü etkilemesi",
            "Kullanıcı deneyimleri ve trendlerle ilgili olması",
            "Oyun ve dijital platformları ilgilendirmesi"
        ],

        # Savunma / Askeri
        "Savunma / Askeri": [
            "Ulusal veya bölgesel güvenlikle ilgili olması",
            "Savunma politikaları ve stratejileri etkilemesi",
            "Askerî gelişmeler açısından önem taşıması"
        ]
    }

    # Her haberde aynı cümle çıkmasın diye döndürme
    options = reasons.get(category)
    if options:
        pick = stable_pick(category, options)
        return [pick] if pick else [options[0]]

    return ["Kamuoyunu ilgilendiren önemli bir gelişme olması"]

def build_possible_impacts(category):
    impacts = {
        # Türkiye / Gündem
        "Gündem": [
            "Kamu politikalarında değişiklikler olabilir",
            "Toplumsal gündemde yeni tartışmalar doğabilir",
            "Resmî kurumların yeni adımlar atması beklenebilir"
        ],

        # Yerel (Türkiye altı)
        "Yerel": [
            "Yerel yönetimlerde karar süreçleri etkilenebilir",
            "Bölge halkının günlük yaşamı doğrudan etkilenebilir",
            "Belediye hizmetlerinde değişiklikler görülebilir"
        ],

        # Dünya
        "Dünya": [
            "Uluslararası ilişkilerde dengeler değişebilir",
            "Bölgesel güvenlik riskleri artabilir",
            "Küresel kamuoyunda yankı uyandırabilir"
        ],

        # Ekonomi
        "Ekonomi": [
            "Piyasalarda dalgalanma yaşanabilir",
            "Tüketici fiyatları ve alım gücü etkilenebilir",
            "Ekonomik beklentiler yeniden şekillenebilir"
        ],

        # Finans
        "Finans": [
            "Yatırımcı davranışları değişebilir",
            "Finansal piyasalarda volatilite artabilir",
            "Para ve sermaye akışları etkilenebilir"
        ],

        # Spor
        "Spor": [
            "Lig sıralamaları ve rekabet dengeleri değişebilir",
            "Takım stratejileri yeniden şekillenebilir",
            "Taraftar beklentileri etkilenebilir"
        ],

        # Sağlık
        "Sağlık": [
            "Toplum sağlığına yönelik önlemler artırılabilir",
            "Sağlık politikalarında güncellemeler yapılabilir",
            "Hizmet erişiminde değişiklikler olabilir"
        ],

        # Teknoloji
        "Teknoloji": [
            "Dijital dönüşüm süreçleri hızlanabilir",
            "Yeni ürün ve hizmetler gündeme gelebilir",
            "Siber güvenlik riskleri artabilir"
        ],

        # Magazin
        "Magazin": [
            "Kamuoyunun ilgisi farklı alanlara kayabilir",
            "Medya ve sosyal ağlarda etkileşim artabilir",
            "Popüler kültür trendleri değişebilir"
        ],

        # Yaşam
        "Yaşam": [
            "Günlük yaşam alışkanlıkları etkilenebilir",
            "Toplumsal farkındalık artabilir",
            "Kentsel ve sosyal düzenlemeler gündeme gelebilir"
        ],

        # Otomobil
        "Otomobil": [
            "Araç piyasasında fiyat ve talep dengeleri değişebilir",
            "Trafik ve ulaşım alışkanlıkları etkilenebilir",
            "Yeni düzenlemeler gündeme gelebilir"
        ],

        # Bilim
        "Bilim": [
            "Bilimsel araştırmalara ilgi artabilir",
            "Yeni keşifler farklı alanlara yön verebilir",
            "Akademik ve teknolojik gelişmeler hızlanabilir"
        ],

        # Oyun / Dijital
        "Oyun / Dijital": [
            "Dijital eğlence trendleri değişebilir",
            "Oyun sektöründe rekabet artabilir",
            "Kullanıcı alışkanlıkları dönüşebilir"
        ],

        # Savunma / Askeri
        "Savunma / Askeri": [
            "Bölgesel güvenlik dengeleri etkilenebilir",
            "Savunma politikalarında güncellemeler yapılabilir",
            "Askeri yatırımlar ve stratejiler değişebilir"
        ]
    }

    options = impacts.get(category)
    if options:
        pick = stable_pick(category, options)
        return [pick] if pick else [options[0]]
        
    return ["Olası etkiler zamanla netleşebilir."]
    
articles = []

for source, url in RSS_FEEDS:
    feed = feedparser.parse(url)

    for e in feed.entries[:25]:
        published_dt = parse_entry_date(e)
        if published_dt and published_dt < CUTOFF_TIME:
            continue

        image = extract_image(e, e.get("summary", ""))
        raw_title = clean_html(e.get("title", ""))
        raw_summary = clean_html(e.get("summary") or e.get("description") or raw_title)

        origin = determine_origin(source)

        title = translate_text_safe(raw_title) if origin == "yabanci" else raw_title
        summary = translate_text_safe(raw_summary) if origin == "yabanci" else raw_summary

        sub_category = determine_subcategory(
            source,
            origin,
            title,
            summary
        )

        articles.append({
            "origin": origin,
            "category": sub_category,
            "category_slug": slugify_category(sub_category),
            "is_local": is_local_news(origin, sub_category),
            "source": source,
            "title": title,
            "summary": summary,
            "long_summary": build_long_summary(summary),
            "why_important": build_why_important(sub_category),
            "possible_impacts": build_possible_impacts(sub_category),
            "url": e.get("link", ""),
            "image": image,
            "published_at": normalize_published_at(e)
         })
        
OUTPUT.parent.mkdir(exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
