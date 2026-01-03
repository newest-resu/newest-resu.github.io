#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import math
import html
import hashlib
import logging
import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests
import feedparser
from bs4 import BeautifulSoup

# -----------------------------
# Config
# -----------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

UA = "HaberRobotu/1.0 (+https://newest-resu.github.io)"
TIMEOUT = 20

# NOTE: Kullanıcının isteği gereği RSS_SOURCES'e DOKUNULMADI.
RSS_SOURCES = [
    # ... (dosyanızdaki mevcut RSS kaynakları burada aynen durur)
]

# NOTE: Kullanıcının isteği gereği CATEGORY_KEYWORDS'e DOKUNULMADI.
CATEGORY_KEYWORDS = {
    # ... (dosyanızdaki mevcut keyword listeleri burada aynen durur)
}

# -----------------------------
# Helpers
# -----------------------------

TR_TLDS = (".tr",)

def now_utc_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def safe_text(x: Optional[str]) -> str:
    if not x:
        return ""
    x = html.unescape(str(x))
    return re.sub(r"\s+", " ", x).strip()

def get_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        h = urlparse(url).hostname or ""
        h = h.lower().strip()
        if h.startswith("www."):
            h = h[4:]
        return h
    except Exception:
        return ""

def is_intl_domain(domain: str) -> bool:
    domain = (domain or "").lower().strip()
    if not domain:
        return True
    return not domain.endswith(TR_TLDS)

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def clamp_text(s: str, max_len: int) -> str:
    s = safe_text(s)
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"

def clean_html_to_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    text = soup.get_text(" ", strip=True)
    return safe_text(text)

# -----------------------------
# Translation (your existing approach)
# -----------------------------

def translate_to_tr(text: str) -> str:
    """
    Projenizde daha önce kullandığınız çeviri yaklaşımı burada aynen korunur.
    (Bu fonksiyonun içini kendi mevcut sürümünüzdeki gibi bırakın.)
    """
    return text  # placeholder; sizin dosyanızdaki mevcut çeviri mantığı burada olmalı

# -----------------------------
# Category guessing (existing logic)
# -----------------------------

def guess_category(title_tr: str, summary_tr: str, rss_categories: List[str], source_type: str) -> str:
    # Bu fonksiyonun içeriği sizde nasılsa o şekilde kalmalı.
    # (Kullanıcı "keyword'lere dokunma" dediği için burada keyword blokları zaten değişmedi.)
    # Aşağıdaki örnek, mevcut yapınızı bozmadan çalışması için minimal/uyumlu bırakılmıştır.

    # RSS kategorilerinden gelenleri değerlendirme
    rss_cats = [(c or "").lower() for c in (rss_categories or [])]
    for c in rss_cats:
        if "business" in c or "finance" in c or "economy" in c or "market" in c:
            return "ekonomi"
        if "sport" in c:
            return "spor"
        if "tech" in c or "technology" in c:
            return "teknoloji"
        if "science" in c:
            return "bilim"
        if "health" in c:
            return "saglik"
        if "entertainment" in c:
            return "magazin"
        if "local" in c:
            return "yerel"

    text = f"{title_tr} {summary_tr}".lower()

    best_cat = None
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for k in keywords:
            if k and k.lower() in text:
                score += 1
        if score > best_score:
            best_score = score
            best_cat = cat

    if not best_cat or best_score == 0:
        return "dunya" if source_type == "intl" else "gundem"
    return best_cat

# -----------------------------
# NEW: Better, longer, consistent TR fields (copyright-safe)
# -----------------------------

def build_long_summary_tr(title_tr: str, summary_tr: str, source: str, category: str) -> str:
    """Telif riski yaratmadan, haberin anlamını genişleten daha uzun TR özet üretir.

    Not: Bu fonksiyon tam metni kopyalamaz. Başlık + kısa özet üzerinden,
    bağlam/etki/olasılık cümleleriyle kullanıcıya 'anlatı' sağlar.
    """
    title_tr = (title_tr or "").strip()
    summary_tr = (summary_tr or "").strip()

    base = summary_tr if len(summary_tr) >= 60 else (summary_tr or title_tr)

    text = f"{title_tr} {summary_tr}".lower()
    has_market = any(k in text for k in ["borsa", "dolar", "euro", "faiz", "enflasyon", "altın", "hisse"])
    has_public = any(k in text for k in ["bakan", "meclis", "belediye", "valilik", "cumhurbaşkan", "yönetmelik"])
    has_emergency = any(k in text for k in ["deprem", "yangın", "sel", "kaza", "saldırı", "çatışma", "operasyon"])

    focus: List[str] = []
    if category == "finans" or has_market:
        focus.append("Gelişmenin piyasalar ve fiyatlama davranışı üzerindeki etkisi, veri ve açıklamaların tonuna göre kısa vadede değişkenlik gösterebilir.")
        focus.append("Yatırımcılar açısından kritik nokta; açıklanan rakamların beklentiyle farkı ve sonraki adımlara dair sinyallerin gücüdür.")
    elif category == "yerel":
        focus.append("Haberdeki gelişme yerel düzeyde hizmet akışı, günlük yaşam ve karar süreçleri açısından önem taşıyabilir.")
        focus.append("Benzer olayların tekrarlanmaması için kurumların atacağı adımlar ve sahadaki uygulama takip edilecektir.")
    elif category == "teknoloji":
        focus.append("Teknoloji tarafında bu tür gelişmeler genellikle ürün yol haritası, regülasyon uyumu ve kullanıcı güveni gibi başlıklarda sonuç üretir.")
    elif category == "spor":
        focus.append("Spor gündeminde bu tür haberler performans, kadro planlaması ve rekabet dengeleri üzerinde doğrudan etkiler yaratabilir.")
    elif category == "saglik":
        focus.append("Sağlık alanındaki gelişmelerde en önemli başlık; doğrulama, riskin kapsamı ve alınacak koruyucu/önleyici adımlardır.")
    elif category == "bilim":
        focus.append("Bilimsel haberlerde bulgunun yöntemi, örneklem büyüklüğü ve bağımsız doğrulama ihtiyacı, yorumun kalitesini belirler.")
    elif category == "magazin":
        focus.append("Magazin haberlerinde iddia ile doğrulanmış bilgi arasındaki ayrım ve resmi açıklamalar, algıyı belirleyen ana unsurlardır.")
    else:
        if has_public:
            focus.append("Açıklamalar ve karar metinleri netleştikçe, uygulama takvimi ve kapsamın genişliği daha görünür hale gelecektir.")
        if has_emergency:
            focus.append("Olayın seyri; resmi bilgilendirmeler, saha çalışmaları ve güvenlik/önlem adımlarına bağlı olarak güncellenebilir.")

    parts: List[str] = []
    if base:
        parts.append(base.rstrip(". ") + ".")
    if focus:
        parts.extend(focus[:3])

    parts.append("Okur açısından pratik soru şudur: Bu gelişme kimi, ne zaman ve hangi koşullarda etkiliyor; ayrıca sonraki resmi açıklamalar hangi yönde geliyor?")
    parts.append(f"Kaynak: {source}. Detay için 'Kaynağa Git' bağlantısı üzerinden orijinal yayına ulaşabilirsiniz.")

    long_text = "\n\n".join([p.strip() for p in parts if p and p.strip()])

    if len(long_text) < 420:
        long_text += "\n\n" + "Gelişmenin sonuçları; ilgili kurum/şirketin sonraki adımları, kamuoyuna yapılacak ek duyurular ve yeni veriler geldikçe daha netleşecektir."

    return long_text

def make_why_important_tr(title_tr: str, summary_tr: str, category: str, source_type: str) -> List[str]:
    title_tr = (title_tr or "").strip()
    summary_tr = (summary_tr or "").strip()
    text = f"{title_tr} {summary_tr}".lower()

    bullets: List[str] = []

    if category in ("finans", "ekonomi") or any(k in text for k in ["borsa", "faiz", "enflasyon", "dolar", "euro", "hisse", "altın"]):
        bullets.extend([
            "Fiyatlama ve beklenti yönetimi açısından kısa vadede oynaklık yaratabilir.",
            "Faiz/enflasyon/kur gibi göstergelerdeki değişim, sektörlerin kazanç görünümünü etkileyebilir.",
            "Yatırım kararlarında en kritik unsur, yeni bilginin mevcut beklentilerle farkıdır.",
        ])
    elif category == "yerel":
        bullets.extend([
            "Yerel düzeyde hizmet, ulaşım veya kamu düzeni üzerinde doğrudan etkisi olabilir.",
            "Karar ve uygulama takvimi netleştikçe, vatandaşın günlük yaşamına yansıması görünür hale gelir.",
            "Benzer olayların tekrarını önleyici adımlar, haberin kalıcı etkisini belirler.",
        ])
    elif category == "teknoloji":
        bullets.extend([
            "Ürün/hizmetlerin güvenliği ve kullanıcı deneyimi açısından sonuç doğurabilir.",
            "Regülasyon uyumu ve veri güvenliği gibi başlıklarda yeni adımları tetikleyebilir.",
        ])
    elif category == "dunya":
        bullets.extend([
            "Bölgesel dengeler ve diplomatik ilişkiler üzerinde etkiler yaratabilir.",
            "Enerji, ticaret ve güvenlik başlıklarında ikincil sonuçlar görülebilir.",
        ])
    elif category == "spor":
        bullets.extend([
            "Kadro planlaması, performans ve fikstür hedefleri üzerinde doğrudan etkisi olabilir.",
            "Taraftar ve kamuoyu algısı, kulüp/organizasyon kararlarını şekillendirebilir.",
        ])
    else:
        bullets.extend([
            "Kamuoyu, kurumlar ve paydaşlar açısından karar süreçlerini etkileyebilecek yeni bilgi içeriyor.",
            "Takip eden açıklamalar geldikçe, etkinin kapsamı daha net anlaşılacaktır.",
        ])

    if len(bullets) < 3:
        bullets.append("Gelişme, kısa vadede gündem önceliklerini ve alınacak aksiyonları değiştirebilir.")

    return bullets[:5]

def make_background_tr(title_tr: str, summary_tr: str, category: str, source_type: str) -> List[str]:
    title_tr = (title_tr or "").strip()
    summary_tr = (summary_tr or "").strip()
    text = f"{title_tr} {summary_tr}".lower()

    bg: List[str] = []

    if category in ("finans", "ekonomi") or any(k in text for k in ["faiz", "enflasyon", "kur", "borsa", "piyasa"]):
        bg.extend([
            "Finansal haberlerde fiyatların yönünü çoğu zaman 'beklenti' belirler; aynı veri farklı beklenti ortamında farklı tepki doğurabilir.",
            "Merkez bankası söylemi, makro veriler ve jeopolitik riskler eşzamanlı okunur.",
        ])
    elif category == "yerel":
        bg.extend([
            "Yerel haberlerde süreç; belediye/valilik gibi kurumların açıklamaları ve sahadaki uygulamalarla netleşir.",
            "Benzer konularda önceki kararlar ve bölgesel koşullar, mevcut gelişmenin etkisini artırabilir veya sınırlayabilir.",
        ])
    elif category == "teknoloji":
        bg.extend([
            "Teknoloji gündeminde ürün sürümleri, regülasyonlar ve güvenlik açıkları gibi konular sık aralıklarla güncellenir.",
            "Kaynak açıklamaları ve resmi dokümanlar, iddiaları doğrulamada kritik rol oynar.",
        ])
    else:
        bg.extend([
            "Haber akışında ilk bilgiler genellikle sınırlıdır; detaylar resmi açıklamalar ve ek raporlarla zaman içinde tamamlanır.",
            "Farklı kaynakların aynı olayı nasıl çerçevelediği, konunun anlaşılmasına yardımcı olur.",
        ])

    return bg[:5]

def make_impacts_tr(title_tr: str, summary_tr: str, category: str, source_type: str) -> List[str]:
    title_tr = (title_tr or "").strip()
    summary_tr = (summary_tr or "").strip()
    text = f"{title_tr} {summary_tr}".lower()

    imp: List[str] = []

    if category in ("finans", "ekonomi") or any(k in text for k in ["borsa", "hisse", "faiz", "kur", "enflasyon", "altın"]):
        imp.extend([
            "Kısa vadede piyasa tepkisiyle fiyatlarda dalgalanma görülebilir.",
            "Orta vadede politika/şirket adımlarına bağlı olarak trend yönü netleşebilir.",
            "Yüksek belirsizlik dönemlerinde risk iştahı sektörler arasında hızlı kayabilir.",
        ])
    elif category == "yerel":
        imp.extend([
            "Yerel hizmet planlaması ve günlük yaşam pratikleri üzerinde etkiler görülebilir.",
            "Kurumların alacağı yeni önlemler, benzer durumların tekrar riskini azaltabilir.",
            "Kısa vadede bilgilendirme ve koordinasyon ihtiyacı artabilir.",
        ])
    elif category == "dunya":
        imp.extend([
            "Bölgesel politikalar ve ticaret akışında ikincil etkiler oluşabilir.",
            "Enerji fiyatları ve tedarik zinciri gibi alanlarda dolaylı yansımalar görülebilir.",
        ])
    elif category == "teknoloji":
        imp.extend([
            "Kullanıcı davranışı ve ürün tercihleri kısa sürede değişebilir.",
            "Güvenlik/uyumluluk gerekleri nedeniyle yeni güncellemeler veya düzenlemeler gündeme gelebilir.",
        ])
    else:
        imp.extend([
            "Kısa vadede gündem yoğunluğu artabilir ve ilgili kurum/kişilerden ek açıklamalar gelebilir.",
            "Orta vadede uygulama adımları netleştikçe etkinin kapsamı somutlaşır.",
        ])

    return imp[:6]

# -----------------------------
# Feed fetch
# -----------------------------

def fetch_feed(url: str) -> feedparser.FeedParserDict:
    headers = {"User-Agent": UA}
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return feedparser.parse(r.text)

# -----------------------------
# Main build
# -----------------------------

def main():
    out_path = os.path.join("news", "latest.json")
    os.makedirs("news", exist_ok=True)

    articles: List[Dict] = []
    seen: set[str] = set()

    for feed_url in RSS_SOURCES:
        try:
            fp = fetch_feed(feed_url)
        except Exception as e:
            logging.warning("Feed fetch failed: %s | %s", feed_url, e)
            continue

        for entry in fp.entries[:60]:
            try:
                title = safe_text(getattr(entry, "title", ""))
                link = safe_text(getattr(entry, "link", "")) or safe_text(getattr(entry, "id", ""))
                if not link:
                    continue

                key = sha1(link)
                if key in seen:
                    continue
                seen.add(key)

                domain = get_domain(link) or "kaynak"
                source_type = "intl" if is_intl_domain(domain) else "tr"

                # summary / description
                raw_summary = safe_text(getattr(entry, "summary", "")) or safe_text(getattr(entry, "description", ""))
                summary = clean_html_to_text(raw_summary)

                rss_categories = []
                try:
                    rss_categories = [safe_text(t.term) for t in getattr(entry, "tags", []) if getattr(t, "term", None)]
                except Exception:
                    rss_categories = []

                # image (varsa)
                image_url = ""
                try:
                    if hasattr(entry, "media_content") and entry.media_content:
                        image_url = safe_text(entry.media_content[0].get("url"))
                except Exception:
                    pass

                # Translate to TR for intl sources (and keep TR as-is)
                if source_type == "intl":
                    title_tr = translate_to_tr(title) if title else ""
                    summary_tr = translate_to_tr(summary) if summary else ""
                else:
                    title_tr = title
                    summary_tr = summary

                title_tr = clamp_text(title_tr, 160)
                summary_tr = clamp_text(summary_tr, 360)

                category = guess_category(title_tr, summary_tr, rss_categories, source_type)

                # Build extended TR fields (copyright-safe, not full text)
                summary_tr_long = build_long_summary_tr(title_tr, summary_tr, domain, category)
                why_important = make_why_important_tr(title_tr, summary_tr, category, source_type)
                possible_impacts = make_impacts_tr(title_tr, summary_tr, category, source_type)
                background = make_background_tr(title_tr, summary_tr, category, source_type)

                articles.append({
                    "title": title,
                    "summary": summary,
                    "title_tr": title_tr,
                    "summary_tr": summary_tr,
                    "summary_tr_long": summary_tr_long,
                    "why_important": why_important,
                    "possible_impacts": possible_impacts,
                    "background": background,
                    "url": link,
                    "source": domain,
                    "source_type": source_type,
                    "rss_categories": rss_categories,
                    "category": category,
                    "image": image_url,
                })

            except Exception as e:
                logging.debug("Entry parse failed: %s", e)
                continue

    payload = {
        "generated_at": now_utc_iso(),
        "articles": articles
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logging.info("Wrote %s (%d articles)", out_path, len(articles))

if __name__ == "__main__":
    main()
