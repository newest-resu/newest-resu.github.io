# scripts/build_latest.py
import os
import re
import json
import time
import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin

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
REQUEST_TIMEOUT = 20
SLEEP_BETWEEN_FETCH = float(os.getenv("SLEEP_BETWEEN_FETCH", "0.2"))  # nazik crawling

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

    # Finans kategorisini şimdiden destekliyoruz (RSS eklemelerini sonraki adımda genişletiriz)
    # {"name": "XXXX", "url": "https://....rss", "category": "Finans"},
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
    s = (s or "")
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = s.strip()
    return s

def strip_html(html: str) -> str:
    if not html:
        return ""
    return clean_text(BeautifulSoup(html, "lxml").get_text(" "))

def tr(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    try:
        return translator.translate(text)
    except Exception:
        # çeviri fail olursa en azından boş dönmeyelim
        return text

def safe_get(url: str) -> str:
    r = SESSION.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    return r.text

def extract_main_text(html: str) -> str:
    """
    Readability ile ana metni çıkarır.
    """
    doc = Document(html)
    main_html = doc.summary(html_partial=True)
    soup = BeautifulSoup(main_html, "lxml")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    text = soup.get_text("\n")
    return clean_text(text)

def split_sentences(text: str):
    """
    TR/EN için yeterli basit cümle bölme.
    """
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 45:
            out.append(p)
    return out

def score_sentence(s: str) -> float:
    """
    Basit önem skorlaması: sayı/kurum/uzunluk + bazı işaretler.
    """
    score = 0.0
    if re.search(r"\d", s):
        score += 2.5
    if re.search(r"\b[A-ZÇĞİÖŞÜ]{2,}\b", s):  # kısaltma
        score += 1.2
    if re.search(r"\b[A-Z][a-zçğıöşü]+\b", s):  # özel isim kalıbı
        score += 0.8
    if re.search(r"\b(announced|said|reports|according to|confirmed|warning|increase|decrease)\b", s, re.I):
        score += 0.7
    score += min(len(s) / 140.0, 2.5)
    return score

def extractive_summary(text: str, max_words: int):
    sents = split_sentences(text)
    if not sents:
        return ""

    scored = sorted([(score_sentence(s), i, s) for i, s in enumerate(sents)], reverse=True)
    chosen = []
    total = 0

    for _, _, s in scored:
        w = len(s.split())
        if total + w > max_words:
            continue
        chosen.append(s)
        total += w
        if total >= max_words * 0.92:
            break

    if not chosen:
        chosen = sents[:6]

    # Orijinal sıralama
    chosen_sorted = sorted(chosen, key=lambda x: sents.index(x))
    return " ".join(chosen_sorted).strip()

def cut_at_sentence_boundary(text: str, max_chars: int = 360) -> str:
    """
    UI için kısa özet: cümle sınırında kes.
    """
    t = clean_text(text)
    if len(t) <= max_chars:
        return t
    # max_chars yakınında son noktalama
    cut = t[:max_chars]
    m = re.search(r"[.!?]\s", cut[::-1])
    if m:
        # ters aramada bulunan noktalama konumunu hesapla
        idx_from_end = m.start()
        final_len = max_chars - idx_from_end
        return t[:final_len].strip()
    return (cut.rstrip() + "…").strip()

# =========================
# GÖRSEL BULMA (RSS + HTML META FALLBACK)
# =========================
def pick_image_from_feed_entry(entry) -> str:
    # media:content
    if getattr(entry, "media_content", None):
        for m in entry.media_content:
            u = (m.get("url") or "").strip()
            if u:
                return u

    # media:thumbnail
    if getattr(entry, "media_thumbnail", None):
        for m in entry.media_thumbnail:
            u = (m.get("url") or "").strip()
            if u:
                return u

    # enclosure links (feedparser)
    if getattr(entry, "links", None):
        for l in entry.links:
            href = (l.get("href") or "").strip()
            ltype = (l.get("type") or "").lower()
            rel = (l.get("rel") or "").lower()
            # image/*
            if href and ltype.startswith("image/"):
                return href
            # enclosure bazen image verir
            if href and rel == "enclosure" and ("image" in ltype):
                return href

    # entry.enclosures
    if getattr(entry, "enclosures", None):
        for e in entry.enclosures:
            href = (getattr(e, "href", "") or "").strip()
            etype = (getattr(e, "type", "") or "").lower()
            if href and etype.startswith("image/"):
                return href

    return ""

def pick_image_from_html(url: str, html: str) -> str:
    """
    og:image / twitter:image / link rel=image_src fallback
    """
    try:
        soup = BeautifulSoup(html, "lxml")

        def meta(prop_name):
            tag = soup.find("meta", attrs={"property": prop_name})
            if tag and tag.get("content"):
                return tag["content"].strip()
            return ""

        def meta_name(name):
            tag = soup.find("meta", attrs={"name": name})
            if tag and tag.get("content"):
                return tag["content"].strip()
            return ""

        candidates = [
            meta("og:image"),
            meta("og:image:url"),
            meta_name("twitter:image"),
            meta_name("twitter:image:src"),
        ]
        candidates = [c for c in candidates if c]

        # link rel=image_src
        link = soup.find("link", attrs={"rel": "image_src"})
        if link and link.get("href"):
            candidates.append(link["href"].strip())

        for c in candidates:
            # relatifse absolute yap
            if c.startswith("//"):
                c = "https:" + c
            if c.startswith("/"):
                c = urljoin(url, c)
            if c:
                return c
    except Exception:
        pass
    return ""

# =========================
# KATMA DEĞER ÜRETİMİ (Modal Alanları)
# =========================
CATEGORY_TEMPLATES = {
    "Ekonomi": {
        "why": [
            "Piyasalar, fiyatlar ve beklentiler üzerinde kısa vadeli etkiler doğurabilir.",
            "Hanehalkı ve işletmelerin kararlarını (harcama, yatırım, borçlanma) etkileyebilir.",
        ],
        "bg": [
            "Son dönemde açıklanan veriler ve politika adımları ekonomi gündemini şekillendiriyor.",
            "Benzer gelişmeler geçmişte piyasalarda dalgalanmalar yaratmıştı.",
        ],
        "imp": [
            "Kısa vadede volatilite artabilir; orta vadede politika/strateji değişiklikleri görülebilir.",
            "Faiz, kur, enflasyon ve sektör performanslarına yansıması izlenecek.",
        ],
    },
    "Finans": {
        "why": [
            "Finansal piyasalar ve yatırım kararları açısından yakından izlenmesi gereken bir gelişme.",
            "Risk iştahı, fon akışları ve varlık fiyatlamaları üzerinde etkili olabilir.",
        ],
        "bg": [
            "Finans gündeminde son dönemde volatilite ve likidite koşulları belirleyici oluyor.",
            "Regülasyonlar ve küresel gelişmeler finansal kanallar üzerinden yansıyabiliyor.",
        ],
        "imp": [
            "Varlık fiyatlamaları ve portföy dağılımlarında kısa vadeli ayarlamalar görülebilir.",
            "Banka/finans kuruluşlarının stratejileri ve kredi koşulları etkilenebilir.",
        ],
    },
    "Teknoloji": {
        "why": [
            "Sektörün yönünü belirleyen ürün/şirket/regülasyon gelişmeleri kullanıcı davranışlarını etkileyebilir.",
            "Rekabet dengeleri ve teknoloji yatırımları üzerinde etkileri olabilir.",
        ],
        "bg": [
            "Teknoloji sektöründe ürün döngüleri ve regülasyon gündemi hızlı değişiyor.",
            "Şirketler rekabet avantajı için Ar-Ge ve altyapı yatırımlarını artırıyor.",
        ],
        "imp": [
            "Yeni ürün/hizmetlerin yayılımı hızlanabilir; kullanıcı alışkanlıkları değişebilir.",
            "Sektörde birleşme/rekabet ve fiyatlama dinamikleri etkilenebilir.",
        ],
    },
    "Dünya": {
        "why": [
            "Bölgesel gelişmeler küresel ekonomi ve güvenlik dengeleri üzerinde etkiler yaratabilir.",
            "Diplomatik adımların seyri, risk algısı ve piyasalar için kritik olabilir.",
        ],
        "bg": [
            "Bölgesel gerilimler ve diplomatik süreçler uzun süredir uluslararası gündemde.",
            "Taraflar arasında süregelen anlaşmazlıklar çözüm arayışını şekillendiriyor.",
        ],
        "imp": [
            "Diplomatik ilişkilerde yeni adımlar veya yaptırımlar gündeme gelebilir.",
            "Enerji, ticaret ve güvenlik hatları üzerinden ikincil etkiler görülebilir.",
        ],
    },
    "Gündem": {
        "why": [
            "Kamuoyunun doğrudan etkilendiği bir başlık; sosyal ve siyasi tartışmaları tetikleyebilir.",
            "Kurumların alacağı kararlar günlük yaşamı ve yerel dinamikleri etkileyebilir.",
        ],
        "bg": [
            "Konuya ilişkin gelişmeler daha önce de gündeme gelmiş ve farklı görüşler oluşmuştu.",
            "Karar süreçleri çoğu zaman birden fazla kurum/aktörün etkisiyle şekilleniyor.",
        ],
        "imp": [
            "Kısa vadede tartışmaların yoğunlaşması; orta vadede düzenleme/uygulama değişiklikleri görülebilir.",
            "Kamu politikaları ve sosyal etkiler zaman içinde netleşebilir.",
        ],
    },
    "Spor": {
        "why": [
            "Lig dengeleri, kulüp stratejileri ve taraftar gündemi üzerinde etkili olabilir.",
            "Transfer/sonuç/ceza gibi unsurlar sezonun gidişatını değiştirebilir.",
        ],
        "bg": [
            "Takımların form grafiği ve kadro planlaması sezon içinde dalgalanabiliyor.",
            "Benzer kararlar geçmişte lig dinamiklerini etkilemişti.",
        ],
        "imp": [
            "Kısa vadede kadro ve maç planlamasında değişiklikler görülebilir.",
            "Sezon hedefleri ve ekonomik etkiler (gelir, sponsorluk) etkilenebilir.",
        ],
    },
    "Sağlık": {
        "why": [
            "Toplum sağlığı ve sağlık sisteminin işleyişi açısından önem taşıyabilir.",
            "Koruyucu önlemler ve bilgilendirme ihtiyacını artırabilir.",
        ],
        "bg": [
            "Sağlık gündeminde risk değerlendirmeleri ve önleyici tedbirler belirleyici oluyor.",
            "Bilimsel veriler ve resmi açıklamalar süreç yönetimini etkiler.",
        ],
        "imp": [
            "Yeni önlemler, rehber güncellemeleri veya uygulama değişiklikleri gündeme gelebilir.",
            "Kamuoyunun davranışları ve sağlık hizmeti talebi etkilenebilir.",
        ],
    },
}

def pick_evidence_sentences(content: str, k: int = 2) -> list[str]:
    """
    Habere özgü, tekrar hissi vermeyen 1-2 “kanıt cümle” seç.
    """
    sents = split_sentences(content)
    if not sents:
        return []
    scored = sorted([(score_sentence(s), s) for s in sents], reverse=True)
    out = []
    for _, s in scored:
        s = clean_text(s)
        # çok genel cümleleri ele
        if len(s.split()) < 8:
            continue
        if any(s.lower().startswith(p) for p in ["click", "read more", "advert", "sign up"]):
            continue
        # benzerlik (basit)
        if any(s[:60] == x[:60] for x in out):
            continue
        out.append(s)
        if len(out) >= k:
            break
    return out

def extract_markers(content: str) -> list[str]:
    """
    Habere özgü ‘işaretler’: sayılar, para birimleri, tarih/kurum parçaları.
    """
    text = clean_text(content)
    markers = []

    # para/sayı
    nums = re.findall(r"\b\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d+)?\b", text)
    nums = nums[:6]
    if nums:
        markers.append("Öne çıkan sayılar/veriler: " + ", ".join(nums))

    # para birimi/finans işaretleri
    if re.search(r"\b(USD|EUR|GBP|TRY|TL|dolar|euro|sterlin|faiz|enflasyon|borsa)\b", text, re.I):
        markers.append("Finansal göstergeler/piyasa bağlantısı içeriyor.")

    # kurum/ülke (çok kaba)
    orgs = re.findall(r"\b[A-Z][a-zA-ZÇĞİÖŞÜçğıöşü]{2,}\b", text)
    orgs = [o for o in orgs if o.lower() not in ["the", "and", "for", "with"]]
    orgs = orgs[:8]
    if orgs:
        markers.append("Haberde geçen başlıca aktörler: " + ", ".join(orgs))

    return markers[:3]

def build_modal_sections(category: str, content: str) -> tuple[list[str], list[str], list[str]]:
    """
    why_important / background / possible_impacts alanlarını üretir:
    - Kategori şablonu
    - Habere özgü “kanıt cümle” ve işaretler
    """
    cat = category or "Gündem"
    tpl = CATEGORY_TEMPLATES.get(cat, CATEGORY_TEMPLATES["Gündem"])

    evidence = pick_evidence_sentences(content, k=2)
    markers = extract_markers(content)

    # Kanıt cümleleri TR'ye çevir
    ev_tr = [tr(s) for s in evidence if s]

    why = list(tpl["why"])
    bg = list(tpl["bg"])
    imp = list(tpl["imp"])

    # Habere özgü satır ekle
    if ev_tr:
        why.append("Haberde öne çıkan nokta: " + ev_tr[0])
    if len(ev_tr) > 1:
        bg.append("Bağlamı güçlendiren detay: " + ev_tr[1])

    if markers:
        imp.extend(markers)

    # Çok uzayanları kısalt
    def clamp(lines: list[str], max_lines: int = 4) -> list[str]:
        out = []
        for x in lines:
            x = clean_text(x)
            if not x:
                continue
            if len(x) > 220:
                x = x[:217].rstrip() + "…"
            out.append(x)
            if len(out) >= max_lines:
                break
        return out

    return clamp(why, 4), clamp(bg, 4), clamp(imp, 4)

# =========================
# ANA AKIŞ
# =========================
def main():
    raw_items = []

    for src in RSS_SOURCES:
        feed = feedparser.parse(src["url"])
        entries = getattr(feed, "entries", [])[: MAX_ARTICLES * 2]

        for e in entries:
            url = (getattr(e, "link", "") or "").strip()
            if not url:
                continue

            title = clean_text(getattr(e, "title", "") or "")
            summary_html = getattr(e, "summary", "") or ""
            summary = clean_text(strip_html(summary_html))

            image = pick_image_from_feed_entry(e)

            raw_items.append({
                "id": sha1(url),
                "url": url,
                "title": title,
                "summary": summary,
                "image": image,
                "source": src["name"],
                "rss_categories": [src["category"]] if src.get("category") else [],
            })

    # uniq by url
    seen = set()
    items = []
    for it in raw_items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        items.append(it)

    items = items[:MAX_ARTICLES]

    # fetch & enrich
    for it in items:
        try:
            time.sleep(SLEEP_BETWEEN_FETCH)

            html = safe_get(it["url"])

            # Görsel yoksa HTML meta fallback dene
            if not (it.get("image") or "").strip():
                img2 = pick_image_from_html(it["url"], html)
                if img2:
                    it["image"] = img2

            content = extract_main_text(html)

            # --- Türkçe alanlar ---
            it["title_tr"] = tr(it.get("title", ""))
            # uzun özet: yaklaşık 800-1100 kelime bandı
            long_src = extractive_summary(content, max_words=950)
            it["summary_tr_long"] = tr(long_src) if long_src else tr(it.get("summary", ""))

            # kısa özet: UI için
            short_tr = cut_at_sentence_boundary(it["summary_tr_long"], max_chars=360)
            it["summary_tr"] = short_tr

            # modal bölümleri (generator tarafında)
            cat = (it.get("rss_categories") or ["Gündem"])[0] or "Gündem"
            why, bg, imp = build_modal_sections(cat, content)
            it["why_important"] = why
            it["background"] = bg
            it["possible_impacts"] = imp

            # telif riskine karşı TAM METİN yayınlamıyoruz:
            # it["content"] / it["content_tr"] yok.

        except Exception as e:
            # En azından RSS özetlerinden TR üret
            it["title_tr"] = tr(it.get("title", ""))
            it["summary_tr_long"] = tr(it.get("summary", ""))
            it["summary_tr"] = cut_at_sentence_boundary(it["summary_tr_long"], max_chars=360)
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

    print(f"✅ latest.json üretildi: {len(items)} haber -> {OUT_PATH}")

if __name__ == "__main__":
    main()
