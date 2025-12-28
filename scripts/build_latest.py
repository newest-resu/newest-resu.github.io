# scripts/build_latest.py
import json
import os
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import requests
import feedparser
from bs4 import BeautifulSoup

OUT_PATH = os.path.join("news", "latest.json")
os.makedirs("news", exist_ok=True)

TR_TZ = timezone(timedelta(hours=3))  # Europe/Istanbul (+03:00)
UA = "Mozilla/5.0 (compatible; HaberRobotuBot/1.0; +https://newest-resu.github.io/)"

MAX_ITEMS_PER_SOURCE = 18
TOTAL_LIMIT = 260  # biraz artırdım

# ------------------------------------------------------------
# RSS Sources (Finans + Yerel güçlendirildi)
# Güvenlik/Stabilite için ağırlık: Google News RSS (çok siteyi kapsar)
# ------------------------------------------------------------
RSS_SOURCES = [
    # --- BBC (genel) ---
    {"url": "https://feeds.bbci.co.uk/news/rss.xml", "hint": "dunya"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "hint": "dunya"},
    {"url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "hint": "teknoloji"},
    {"url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "hint": "bilim"},
    {"url": "https://feeds.bbci.co.uk/news/health/rss.xml", "hint": "saglik"},
    {"url": "https://feeds.bbci.co.uk/news/business/rss.xml", "hint": "finans"},  # sadece doğrulanırsa finans

    # --- TR örnek kaynaklarınız (mevcut düzenle uyumlu) ---
    {"url": "https://www.hurriyet.com.tr/rss/anasayfa", "hint": "gundem"},
    {"url": "https://www.cnnturk.com/feed/rss/all/news", "hint": "gundem"},
    {"url": "https://www.cnnturk.com/feed/rss/turkiye/news", "hint": "gundem"},
    {"url": "https://www.cnnturk.com/feed/rss/dunya/news", "hint": "dunya"},
    {"url": "https://www.cnnturk.com/feed/rss/ekonomi/news", "hint": "ekonomi"},
    {"url": "https://www.cnnturk.com/feed/rss/spor/news", "hint": "spor"},
    {"url": "https://www.cnnturk.com/feed/rss/bilim-teknoloji/news", "hint": "teknoloji"},
    {"url": "https://www.cnnturk.com/feed/rss/saglik/news", "hint": "saglik"},
    {"url": "https://www.cnnturk.com/feed/rss/magazin/news", "hint": "magazin"},
    {"url": "https://www.cnnturk.com/feed/rss/otomobil/news", "hint": "otomobil"},
    {"url": "https://www.cnnturk.com/feed/rss/yasam/news", "hint": "yasam"},

    # =========================
    # FINANS (TR) – 7 günlük aramalar (birkaç farklı sorgu)
    # =========================
    {"url": "https://news.google.com/rss/search?q=(borsa%20OR%20BIST%20OR%20hisse%20OR%20temett%C3%BC)%20when%3A7d&hl=tr&gl=TR&ceid=TR%3Atr", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(dolar%20OR%20euro%20OR%20alt%C4%B1n%20OR%20gram%20alt%C4%B1n)%20when%3A7d&hl=tr&gl=TR&ceid=TR%3Atr", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(TCMB%20OR%20faiz%20OR%20enflasyon%20OR%20PPI%20OR%20CPI)%20when%3A7d&hl=tr&gl=TR&ceid=TR%3Atr", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(kripto%20OR%20Bitcoin%20OR%20Ethereum)%20when%3A7d&hl=tr&gl=TR&ceid=TR%3Atr", "hint": "finans"},

    # =========================
    # FINANS (INTL) – İngilizce aramalar (global piyasalar)
    # =========================
    {"url": "https://news.google.com/rss/search?q=(stocks%20OR%20markets%20OR%20inflation%20OR%20interest%20rates)%20when%3A7d&hl=en&gl=US&ceid=US%3Aen", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(gold%20price%20OR%20oil%20prices%20OR%20dollar%20index)%20when%3A7d&hl=en&gl=US&ceid=US%3Aen", "hint": "finans"},

    # =========================
    # YEREL (YALOVA) – 7 günlük aramalar (birkaç farklı sorgu)
    # =========================
    {"url": "https://news.google.com/rss/search?q=Yalova%20when%3A7d&hl=tr&gl=TR&ceid=TR%3Atr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Yalova%20Belediyesi%20OR%20Yalova%20Valili%C4%9Fi)%20when%3A14d&hl=tr&gl=TR&ceid=TR%3Atr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(%C3%87%C4%B1narc%C4%B1k%20OR%20%C3%87iftlikk%C3%B6y%20OR%20Alt%C4%B1nova%20OR%20Termal%20OR%20Armutlu)%20when%3A14d&hl=tr&gl=TR&ceid=TR%3Atr", "hint": "yerel"},
]

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    out = soup.get_text(" ", strip=True)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def get_domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        return host.replace("www.", "")
    except Exception:
        return ""


def is_foreign(url: str) -> bool:
    d = get_domain(url)
    if not d:
        return True
    return not d.endswith(".tr")


def safe(s: str) -> str:
    return (s or "").strip()


def extract_image(entry) -> str:
    try:
        if "media_content" in entry and entry.media_content:
            u = entry.media_content[0].get("url")
            if u:
                return u
    except Exception:
        pass

    try:
        if "media_thumbnail" in entry and entry.media_thumbnail:
            u = entry.media_thumbnail[0].get("url")
            if u:
                return u
    except Exception:
        pass

    try:
        if "links" in entry:
            for l in entry.links:
                if l.get("rel") == "enclosure" and ("image" in (l.get("type", "") or "")):
                    u = l.get("href")
                    if u:
                        return u
    except Exception:
        pass

    try:
        s = entry.get("summary", "") or ""
        m = re.search(r'<img[^>]+src="([^"]+)"', s, re.IGNORECASE)
        if m:
            return m.group(1)
    except Exception:
        pass

    return ""


# ------------------------------------------------------------
# Translation (defensive)
# ------------------------------------------------------------
_TRANSLATION_CALLS = 0
_TRANSLATION_LIMIT = 120  # biraz artırdım

def translate_to_tr(text: str) -> str:
    global _TRANSLATION_CALLS
    t = safe(text)
    if not t:
        return t
    if _TRANSLATION_CALLS >= _TRANSLATION_LIMIT:
        return t

    _TRANSLATION_CALLS += 1

    # deep-translator varsa
    try:
        from deep_translator import GoogleTranslator  # type: ignore
        return GoogleTranslator(source="auto", target="tr").translate(t[:2500])
    except Exception:
        pass

    # MyMemory fallback
    try:
        q = requests.utils.quote(t[:450])
        url = f"https://api.mymemory.translated.net/get?q={q}&langpair=en|tr"
        r = requests.get(url, timeout=12, headers={"User-Agent": UA})
        data = r.json() if r.ok else {}
        tr = (data.get("responseData", {}) or {}).get("translatedText") or ""
        up = tr.upper()
        if "MYMEMORY WARNING" in up or "YOU USED ALL AVAILABLE FREE TRANSLATIONS" in up:
            return t
        return tr or t
    except Exception:
        return t


# ------------------------------------------------------------
# Categories
# ------------------------------------------------------------
CATEGORY_LABELS = {
    "gundem": "Gündem",
    "dunya": "Dünya",
    "spor": "Spor",
    "teknoloji": "Teknoloji",
    "saglik": "Sağlık",
    "ekonomi": "Ekonomi",
    "finans": "Finans",
    "magazin": "Magazin",
    "bilim": "Bilim",
    "savunma": "Savunma / Askeri",
    "oyun": "Oyun / Dijital",
    "otomobil": "Otomobil",
    "yasam": "Yaşam",
    "yerel": "Yerel",
}

CATEGORY_KEYWORDS = {
    "finans": [
        "borsa", "bist", "hisse", "endeks", "temettü", "temettu", "portföy", "portfoy", "bist30", "bist50", "bist100", "bist banka",
        "dolar", "euro", "kur", "altın", "altin", "faiz", "enflasyon", "tcmb", "fed", "temettü", "temettu", "halka arz"
        "tahvil", "bono", "mevduat", "swap", "kripto", "bitcoin", "ethereum", "emtia",
        "nasdaq", "s&p", "dow jones", "market", "stocks", "markets", "inflation", "rates"
    ],
    "yerel": [
        "yalova", "çınarcık", "cinarcik", "çiftlikköy", "ciftlikkoy", "termal", "yalova merkez"
        "altınova", "altinova", "armutlu", "yalova belediyesi", "yalova valiliği", "yalova valiligi"
    ],
    "spor": ["maç", "mac", "lig", "şampiyona", "gol", "transfer", "derbi", "futbol", "basketbol", "voleybol", "tenis"],
    "teknoloji": ["teknoloji", "yazılım", "yazilim", "android", "ios", "yapay zeka", "ai", "çip", "cip", "işlemci", "islemci", "bilgisayar"],
    "saglik": ["sağlık", "saglik", "hastane", "doktor", "virüs", "virus", "kanser", "tedavi", "aşı", "asi", "grip", "diyet"],
    "ekonomi": ["ekonomi", "ihracat", "ithalat", "bütçe", "butce", "vergi", "asgari", "maaş", "maas", "sanayi", "üretim", "uretim"],
    "magazin": ["magazin", "ünlü", "unlu", "oyuncu", "dizi", "film", "evlilik", "boşanma", "bosanma", "konser"],
    "bilim": ["bilim", "araştırma", "arastirma", "deney", "keşif", "kesif", "nasa", "teleskop", "genetik"],
    "savunma": ["savunma", "ordu", "asker", "füze", "fuze", "tank", "operasyon", "nato", "güvenlik", "guvenlik"],
    "oyun": ["oyun", "playstation", "ps5", "xbox", "nintendo", "steam", "mobil oyun", "espor", "gamer", "valorant"],
    "otomobil": ["otomobil", "araba", "araç", "arac", "tesla", "togg", "trafik", "muayene", "lastik"],
    "yasam": ["yaşam", "yasam", "aile", "çocuk", "cocuk", "alışveriş", "alisveris", "tatil", "seyahat", "yemek", "dekorasyon"],
}

def score_keywords(text: str, cat: str) -> int:
    t = (text or "").lower()
    score = 0
    for k in CATEGORY_KEYWORDS.get(cat, []):
        if k and k.lower() in t:
            score += 1
    return score


def guess_category(title_any: str, summary_any: str, rss_categories: list, hint: str, url: str) -> str:
    text = (safe(title_any) + " " + safe(summary_any)).lower()
    rc = " ".join([safe(x).lower() for x in (rss_categories or []) if safe(x)])

    # 1) YEREL: hint varsa bile sadece Yalova/ilçe kelimeleri geçiyorsa yerel
    if hint == "yerel":
        if score_keywords(text, "yerel") > 0:
            return "yerel"

    # 2) FINANS: hint varsa bile sadece finans anahtarları veya rss kategorileri uygunsa finans
    if hint == "finans":
        if score_keywords(text, "finans") >= 1:
            return "finans"
        if any(k in rc for k in ["business", "finance", "markets", "money", "economy"]):
            # rss gerçekten business/finance ise finans diyebiliriz
            return "finans"
        # aksi halde hint'i zorlamıyoruz (fırtına gibi haberler yanlış finans düşmesin)

    # 3) RSS kategorilerinden eşleme
    if rc:
        if any(k in rc for k in ["finance", "markets", "stock", "stocks", "money"]):
            return "finans"
        if any(k in rc for k in ["business", "economy", "economics"]):
            return "ekonomi"
        if "sport" in rc:
            return "spor"
        if any(k in rc for k in ["technology", "tech"]):
            return "teknoloji"
        if any(k in rc for k in ["health", "medical", "medicine"]):
            return "saglik"
        if any(k in rc for k in ["science", "environment"]):
            return "bilim"

    # 4) Keyword scoring (yerel/finans dahil)
    scores = {}
    for cat in CATEGORY_KEYWORDS.keys():
        scores[cat] = score_keywords(text, cat)

    # yerel öncelik
    if scores.get("yerel", 0) > 0:
        return "yerel"

    # finans vs ekonomi çakışması: finans kelimeleri varsa finans
    fin = scores.get("finans", 0)
    eco = scores.get("ekonomi", 0)

    best_cat = max(scores.items(), key=lambda x: x[1])[0]
    best_score = scores.get(best_cat, 0)

    if best_score > 0:
        if eco > 0 and fin > 0 and fin >= eco:
            return "finans"
        return best_cat

    # 5) fallback
    return "dunya" if is_foreign(url) else "gundem"


# ------------------------------------------------------------
# Modal content generation (Uzun Özet GERÇEKTEN uzun)
# Hukuki risk için: tam metin çekmiyoruz; title+summary üzerinden "analitik" uzun metin üretiyoruz.
# ------------------------------------------------------------
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

def pick_sentences(text: str, max_sent: int = 10) -> list:
    t = clean_html(text)
    if not t:
        return []
    parts = [p.strip() for p in SENT_SPLIT.split(t) if p.strip()]
    out = []
    for p in parts:
        if len(p) < 25:
            continue
        if len(p) > 320:
            p = p[:320].rsplit(" ", 1)[0] + "…"
        out.append(p)
        if len(out) >= max_sent:
            break
    return out


def extract_numbers(text: str) -> list:
    # 7 milyon, 6.5, 2025, 17 years vb
    nums = re.findall(r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\b", text or "")
    # benzersiz
    out = []
    for n in nums:
        if n not in out:
            out.append(n)
    return out[:6]


def extract_locations_like(text: str) -> list:
    # basit: büyük harfle başlayan kelimelerden (TR/EN) “olası yer” çıkarımı
    # (mükemmel değil; ama uzun özete “somutluk” katıyor)
    words = re.findall(r"\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\b", text or "")
    blacklist = {"Bu", "Bir", "İçin", "Kaynak", "Finans", "Yerel", "Dünya", "Gündem"}
    out = []
    for w in words:
        if w in blacklist:
            continue
        if w not in out:
            out.append(w)
        if len(out) >= 6:
            break
    return out


def build_long_summary_tr(title_tr: str, summary_tr: str, category: str, source: str, url: str) -> str:
    title_tr = safe(title_tr)
    summary_tr = safe(summary_tr)

    base_sents = pick_sentences(summary_tr, max_sent=8)
    nums = extract_numbers(summary_tr)
    locs = extract_locations_like(title_tr + " " + summary_tr)

    cat_label = CATEGORY_LABELS.get(category, "Genel")
    origin = "Türkiye kaynağı" if not is_foreign(url) else "Uluslararası kaynak"

    # 1) Giriş
    intro = (
        f"Bu içerik, {cat_label} kategorisinde derlenmiş bir haber özetidir ({origin}, Kaynak: {source}).\n"
        f"Başlık: {title_tr}"
    )

    # 2) Ne oldu? (summary cümleleri)
    if base_sents:
        happened = " ".join(base_sents[:3])
    else:
        happened = summary_tr or "Bu haber için kısa özet mevcut değil."

    # 3) Detaylar / bağlam (kısmen şablon + sayılar/yerler)
    detail_bits = []
    if locs:
        detail_bits.append("Öne çıkan yer/başlıklar: " + ", ".join(locs) + ".")
    if nums:
        detail_bits.append("Haberde geçen sayısal veriler: " + ", ".join(nums) + ".")
    if category == "finans":
        detail_bits.append("Finans haberlerinde benzer gelişmeler genellikle veri akışı, politika kararları ve küresel risk iştahıyla birlikte fiyatlanır.")
        detail_bits.append("Bu nedenle kısa vadeli hareketler görülebilir; karar için kaynak detayını kontrol etmek önemlidir.")
    elif category == "yerel":
        detail_bits.append("Yerel gelişmelerde resmi kurum açıklamaları (belediye/valilik) ve saha güncellemeleri takip edilmelidir.")
        detail_bits.append("Etkiler; hizmetler, ulaşım, etkinlikler veya yerel gündem başlıklarında daha netleşebilir.")
    else:
        detail_bits.append("Gelişme yeni ayrıntılarla güncellenebilir; resmi açıklamalar ve kaynak detayları izlenmelidir.")

    details = " ".join(detail_bits)

    # 4) “Ne izlenmeli?” bölümü (ziyaretçiyi sitede tutacak şekilde, ama telifsiz)
    watch = []
    if category == "finans":
        watch.append("İzlenecek başlıklar: piyasa tepkisi, ilgili kurum açıklamaları, yeni veri/karar akışı ve olası ikinci etkiler.")
    elif category == "yerel":
        watch.append("İzlenecek başlıklar: yerel kurum duyuruları, sahadan yeni görüntü/raporlar, hizmet/ulaşım güncellemeleri.")
    else:
        watch.append("İzlenecek başlıklar: resmi teyitler, gelişmenin zaman çizelgesi ve ek açıklamalar.")

    watch_text = " ".join(watch)

    # Uzun özet formatı: 3–4 paragraf
    long_text = (
        f"{intro}\n\n"
        f"Ne oldu?\n{happened}\n\n"
        f"Detaylar ve bağlam:\n{details}\n\n"
        f"Ne izlenmeli?\n{watch_text}"
    )

    # Çok uzarsa kırp (UI için)
    if len(long_text) > 1400:
        long_text = long_text[:1400].rsplit(" ", 1)[0] + "…"

    return long_text


def make_why_important_tr(title_tr: str, summary_tr: str, category: str) -> list:
    t = (safe(title_tr) + " " + safe(summary_tr)).lower()
    bullets = []

    if category == "finans":
        bullets.append("Piyasa fiyatlamaları (kur/altın/borsa/faiz) üzerinde kısa vadeli dalgalanma yaratabilir.")
        bullets.append("Yatırımcı beklentilerini etkileyebilecek yeni veri/karar/söylem içerebilir.")
        bullets.append("İlgili sektör/şirketler için risk ve fırsat dengesi değişebilir.")
    elif category == "yerel":
        bullets.append("Yalova ve çevresinde günlük yaşamı etkileyebilecek bir gelişmeyi işaret ediyor.")
        bullets.append("Yerel kurumların alacağı kararlar ve uygulamalar açısından önem taşıyabilir.")
        bullets.append("Kamu hizmetleri/ulaşım/etkinlikler gibi başlıklarda yeni güncellemeler doğurabilir.")
    elif category == "saglik":
        bullets.append("Kamu sağlığı, riskler veya tedavi süreçleri açısından doğrudan etki doğurabilir.")
        bullets.append("Yeni uyarılar/öneriler veya kısıtlar gündeme gelebilir.")
    elif category == "teknoloji":
        bullets.append("Kullanıcı güvenliği ve maliyetler üzerinde etkisi olabilecek yeni bir gelişmeye işaret ediyor.")
        bullets.append("Ürün/hizmet değişiklikleri veya düzenleme etkileri görülebilir.")
    else:
        bullets.append("Gündemi etkileyebilecek yeni bir bilgi veya gelişme içeriyor.")
        bullets.append("Kısa vadede kamuoyu ve karar vericiler üzerinde etkisi olabilir.")

    # sayısal veri varsa ek vurgu
    if re.search(r"\b\d{1,3}([.,]\d{3})*\b", summary_tr):
        bullets.insert(0, "Haberde yer alan sayısal veriler, gelişmenin ölçeğini ve olası etkisini anlamayı kolaylaştırır.")

    # benzersiz ve kısa tut
    out = []
    for b in bullets:
        if b not in out:
            out.append(b)
    return out[:4]


def make_background_tr(summary_tr: str, category: str) -> list:
    sents = pick_sentences(summary_tr, max_sent=10)
    out = sents[:3] if sents else ["—"]

    if category == "finans":
        out.append("Benzer haberler genellikle veri takvimi (enflasyon/faiz), küresel risk iştahı ve şirket bilançolarıyla birlikte değerlendirilir.")
    if category == "yerel":
        out.append("Yerel gelişmelerde resmi duyurular, belediye/valilik açıklamaları ve sahadan teyitler kritik önemdedir.")
    return out[:5]


def make_impacts_tr(summary_tr: str, category: str) -> list:
    t = safe(summary_tr)
    if not t:
        return ["—"]

    bullets = []
    impact_sents = []
    for s in pick_sentences(t, max_sent=12):
        low = s.lower()
        if any(k in low for k in ["beklen", "öngör", "planlan", "etkile", "yol aç", "risk", "olabilir", "muhtemel"]):
            impact_sents.append(s)
        if len(impact_sents) >= 3:
            break

    bullets.extend(impact_sents[:3])

    if category == "finans":
        bullets.append("Yeni haber akışı devam ederse, fiyatlar kısa süreli “haber bazlı” tepkiler verebilir; kaynak detayını doğrulamak gerekir.")
    elif category == "yerel":
        bullets.append("Gelişmenin seyrine göre yerel hizmetler/ulaşım/etkinlikler gibi alanlarda güncellemeler görülebilir.")
    else:
        bullets.append("Gelişme yeni ayrıntılarla güncellenebilir; resmi açıklamalar ve kaynak detayları takip edilmelidir.")

    out = []
    for b in bullets:
        bb = safe(b)
        if bb and bb not in out:
            out.append(bb)
    return out[:5]


# ------------------------------------------------------------
def fetch_feed(url: str):
    r = requests.get(url, timeout=20, headers={"User-Agent": UA})
    r.raise_for_status()
    return feedparser.parse(r.content)


def main():
    seen = set()
    articles = []

    for src in RSS_SOURCES:
        url = src["url"]
        hint = src.get("hint", "gundem")

        try:
            feed = fetch_feed(url)
            entries = feed.entries[:MAX_ITEMS_PER_SOURCE]

            for e in entries:
                link = safe(e.get("link"))
                if not link:
                    continue
                if link in seen:
                    continue
                seen.add(link)

                title = safe(e.get("title"))
                summary = clean_html(e.get("summary", "") or e.get("description", "") or "")

                if not title:
                    continue

                domain = get_domain(link) or "kaynak"

                rss_cats = []
                try:
                    if "tags" in e and e.tags:
                        rss_cats = [safe(t.get("term", "")).lower() for t in e.tags if safe(t.get("term", ""))]
                except Exception:
                    rss_cats = []

                img = extract_image(e)

                # Çeviri: yabancıysa TR'ye çevir
                if is_foreign(link):
                    title_tr = translate_to_tr(title)
                    summary_tr = translate_to_tr(summary)
                else:
                    title_tr = title
                    summary_tr = summary

                category = guess_category(title_tr or title, summary_tr or summary, rss_cats, hint, link)

                long_tr = build_long_summary_tr(title_tr, summary_tr, category, domain, link)
                why = make_why_important_tr(title_tr, summary_tr, category)
                bg = make_background_tr(summary_tr, category)
                impacts = make_impacts_tr(summary_tr, category)

                articles.append({
                    "title": title,
                    "summary": summary,
                    "title_tr": title_tr,
                    "summary_tr": summary_tr,

                    "summary_tr_long": long_tr,
                    "why_important": why,
                    "background": bg,
                    "possible_impacts": impacts,

                    "image": img,
                    "url": link,
                    "source": domain,
                    "rss_categories": rss_cats,
                    "category": category,
                })

                if len(articles) >= TOTAL_LIMIT:
                    break

        except Exception as ex:
            print("RSS hata:", url, ex)

        if len(articles) >= TOTAL_LIMIT:
            break

    now_tr = datetime.now(TR_TZ).replace(microsecond=0)
    out = {
        "generated_at": now_tr.isoformat(),
        "articles": articles
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("Yazıldı:", OUT_PATH, "Toplam:", len(articles))


if __name__ == "__main__":
    main()
