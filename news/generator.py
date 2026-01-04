import os
import json
import re
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import urllib.parse
from urllib.parse import urlparse

import requests

# news klasörünü garanti altına al
os.makedirs("news", exist_ok=True)

# RSS KAYNAKLARI (genel + kategori bazlı)
RSS_SOURCES = [
    # BBC genel ve dünya
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",

    # BBC tematik: teknoloji, bilim, sağlık, ekonomi
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "https://feeds.bbci.co.uk/news/health/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",

    # Türkiye genel
    "https://www.hurriyet.com.tr/rss/anasayfa",
    "https://www.cnnturk.com/feed/rss/all/news",

    # CNN Türk kategori bazlı RSS (spor, ekonomi, teknoloji, sağlık, magazin, otomobil, yaşam vs.)
    "https://www.cnnturk.com/feed/rss/turkiye/news",
    "https://www.cnnturk.com/feed/rss/dunya/news",
    "https://www.cnnturk.com/feed/rss/ekonomi/news",
    "https://www.cnnturk.com/feed/rss/spor/news",
    "https://www.cnnturk.com/feed/rss/bilim-teknoloji/news",
    "https://www.cnnturk.com/feed/rss/saglik/news",
    "https://www.cnnturk.com/feed/rss/magazin/news",
    "https://www.cnnturk.com/feed/rss/otomobil/news",
    "https://www.cnnturk.com/feed/rss/yasam/news",
]

def clean_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<.*?>", " ", text).replace("&nbsp;", " ").strip()

def extract_image(item):
    # media:content
    media = item.find("{http://search.yahoo.com/mrss/}content")
    if media is not None and "url" in media.attrib:
        return media.attrib["url"]

    # media:thumbnail
    thumb = item.find("{http://search.yahoo.com/mrss/}thumbnail")
    if thumb is not None and "url" in thumb.attrib:
        return thumb.attrib["url"]

    # enclosure
    enclosure = item.find("enclosure")
    if enclosure is not None and "url" in enclosure.attrib:
        return enclosure.attrib["url"]

    # description içinden <img> ara
    desc = item.findtext("description") or ""
    img = re.search(r'<img[^>]+src="([^"]+)"', desc)
    if img:
        return img.group(1)

    return ""

def is_foreign(url: str) -> bool:
    """Sonu .tr ile bitmeyen domainleri 'yabancı' say."""
    try:
        d = urlparse(url).hostname or ""
        d = d.replace("www.", "")
        return not d.endswith(".tr")
    except Exception:
        return True

# Çeviri ile ilgili ayarlar
TRANSLATION_CALLS = 0
TRANSLATION_LIMIT = 60  # tek çalışmada maksimum çeviri isteği

def translate_to_tr(text: str) -> str:
    """MyMemory API ile EN -> TR çeviri. Limit ve WARNING filtreli."""
    global TRANSLATION_CALLS
    if not text:
        return text
    if TRANSLATION_CALLS >= TRANSLATION_LIMIT:
        return text

    try:
        TRANSLATION_CALLS += 1
        query = urllib.parse.quote(text[:450])  # çok uzun metinleri kısalt
        url = f"https://api.mymemory.translated.net/get?q={query}&langpair=en|tr"
        r = requests.get(url, timeout=10)
        data = r.json()
        translated = (data.get("responseData", {}) or {}).get("translatedText") or ""

        # Günlük limit dolduğunda gelen WARNING metnini tamamen yoksay
        upper = translated.upper()
        if "MYMEMORY WARNING" in upper or "YOU USED ALL AVAILABLE FREE TRANSLATIONS" in upper:
            print("Çeviri limit uyarısı alındı, orijinal metin kullanılacak.")
            return text

        return translated or text
    except Exception as e:
        print("Çeviri hatası:", e)
        return text

articles = []
seen_links = set()  # aynı haberi birden fazla kaynaktan çekersek tekrarı önlemek için

for src in RSS_SOURCES:
    try:
        print("Kaynak:", src)
        resp = requests.get(src, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        items = root.findall(".//item")
        count_from_source = 0

        for item in items[:12]:  # her kaynaktan en fazla 12 haber al
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link") or "").strip()
            desc  = item.findtext("description") or ""

            if not title or not link:
                continue

            # Aynı link daha önce eklendiyse atla
            if link in seen_links:
                continue
            seen_links.add(link)

            summary = clean_html(desc)
            image   = extract_image(item)

            # RSS category etiketlerini oku
            rss_categories = [ (c.text or "").lower() for c in item.findall("category") if c.text ]

            # Kaynağa göre çeviri kararı
            if is_foreign(link):
                title_tr   = translate_to_tr(title)
                summary_tr = translate_to_tr(summary)
            else:
                title_tr, summary_tr = title, summary

            articles.append({
                "title": title_tr,
                "summary": summary_tr,
                "image": image,
                "url": link,
                "rss_categories": rss_categories
            })
            count_from_source += 1

        print(f"{src} -> {count_from_source} haber eklendi.")

    except Exception as e:
        print("Hata:", src, e)

print("TOPLAM HABER:", len(articles))

# Türkiye yerel saati: UTC + 3, sade format
now_tr = datetime.utcnow() + timedelta(hours=3)
generated_str = now_tr.strftime("%Y-%m-%d %H.%M")

output = {
    "generated_at": generated_str,
    "articles": articles
}

with open("news/latest.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("news/latest.json yazıldı.")
