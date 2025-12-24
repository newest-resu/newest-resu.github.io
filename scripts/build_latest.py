import os, re, json, time, hashlib
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document
from deep_translator import GoogleTranslator

OUT_PATH = "news/latest.json"
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "120"))

# RSS kaynakları (sende olan listeyi buraya koyabilirsin)
RSS_SOURCES = [
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "Dünya"},
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "category": "Teknoloji"},
    {"name": "BBC", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "category": "Ekonomi"},

    {"name": "Hürriyet", "url": "https://www.hurriyet.com.tr/rss/anasayfa", "category": "Türkiye"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/all/news", "category": "Türkiye"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/ekonomi/news", "category": "Ekonomi"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/spor/news", "category": "Spor"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/bilim-teknoloji/news", "category": "Teknoloji"},
    {"name": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/saglik/news", "category": "Sağlık"},
]

UA = "HaberRobotuBot/1.0 (+https://newest-resu.github.io/)"
S = requests.Session()
S.headers.update({"User-Agent": UA})
translator = GoogleTranslator(source="auto", target="tr")


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def norm_ws(s: str) -> str:
    s = s.replace("\r", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def pick_image(entry) -> str:
    if hasattr(entry, "media_content") and entry.media_content:
        url = entry.media_content[0].get("url")
        if url:
            return url
    if hasattr(entry, "links"):
        for l in entry.links:
            if l.get("type", "").startswith("image/") and l.get("href"):
                return l["href"]
    return ""


def safe_get(url: str, timeout=20) -> str:
    r = S.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def extract_main_text(html: str) -> str:
    # Readability -> ana metin
    doc = Document(html)
    main_html = doc.summary(html_partial=True)
    soup = BeautifulSoup(main_html, "lxml")

    # Gereksiz alanlar
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    text = soup.get_text("\n")
    return norm_ws(text)


def split_sentences(text: str):
    # Basit cümle bölme (TR/EN için yeterli)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    # Çok kısa/boşları ayıkla
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 40:
            out.append(p)
    return out


def score_sentence(s: str):
    # Basit önem skoru: sayı, özel isim benzeri, uzunluk
    score = 0
    if re.search(r"\d", s):
        score += 3
    if re.search(r"\b[A-ZÇĞİÖŞÜ]{2,}\b", s):  # kısaltmalar
        score += 2
    if re.search(r"\b[A-Z][a-zçğıöşü]+\b", s):  # İngilizce/özel isim kalıbı
        score += 1
    score += min(len(s) / 120, 3)  # uzunluk katkısı
    return score


def build_extractive_summary(text: str, max_words: int):
    sents = split_sentences(text)
    if not sents:
        return ""

    scored = sorted([(score_sentence(s), i, s) for i, s in enumerate(sents)], reverse=True)
    chosen = []
    total_words = 0

    # En iyi cümlelerden al, sonra orijinal sıraya göre diz
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

    # okunabilirlik için orijinal sıralama
    chosen_sorted = sorted(chosen, key=lambda x: sents.index(x))
    return " ".join(chosen_sorted).strip()


def chunk_text(text: str, max_chars: int = 2500):
    if len(text) <= max_chars:
        return [text]
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


def tr(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    parts = chunk_text(text, 2500)
    out = []
    for p in parts:
        try:
            out.append(translator.translate(p))
        except Exception:
            out.append(p)
        time.sleep(0.30)
    return norm_ws("\n\n".join(out))


def bullets_from_summary(summary_tr: str, max_bullets: int = 4):
    # Basit bullet üretimi: uzun özeti cümlelere ayırıp ilk güçlü cümleleri seç
    sents = split_sentences(summary_tr)
    sents = [s for s in sents if len(s.split()) >= 8]
    if not sents:
        return []

    # skora göre seç
    scored = sorted([(score_sentence(s), s) for s in sents], reverse=True)
    picked = []
    for _, s in scored:
        s = s.strip()
        if s and s not in picked:
            picked.append(s)
        if len(picked) >= max_bullets:
            break

    # Bullet’ları biraz kısalt (çok uzunsa)
    out = []
    for s in picked:
        words = s.split()
        out.append(" ".join(words[:28]) + ("…" if len(words) > 28 else ""))
    return out


def main():
    raw_items = []
    for src in RSS_SOURCES:
        feed = feedparser.parse(src["url"])
        for e in getattr(feed, "entries", [])[: MAX_ARTICLES * 2]:
            url = getattr(e, "link", "") or ""
            if not url:
                continue
            title = getattr(e, "title", "") or ""
            summary_html = getattr(e, "summary", "") or ""
            summary = BeautifulSoup(summary_html, "lxml").get_text(" ").strip()
            image = pick_image(e)

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

    # Fetch -> extract -> make summaries -> translate
    for it in items:
        try:
            html = safe_get(it["url"])
            content = extract_main_text(html)

            # uzun özet (EN/TR fark etmez; önce extractive özetle kısalt)
            long_src = build_extractive_summary(content, max_words=1000)  # ~800-1200 kelime bandı
            short_src = build_extractive_summary(content, max_words=70)

            # Türkçe çeviri (başlık/özet/uzun özet)
            it["title_tr"] = tr(it["title"]) if it["title"].strip() else ""
            it["summary_tr"] = tr(short_src) if short_src else tr(it["summary"])
            it["summary_tr_long"] = tr(long_src) if long_src else it["summary_tr"]

            # Katma değer bölümleri (bullet)
            # Not: Bu bölümler "yorum" içermez, türetilmiş çıkarım/özet formatındadır.
            it["why_important"] = bullets_from_summary(it["summary_tr_long"], 4)
            it["background"] = bullets_from_summary(it["summary_tr_long"], 4)
            it["possible_impacts"] = bullets_from_summary(it["summary_tr_long"], 4)

            # Tam metni yayınlamıyoruz (telif riskini azaltmak için)
            # content/content_tr alanları YOK.
        except Exception as ex:
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
