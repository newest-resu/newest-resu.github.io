import os, re, json, hashlib
from datetime import datetime, timezone
import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document
from deep_translator import GoogleTranslator

# =========================
# AYARLAR
# =========================
OUT_PATH = "news/latest.json"
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "120"))

RSS_SOURCES = [
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "Dünya"},
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "category": "Teknoloji"},
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "category": "Ekonomi"},

    {"name": "Hürriyet", "url": "https://www.hurriyet.com.tr/rss/anasayfa", "category": "Gündem"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/all/news", "category": "Gündem"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/ekonomi/news", "category": "Ekonomi"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/spor/news", "category": "Spor"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/bilim-teknoloji/news", "category": "Teknoloji"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/saglik/news", "category": "Sağlık"},
]

UA = "HaberRobotuBot/1.0 (+https://newest-resu.github.io/)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})
translator = GoogleTranslator(source="auto", target="tr")

# =========================
# YARDIMCI FONKSİYONLAR
# =========================
def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s

def pick_image(entry) -> str:
    if hasattr(entry, "media_content") and entry.media_content:
        return entry.media_content[0].get("url", "")
    if hasattr(entry, "links"):
        for l in entry.links:
            if l.get("type", "").startswith("image/"):
                return l.get("href", "")
    return ""

def safe_get(url: str) -> str:
    r = SESSION.get(url, timeout=20)
    r.raise_for_status()
    return r.text

def extract_main_text(html: str) -> str:
    doc = Document(html)
    soup = BeautifulSoup(doc.summary(html_partial=True), "lxml")
    for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
        tag.decompose()
    return clean_text(soup.get_text(" "))

def sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 50]

def summarize(text: str, max_sentences=12):
    sents = sentences(text)
    return " ".join(sents[:max_sentences])

def tr(text: str) -> str:
    try:
        return translator.translate(text) if text else ""
    except:
        return text

# =========================
# KATMA DEĞER ÜRETİCİLER
# =========================
def build_long_summary_tr(text: str) -> str:
    base = summarize(text, 14)
    tr_text = tr(base)
    return tr_text

def why_important(category: str):
    MAP = {
        "Ekonomi": [
            "Ekonomik göstergeler ve piyasa beklentileri üzerinde etkisi olabilir.",
            "Yatırımcılar ve tüketiciler açısından dikkatle takip ediliyor."
        ],
        "Teknoloji": [
            "Teknolojik gelişmeler sektörün yönünü belirleyebilir.",
            "Kullanıcı alışkanlıklarını ve dijital ekosistemi etkileyebilir."
        ],
        "Sağlık": [
            "Toplum sağlığı açısından risk veya fırsatlar barındırıyor.",
            "Sağlık politikaları ve bireysel yaşamı etkileyebilir."
        ],
        "Spor": [
            "Spor kamuoyunda ve taraftarlar arasında geniş yankı uyandırdı.",
            "Lig dengeleri ve kulüp stratejileri üzerinde etkili olabilir."
        ],
        "Dünya": [
            "Uluslararası ilişkiler ve jeopolitik dengeler açısından önemli.",
            "Bölgesel ve küresel etkiler doğurabilir."
        ],
        "Gündem": [
            "Kamuoyunun yakından takip ettiği başlıklar arasında yer alıyor.",
            "Siyasi ve sosyal tartışmaları etkileyebilir."
        ]
    }
    return MAP.get(category, [
        "Kamuoyunu ilgilendiren önemli gelişmeler içeriyor.",
        "Yakın dönemde etkileri daha net görülebilir."
    ])

def background_info(category: str):
    MAP = {
        "Ekonomi": [
            "Benzer gelişmeler geçmişte piyasalarda dalgalanmalara yol açmıştı.",
            "Ekonomik veriler son dönemde yakından izleniyor."
        ],
        "Dünya": [
            "Bölgedeki gelişmeler uzun süredir uluslararası gündemde.",
            "Taraflar arasında süregelen anlaşmazlıklar bulunuyor."
        ],
        "Teknoloji": [
            "Teknoloji sektörü son yıllarda hızlı bir dönüşüm sürecinde.",
            "Şirketler rekabet avantajı için yatırımlarını artırıyor."
        ]
    }
    return MAP.get(category, [
        "Konu daha önce de kamuoyunda gündeme gelmişti.",
        "Arka planda uzun süredir devam eden gelişmeler bulunuyor."
    ])

def possible_impacts(category: str):
    MAP = {
        "Ekonomi": [
            "Piyasalarda dalgalanma ve fiyat değişimleri görülebilir.",
            "Ekonomik kararlar ve politikalar yeniden şekillenebilir."
        ],
        "Dünya": [
            "Diplomatik ilişkilerde yeni adımlar gündeme gelebilir.",
            "Bölgesel güvenlik dengeleri etkilenebilir."
        ],
        "Teknoloji": [
            "Yeni ürün ve hizmetlerin önünü açabilir.",
            "Sektörde rekabet koşulları değişebilir."
        ],
        "Sağlık": [
            "Toplum sağlığına yönelik yeni önlemler alınabilir.",
            "Sağlık sisteminde düzenlemeler gündeme gelebilir."
        ]
    }
    return MAP.get(category, [
        "Kısa ve orta vadede etkileri yakından izlenecek.",
        "Gelişmelere bağlı olarak yeni adımlar atılabilir."
    ])

# =========================
# ANA AKIŞ
# =========================
def main():
    raw = []

    for src in RSS_SOURCES:
        feed = feedparser.parse(src["url"])
        for e in feed.entries[: MAX_ARTICLES * 2]:
            url = getattr(e, "link", "")
            if not url:
                continue
            raw.append({
                "id": sha1(url),
                "url": url,
                "title": clean_text(getattr(e, "title", "")),
                "summary": clean_text(BeautifulSoup(getattr(e, "summary", ""), "lxml").get_text()),
                "image": pick_image(e),
                "source": src["name"],
                "rss_categories": [src["category"]],
            })

    seen = set()
    items = []
    for r in raw:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        items.append(r)
    items = items[:MAX_ARTICLES]

    for it in items:
        try:
            html = safe_get(it["url"])
            content = extract_main_text(html)

            it["title_tr"] = tr(it["title"])
            it["summary_tr_long"] = build_long_summary_tr(content)
            it["summary_tr"] = it["summary_tr_long"][:400]

            cat = it["rss_categories"][0]
            it["why_important"] = why_important(cat)
            it["background"] = background_info(cat)
            it["possible_impacts"] = possible_impacts(cat)

        except Exception as e:
            it["summary_tr_long"] = tr(it["summary"])
            it["summary_tr"] = tr(it["summary"])
            it["why_important"] = []
            it["background"] = []
            it["possible_impacts"] = []
            it["error"] = str(e)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "articles": items,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"✅ latest.json üretildi: {len(items)} haber")

if __name__ == "__main__":
    main()
