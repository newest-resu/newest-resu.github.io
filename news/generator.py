import os
import json
import re
import urllib.parse
from datetime import datetime
import xml.etree.ElementTree as ET

import requests

# news klasörünü garanti altına al
os.makedirs("news", exist_ok=True)

# ÜCRETSİZ RSS KAYNAKLARI
RSS_SOURCES = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.hurriyet.com.tr/rss/anasayfa",
    "https://www.cnnturk.com/feed/rss/all/news",
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

def translate_to_tr(text: str) -> str:
    """MyMemory API ile EN -> TR çeviri (server-side)"""
    if not text:
        return text
    try:
        query = urllib.parse.quote(text[:450]) # çok uzun metinlerde kısalt
        url = f"https://api.mymemory.translated.net/get?q={query}&langpair=en|tr"
        r = requests.get(url, timeout=10)
        data = r.json()
        translated = data.get("responseData", {}).get("translatedText")
        return translated or text
    except Exception as e:
        print("Çeviri hatası:", e)
        return text

articles = []

for src in RSS_SOURCES:
    try:
        print("Kaynak:", src)
        resp = requests.get(src, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        items = root.findall(".//item")
        count_from_source = 0

        for item in items[:20]: # her kaynaktan en fazla 20 haber
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = item.findtext("description") or ""

            if not title or not link:
                continue

            summary = clean_html(desc)
            image = extract_image(item)

            # İngilizce olabilecek başlık ve özetleri Türkçeye çevir
            title_tr = translate_to_tr(title)
            summary_tr = translate_to_tr(summary)

            articles.append({
                "title": title_tr,
                "summary": summary_tr,
                "image": image,
                "url": link
            })
            count_from_source += 1

        print(f"{src} -> {count_from_source} haber eklendi.")

    except Exception as e:
        print("Hata:", src, e)

print("TOPLAM HABER:", len(articles))

output = {
    "generated_at": datetime.utcnow().isoformat(),
    "articles": articles
}

with open("news/latest.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("news/latest.json yazıldı.")
