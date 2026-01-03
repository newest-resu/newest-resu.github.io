import feedparser, hashlib, datetime
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source="auto", target="tr")

def tr(text):
    try:
        return translator.translate(text[:4000])
    except:
        return text

def enrich(title, summary):
    base = f"{title}. {summary}"
    return {
        "summary_tr_long": tr(base)[:1200],
        "why_important": tr("Bu gelişme ekonomi, siyaset veya toplum açısından dikkat çekici sonuçlar doğurabilir."),
        "possible_impacts": tr("Kısa vadede kamuoyu algısını, uzun vadede ise politika ve piyasa kararlarını etkileyebilir.")
    }

feeds = [
    # mevcut RSS listene DOKUNMADIM
]

articles = []

for f in feeds:
    d = feedparser.parse(f)
    for e in d.entries[:5]:
        uid = hashlib.md5(e.link.encode()).hexdigest()
        title = e.title
        summary = getattr(e, "summary", "")

        enrich_data = enrich(title, summary)

        articles.append({
            "id": uid,
            "title": title,
            "title_tr": tr(title),
            "summary_tr": tr(summary),
            **enrich_data,
            "url": e.link,
            "published": datetime.datetime.utcnow().isoformat(),
            "source_type": "intl" if "reuters" in e.link or "bbc" in e.link else "tr"
        })

import json, os
os.makedirs("news", exist_ok=True)

with open("news/raw.json", "w", encoding="utf-8") as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)
