import os
import re
import json
import hashlib
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document

# -------------------------
# Translation (0 maliyet) - varsa deep-translator kullanır, yoksa olduğu gibi bırakır
# -------------------------
def _get_translator():
    try:
        from deep_translator import GoogleTranslator  # pip: deep-translator
        return GoogleTranslator(source="auto", target="tr")
    except Exception:
        return None

_TRANSLATOR = _get_translator()

def tr(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if _TRANSLATOR is None:
        return text  # çeviri paketi yoksa fallback: olduğu gibi
    # Çok uzun metinlerde translator hata verebilir; chunk’layıp birleştiriyoruz
    chunks = chunk_text(text, max_chars=2200)
    out = []
    for c in chunks:
        try:
            out.append(_TRANSLATOR.translate(c))
        except Exception:
            out.append(c)
    return "\n\n".join(out).strip()

# -------------------------
# Config
# -------------------------
OUT_PATH = "news/latest.json"
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "120"))

UA = "HaberRobotuBot/1.0 (+https://newest-resu.github.io/)"
S = requests.Session()
S.headers.update({"User-Agent": UA})
S.timeout = 25

# -------------------------
# RSS Sources (Kategoriler KORUNUYOR + Finans + Yerel eklendi)
# category alanı: JSON'da rss_categories olarak geçer.
# -------------------------
RSS_SOURCES = [
    # ---- Dünya / Teknoloji / Ekonomi (mevcutlar + ekler) ----
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "Dünya"},
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "category": "Teknoloji"},
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "category": "Ekonomi"},

    # ---- Türkiye geneli (mevcutlar) ----
    {"name": "Hürriyet", "url": "https://www.hurriyet.com.tr/rss/anasayfa", "category": "Türkiye"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/all/news", "category": "Türkiye"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/ekonomi/news", "category": "Ekonomi"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/spor/news", "category": "Spor"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/bilim-teknoloji/news", "category": "Teknoloji"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/saglik/news", "category": "Sağlık"},

    # ---- (Örnek ek ulusal RSS'ler) ----
    # Bu kaynaklar RSS veriyorsa çalışır; vermezse otomatik skip olur (pipeline bozulmaz).
    {"name": "NTV", "url": "https://www.ntv.com.tr/turkiye.rss", "category": "Türkiye"},
    {"name": "NTV", "url": "https://www.ntv.com.tr/ekonomi.rss", "category": "Ekonomi"},
    {"name": "NTV", "url": "https://www.ntv.com.tr/spor.rss", "category": "Spor"},
    {"name": "NTV", "url": "https://www.ntv.com.tr/teknoloji.rss", "category": "Teknoloji"},

    # -------------------------
    # YENİ: Finans (buton)
    # -------------------------
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "category": "Finans"},
    {"name": "NTV", "url": "https://www.ntv.com.tr/ekonomi.rss", "category": "Finans"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/ekonomi/news", "category": "Finans"},

    # -------------------------
    # YENİ: Yerel (Yalova) - RSS varsa çeker, yoksa sessizce atlar
    # Not: Yerel için birkaç olası feed pattern ekledim. Hangisi çalışırsa onu kullanır.
    # -------------------------
    {"name": "Yalova Gazetesi", "url": "https://www.yalovagazetesi.com/rss", "category": "Yerel"},
    {"name": "Yalova Gazetesi", "url": "https://www.yalovagazetesi.com/feed", "category": "Yerel"},
    {"name": "Yalova Gazetesi", "url": "https://www.yalovagazetesi.com/feed/", "category": "Yerel"},
]

# -------------------------
# Helpers
# -------------------------
def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def norm_ws(s: str) -> str:
    s = (s or "").replace("\r", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()

def strip_html(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text(" ").strip()

def safe_get(url: str, timeout=25) -> str:
    r = S.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text

def pick_image(entry) -> str:
    # RSS/Atom alanları farklı olabiliyor; olabildiğince yakalamaya çalışıyoruz
    try:
        if hasattr(entry, "media_content") and entry.media_content:
            url = entry.media_content[0].get("url")
            if url:
                return url
    except Exception:
        pass

    try:
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            url = entry.media_thumbnail[0].get("url")
            if url:
                return url
    except Exception:
        pass

    try:
        if hasattr(entry, "links"):
            for l in entry.links:
                if l.get("type", "").startswith("image/") and l.get("href"):
                    return l["href"]
    except Exception:
        pass

    # summary içindeki img
    try:
        summary_html = getattr(entry, "summary", "") or ""
        soup = BeautifulSoup(summary_html, "lxml")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    except Exception:
        pass

    return ""

def extract_main_text(html: str) -> str:
    doc = Document(html)
    main_html = doc.summary(html_partial=True)
    soup = BeautifulSoup(main_html, "lxml")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    text = soup.get_text("\n")
    return norm_ws(text)

def split_sentences(text: str):
    text = (text or "").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 45:
            out.append(p)
    return out

def score_sentence(s: str):
    score = 0.0
    if re.search(r"\d", s):
        score += 2.5
    if re.search(r"\b[A-ZÇĞİÖŞÜ]{2,}\b", s):
        score += 1.8
    if re.search(r"\b[A-Z][a-zçğıöşü]+\b", s):
        score += 1.0
    score += min(len(s) / 140.0, 2.5)
    return score

def build_extractive_summary(text: str, max_words: int):
    sents = split_sentences(text)
    if not sents:
        return ""

    scored = sorted([(score_sentence(s), i, s) for i, s in enumerate(sents)], reverse=True)
    chosen = []
    total_words = 0

    for _, _, s in scored:
        w = len(s.split())
        if total_words + w > max_words:
            continue
        chosen.append(s)
        total_words += w
        if total_words >= max_words * 0.92:
            break

    if not chosen:
        chosen = sents[:5]

    # orijinal sıraya göre diz
    idx_map = {s: i for i, s in enumerate(sents)}
    chosen_sorted = sorted(chosen, key=lambda x: idx_map.get(x, 999999))
    return " ".join(chosen_sorted).strip()

def chunk_text(text: str, max_chars: int = 2500):
    text = (text or "").strip()
    if len(text) <= max_chars:
        return [text] if text else []
    chunks, cur, cur_len = [], [], 0
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        add_len = len(para) + 2
        if cur_len + add_len > max_chars and cur:
            chunks.append("\n\n".join(cur))
            cur, cur_len = [para], len(para)
        else:
            cur.append(para)
            cur_len += add_len
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks

# -------------------------
# "Daha mantıklı" bullet üretimi (tekrar cümle yapıştırma hissini azaltır)
#  - Tam LLM kalitesi değildir ama okuyucu algısı belirgin şekilde iyileşir.
# -------------------------
def _simplify_sentence(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    # Çok uzun ise kısalt
    words = s.split()
    if len(words) > 26:
        s = " ".join(words[:26]).rstrip() + "…"
    return s

def bullets_structured(summary_tr_long: str):
    sents = split_sentences(summary_tr_long)
    if not sents:
        return {
            "why_important": [],
            "background": [],
            "possible_impacts": []
        }

    # skorla, ama bölümler için farklı dil kalıplarıyla sun
    scored = sorted([(score_sentence(s), s) for s in sents], reverse=True)
    top = [s for _, s in scored[:12]]

    why = []
    bg = []
    imp = []

    # Basit ama işe yarayan seçim: farklı cümleleri farklı bölümlere paylaştır
    for i, s in enumerate(top):
        t = _simplify_sentence(s)
        if len(why) < 3 and i % 3 == 0:
            why.append(f"Öne çıkan nokta: {t}")
        elif len(bg) < 3 and i % 3 == 1:
            bg.append(f"Arka plan: {t}")
        elif len(imp) < 3 and i % 3 == 2:
            imp.append(f"Muhtemel etki: {t}")

        if len(why) >= 3 and len(bg) >= 3 and len(imp) >= 3:
            break

    return {
        "why_important": why,
        "background": bg,
        "possible_impacts": imp
    }

# -------------------------
# Main
# -------------------------
def main():
    raw_items = []

    for src in RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            entries = getattr(feed, "entries", []) or []
        except Exception:
            continue

        for e in entries[: MAX_ARTICLES * 2]:
            url = getattr(e, "link", "") or ""
            if not url:
                continue

            title = getattr(e, "title", "") or ""
            summary_html = getattr(e, "summary", "") or ""
            summary = strip_html(summary_html)

            image = pick_image(e)

            raw_items.append({
                "id": sha1(url),
                "url": url,
                "title": title,
                "summary": summary,
                "image": image,
                "source": src.get("name", "") or "Kaynak",
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

    # Fetch -> extract -> summarize -> translate -> structured bullets
    for it in items:
        try:
            html = safe_get(it["url"])
            content = extract_main_text(html)

            long_src = build_extractive_summary(content, max_words=900)   # uzun özet kaynağı
            short_src = build_extractive_summary(content, max_words=70)   # kısa özet kaynağı

            # Çeviri (başlık / kısa / uzun)
            it["title_tr"] = tr(it["title"]) if it["title"].strip() else ""
            it["summary_tr"] = tr(short_src) if short_src else tr(it.get("summary", ""))
            it["summary_tr_long"] = tr(long_src) if long_src else it["summary_tr"]

            structured = bullets_structured(it["summary_tr_long"])
            it["why_important"] = structured["why_important"]
            it["background"] = structured["background"]
            it["possible_impacts"] = structured["possible_impacts"]

        except Exception as ex:
            # En kötü durumda RSS verisi ile ayakta kal
            it["title_tr"] = it.get("title", "")
            it["summary_tr"] = it.get("summary", "")
            it["summary_tr_long"] = it["summary_tr"]
            it["why_important"] = []
            it["background"] = []
            it["possible_impacts"] = []
            it["error"] = str(ex)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "articles": items,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUT_PATH} with {len(items)} articles")

if __name__ == "__main__":
    main()
