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

TR_TZ = timezone(timedelta(hours=3))  # Europe/Istanbul sabit +03:00

# ------------------------------------------------------------
# RSS Sources
# Not: RSS listesi "kaynakları arttırmak" için en güvenli yer burası.
# Finans ve Yerel (Yalova) için Google News RSS araması ekliyoruz (stabil ve geniş kapsama).
# ------------------------------------------------------------
RSS_SOURCES = [
    # --- BBC ---
    {"url": "https://feeds.bbci.co.uk/news/rss.xml", "hint": "dunya"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "hint": "dunya"},
    {"url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "hint": "teknoloji"},
    {"url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "hint": "bilim"},
    {"url": "https://feeds.bbci.co.uk/news/health/rss.xml", "hint": "saglik"},
    {"url": "https://feeds.bbci.co.uk/news/business/rss.xml", "hint": "finans"},

    # --- TR genel (mevcutlarınızla uyumlu) ---
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

    # --- Google News RSS (Finans TR) ---
    # Son 7 gün; borsa/dolar/altın/faiz odaklı
    {"url": "https://news.google.com/rss/search?q=(borsa%20OR%20dolar%20OR%20alt%C4%B1n%20OR%20faiz)%20when%3A7d&hl=tr&gl=TR&ceid=TR%3Atr", "hint": "finans"},

    # --- Google News RSS (Yerel: Yalova) ---
    # Yalova + ilçeler (isteğe göre genişletebilirsiniz)
    {"url": "https://news.google.com/rss/search?q=(Yalova%20OR%20%C3%87%C4%B1narc%C4%B1k%20OR%20Termal%20OR%20Alt%C4%B1nova%20OR%20Armutlu)%20when%3A7d&hl=tr&gl=TR&ceid=TR%3Atr", "hint": "yerel"},
]

MAX_ITEMS_PER_SOURCE = 18
TOTAL_LIMIT = 240

UA = "Mozilla/5.0 (compatible; HaberRobotuBot/1.0; +https://newest-resu.github.io/)"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def clean_html(text: str) -> str:
    if not text:
        return ""
    # feedparser summary bazen HTML gelir
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


def extract_image(entry) -> str:
    # feedparser entry: media_content, media_thumbnail, links(enclosure)
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
                if l.get("rel") == "enclosure" and (l.get("type", "").startswith("image") or "image" in l.get("type", "")):
                    u = l.get("href")
                    if u:
                        return u
    except Exception:
        pass

    # summary içinden img src çekmeyi dener (bazı RSS’ler)
    try:
        s = entry.get("summary", "") or ""
        m = re.search(r'<img[^>]+src="([^"]+)"', s, re.IGNORECASE)
        if m:
            return m.group(1)
    except Exception:
        pass

    return ""


def safe(s: str) -> str:
    return (s or "").strip()


# ------------------------------------------------------------
# Translation (lightweight, defensive)
# ------------------------------------------------------------
_TRANSLATION_CALLS = 0
_TRANSLATION_LIMIT = 80  # bir çalışmada

def translate_en_to_tr(text: str) -> str:
    """
    1) deep-translator varsa kullanmayı dener (GH'de bazen daha stabil).
    2) olmazsa MyMemory ile dener (rate-limit olabilir).
    3) olmazsa orijinal döner.
    """
    global _TRANSLATION_CALLS
    t = safe(text)
    if not t:
        return t
    if _TRANSLATION_CALLS >= _TRANSLATION_LIMIT:
        return t

    _TRANSLATION_CALLS += 1

    # 1) deep-translator
    try:
        from deep_translator import GoogleTranslator  # type: ignore
        return GoogleTranslator(source="auto", target="tr").translate(t[:2500])
    except Exception:
        pass

    # 2) MyMemory fallback (kısa tut)
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
# Category classification (Finans + Yerel eklendi)
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
        "borsa", "bist", "hisse", "hisseleri", "endeks", "dolar", "euro", "altın", "altin",
        "kripto", "bitcoin", "ethereum", "faiz", "tahvil", "bono", "swap", "kur",
        "bankacılık", "bankacilik", "temettü", "temettu", "portföy", "portfoy",
        "fed", "tcmb", "merkez bank", "enflasyon", "piyasa", "futures", "emtia"
    ],
    "yerel": [
        "yalova", "çınarcık", "cinarcik", "termal", "altınova", "altinova", "armutlu",
        "çiftlikköy", "ciftlikkoy", "kocaeli", "bursa", "marmara"
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
    "dunya": ["world", "international", "global", "europe", "middle east", "asia", "africa", "us", "canada", "politic"],
    "gundem": ["türkiye", "turkiye", "gündem", "gundem", "yerel", "son dakika"],
}

def guess_category(title_any: str, summary_any: str, rss_categories: list, hint: str, url: str) -> str:
    # 1) hint (source bazlı)
    if hint in CATEGORY_LABELS:
        # yerel/finans gibi özel hintleri güçlü tut
        if hint in ("yerel", "finans"):
            return hint

    # 2) rss categories
    rc = " ".join([safe(x).lower() for x in (rss_categories or []) if safe(x)])
    if rc:
        # rss'de finance/business geçiyorsa finansı öne al
        if any(k in rc for k in ["finance", "markets", "stock", "stocks", "bist", "borsa"]):
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

    # 3) keyword scoring
    text = (safe(title_any) + " " + safe(summary_any)).lower()

    # Yerel: yalova yakalarsa direkt yerel
    if any(k in text for k in CATEGORY_KEYWORDS["yerel"]):
        return "yerel"

    scores = {}
    for cat, kws in CATEGORY_KEYWORDS.items():
        if cat in ("yerel",):
            continue
        score = 0
        for k in kws:
            if k and k in text:
                score += 1
        scores[cat] = score

    best = max(scores.items(), key=lambda x: x[1])[0] if scores else ""
    if scores.get(best, 0) > 0:
        # finance ve economy çakışırsa; piyasaya dönük kelimeler varsa finans
        if best == "ekonomi" and any(k in text for k in CATEGORY_KEYWORDS["finans"]):
            return "finans"
        return best

    # fallback: foreign -> dünya, tr -> gündem
    return "dunya" if is_foreign(url) else "gundem"


# ------------------------------------------------------------
# Modal content generation (telif riskini azaltan, tutarlı üretim)
# ------------------------------------------------------------
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

def pick_sentences(text: str, max_sent: int = 6) -> list:
    t = clean_html(text)
    if not t:
        return []
    parts = [p.strip() for p in SENT_SPLIT.split(t) if p.strip()]
    # çok kısa/çok uzun parçaları filtrele
    out = []
    for p in parts:
        if len(p) < 30:
            continue
        if len(p) > 320:
            p = p[:320].rsplit(" ", 1)[0] + "…"
        out.append(p)
        if len(out) >= max_sent:
            break
    return out


def build_long_summary_tr(title_tr: str, summary_tr: str, category: str, source: str) -> str:
    # Tam metin değil; özetin üstüne tutarlı bir giriş + özet cümleleri.
    sents = pick_sentences(summary_tr, max_sent=5)
    if not sents:
        base = safe(summary_tr) or "Bu haber için kısa özet mevcut değil."
        sents = [base[:240] + ("…" if len(base) > 240 else "")]
    intro = f"Bu içerik, {CATEGORY_LABELS.get(category, 'Genel')} kategorisinde derlenmiş bir haber özetidir (Kaynak: {source})."
    body = " ".join(sents)
    # aşırı tekrarları azalt
    body = re.sub(r"\s+", " ", body).strip()
    return intro + "\n\n" + body


def make_why_important_tr(title_tr: str, summary_tr: str, category: str) -> list:
    t = (safe(title_tr) + " " + safe(summary_tr)).lower()
    bullets = []

    # kategori bazlı “mantıklı” kalıplar
    if category == "finans":
        bullets.append("Piyasa fiyatlamaları (kur/altın/borsa/faiz) üzerinde kısa vadeli dalgalanma yaratabilir.")
        bullets.append("Yatırımcı beklentilerini etkileyebilecek yeni veri/karar/söylem içerebilir.")
    elif category == "yerel":
        bullets.append("Yalova ve çevresinde günlük yaşamı ve yerel kararları etkileyebilecek bir gelişmeyi işaret ediyor.")
        bullets.append("Yerel kurumların atacağı adımlar veya kamu hizmetleri açısından önem taşıyabilir.")
    elif category == "saglik":
        bullets.append("Kamu sağlığı, riskler veya tedavi süreçleri açısından doğrudan etki doğurabilir.")
    elif category == "teknoloji":
        bullets.append("Yeni ürün/hizmet veya düzenleme, kullanıcılar ve şirketler için maliyet ve güvenlik etkileri doğurabilir.")
    elif category == "spor":
        bullets.append("Takım/lig dinamiklerini ve yaklaşan karşılaşmaların dengelerini etkileyebilir.")
    else:
        bullets.append("Gündemi etkileyebilecek yeni bir bilgi veya gelişme içeriyor.")
        bullets.append("Kısa vadede kamuoyu ve karar vericiler üzerinde etkisi olabilir.")

    # metinden ekstra bir “somutluk” yakala: sayı/para/tarih
    if re.search(r"\b\d{1,3}([.,]\d{3})*\b", summary_tr):
        bullets.insert(0, "Haberde yer alan sayısal veriler, gelişmenin ölçeğini ve olası etkisini anlamayı kolaylaştırıyor.")

    return bullets[:3]


def make_background_tr(summary_tr: str, category: str) -> list:
    sents = pick_sentences(summary_tr, max_sent=6)
    if not sents:
        return ["—"]
    # “arka plan” için ilk 2-3 cümle
    out = sents[:3]
    if category == "finans":
        out.append("Finansal haberlerde benzer başlıklar genellikle veri akışı, politika kararları ve küresel risk iştahıyla birlikte fiyatlanır.")
    if category == "yerel":
        out.append("Yerel gelişmeler, belediye/valilik kararları ve bölgesel altyapı–hizmet süreçleriyle birlikte değerlendirilmelidir.")
    return out[:4]


def make_impacts_tr(summary_tr: str, category: str) -> list:
    t = safe(summary_tr)
    if not t:
        return ["—"]

    bullets = []
    # özet içinden “bekleniyor/olabilir/planlanıyor” gibi ifadeleri yakala
    impact_sents = []
    for s in pick_sentences(t, max_sent=10):
        low = s.lower()
        if any(k in low for k in ["beklen", "öngör", "planlan", "etkile", "yol aç", "yol ac", "risk", "olabilir", "muhtemel"]):
            impact_sents.append(s)
        if len(impact_sents) >= 2:
            break

    if impact_sents:
        bullets.extend(impact_sents[:2])

    # kategori bazlı ek
    if category == "finans":
        bullets.append("Yeni haber akışı devam ederse, fiyatlar kısa süreli “haber bazlı” tepkiler verebilir; karar için kaynağa gidip detay doğrulaması yapılmalıdır.")
    elif category == "yerel":
        bullets.append("Gelişmenin seyrine göre yerel hizmetler/ulaşım/etkinlikler gibi alanlarda güncellemeler görülebilir.")
    else:
        bullets.append("Gelişme yeni ayrıntılarla güncellenebilir; resmi açıklamalar ve kaynak detayları takip edilmelidir.")

    # temizle
    out = []
    for b in bullets:
        bb = safe(b)
        if bb and bb not in out:
            out.append(bb)
    return out[:3]


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

                # ham alanlar
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

                # TR/EN ayır
                if is_foreign(link):
                    title_tr = translate_en_to_tr(title)
                    summary_tr = translate_en_to_tr(summary)
                else:
                    title_tr = title
                    summary_tr = summary

                category = guess_category(title_tr or title, summary_tr or summary, rss_cats, hint, link)

                # Modal alanları (TR üret)
                long_tr = build_long_summary_tr(title_tr, summary_tr, category, domain)
                why = make_why_important_tr(title_tr, summary_tr, category)
                bg = make_background_tr(summary_tr, category)
                impacts = make_impacts_tr(summary_tr, category)

                articles.append({
                    "title": title,
                    "summary": summary,
                    "title_tr": title_tr,
                    "summary_tr": summary_tr,

                    # modal alanları
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

    # generated_at: ISO +03:00
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
