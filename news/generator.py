import os
import json
from datetime import datetime
import re
import requests
import xml.etree.ElementTree as ET

# news klasörünü garanti altına al
os.makedirs("news", exist_ok=True)

# ÜCRETSİZ, API KEY GEREKTİRMEYEN RSS KAYNAKLARI
RSS_SOURCES = [
    # Dünya
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    # Türkiye – örnekler
    "https://www.hurriyet.com.tr/rss/anasayfa",
    "https://www.cnnturk.com/feed/rss/all/news",
]

def clean_html(text: str) -> str:
    if not text:
        return ""
    # basit HTML tag temizleme
    return re.sub(r"<.*?>", " ", text).replace("&nbsp;", " ").strip()

articles = []

for src in RSS_SOURCES:
    try:
        print(f"Kaynak alınıyor: {src}")
        resp = requests.get(src, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        # RSS yapısı: <rss><channel><item>...</item></channel></rss>
        channel = root.find("channel")
        if channel is None:
            # Bazı feed'ler namespace kullanır
            # fallback olarak tüm item'ları ara
            items = root.findall(".//item")
        else:
            items = channel.findall("item")

        count_from_source = 0

        for item in items[:20]: # her kaynaktan en fazla 20 haber
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = item.findtext("description") or ""

            if not title or not link:
                continue

            summary = clean_html(desc)

            # görseli basitçe description içinden aramaya çalış (çoğu feed'te olmayabilir)
            image = ""

            articles.append(
                {
                    "title": title,
                    "summary": summary,
                    "image": image,
                    "url": link,
                }
            )
            count_from_source += 1

        print(f"{src} -> {count_from_source} haber eklendi.")

    except Exception as e:
        print(f"HATA ({src}): {e}")

print(f"TOPLAM HABER SAYISI: {len(articles)}")

output = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "articles": articles,
}

with open("news/latest.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("news/latest.json yazıldı.")
