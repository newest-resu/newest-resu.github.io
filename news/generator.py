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

INTL_LABELS_TR = {
    "savunma": "Savunma",
    "ekonomi": "Ekonomi",
    "teknoloji": "Teknoloji",
    "spor": "Spor",
    "finans": "Finans",
    "saglık": "Sağlık",
    "magazin": "Magazin",
    "bilim": "Bilim",
    "oyun/dijital": "Oyun / Dijital",
    "otomobil": "Otomobil",
    "yasam": "Yaşam",
    "dunya": "Dünya"
}

def clean_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r"<[^>]+>", "", text).strip()

# -------------------------
# TRANSLATION CACHE
# -------------------------
TRANSLATION_CACHE = {}

def translate_text_safe(text):
    if not text or len(text.strip()) < 5:
        return text

    if text in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[text]

    try:
        r = requests.post(
            "https://libretranslate.de/translate",
            data={
                "q": text,
                "source": "en",
                "target": "tr",
                "format": "text"
            },
            timeout=15
        )
        if r.status_code == 200:
            translated = r.json().get("translatedText", text)
            TRANSLATION_CACHE[text] = translated
            time.sleep(0.3)  # rate-limit guard
            return translated
    except Exception:
        pass

    return text

def translate_article(title, summary):
    combined = f"TITLE: {title}\nSUMMARY: {summary}"
    translated = translate_text_safe(combined)

    if "SUMMARY:" in translated:
        t_title, t_summary = translated.split("SUMMARY:", 1)
        return (
            t_title.replace("TITLE:", "").strip(),
            t_summary.strip()
        )

    return title, summary

def detect_intl_category(text):
    t = text.lower()
    scores = {cat: sum(1 for k in keys if k in t) for cat, keys in INTL_CATEGORY_KEYWORDS.items()}
    scores = {k: v for k, v in scores.items() if v > 0}
    return max(scores, key=scores.get) if scores else "dunya"

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
    source_type = "intl" if source in (
        "BBC World", "Reuters World", "Sky Sports", "BBC Sport","Defense News","Breaking Defense", "Popular Science", "Science Daily","Elle","IGN","GameSpot","Autocar"
    ) else "tr"

    for e in feed.entries[:25]:
        raw_title = clean_html(e.get("title", ""))
        raw_summary = clean_html(e.get("summary") or e.get("description") or "")
        raw_summary = raw_summary or f"{raw_title} ile ilgili gelişmeler aktarıldı."

        combined_raw = f"{raw_title} {raw_summary}"

        if source_type == "intl":
            intl_category = detect_intl_category(combined_raw)
            title, summary = translate_article(raw_title, raw_summary)
            category = intl_category
            label_tr = INTL_LABELS_TR.get(intl_category, "Dünya")
        else:
            intl_category = None
            title = raw_title
            summary = raw_summary
            category = "gundem"
            label_tr = "Gündem"

        articles.append({
            "title": title,
            "summary": summary,
            "url": e.get("link", ""),
            "image": extract_image(e),
            "source": source,
            "published_at": e.get("published", ""),
            "category": category,
            "intl_category": intl_category,
            "label_tr": label_tr,
            "source_type": source_type
        })

OUTPUT.parent.mkdir(exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(
        {
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "articles": articles
        },
        f,
        ensure_ascii=False,
        indent=2
    )
