
# scripts/build_latest.py
import json
import os
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import requests
import feedparser
from bs4 import BeautifulSoup

with open("news/raw.json", encoding="utf-8") as f:
    raw = json.load(f)

TR_TZ = timezone(timedelta(hours=3))  # Europe/Istanbul (+03:00)
UA = "Mozilla/5.0 (compatible; HaberRobotuBot/1.0; +https://newest-resu.github.io/)"

MAX_ITEMS_PER_SOURCE = 18
TOTAL_LIMIT = 320

# ------------------------------------------------------------
# RSS Sources (Çoklu site + Google News RSS)
# Finans + Yerel (Yalova) güçlendirildi
# ------------------------------------------------------------
RSS_SOURCES = [
    # =========================
    # DOĞRUDAN RSS (TR) – Çeşitlilik
    # =========================
    {"url": "https://www.hurriyet.com.tr/rss/anasayfa", "hint": "gundem"},
    {"url": "https://www.milliyet.com.tr/rss/rssnew/gundemrss.xml", "hint": "gundem"},
    {"url": "https://www.sozcu.com.tr/feed/", "hint": "gundem"},
    {"url": "https://www.ntv.com.tr/son-dakika.rss", "hint": "gundem"},
    {"url": "https://www.trthaber.com/rss/sondakika.rss", "hint": "gundem"},
    {"url": "https://www.haberturk.com/rss", "hint": "gundem"},
    {"url": "https://www.tgrthaber.com.tr/rss", "hint": "gundem"},

    # Ekonomi/Finans (TR)
    {"url": "https://www.hurriyet.com.tr/rss/ekonomi", "hint": "ekonomi"},
    {"url": "https://www.trthaber.com/rss/ekonomi.rss", "hint": "ekonomi"},

    # Spor (TR)
    {"url": "https://www.trthaber.com/rss/spor.rss", "hint": "spor"},
    {"url": "https://www.ntv.com.tr/sporskor.rss", "hint": "spor"},

    # Teknoloji/Bilim (TR)
    {"url": "https://www.ntv.com.tr/teknoloji.rss", "hint": "teknoloji"},
    {"url": "https://www.trthaber.com/rss/bilim-teknoloji.rss", "hint": "teknoloji"},

    # Sağlık (TR)
    {"url": "https://www.trthaber.com/rss/saglik.rss", "hint": "saglik"},

    # Magazin (TR)
    {"url": "https://www.ntv.com.tr/yasam.rss", "hint": "yasam"},

    # CNN Türk (sende vardı, korudum)
    {"url": "https://www.cnnturk.com/feed/rss/all/news", "hint": "gundem"},
    {"url": "https://www.cnnturk.com/feed/rss/ekonomi/news", "hint": "ekonomi"},
    {"url": "https://www.cnnturk.com/feed/rss/spor/news", "hint": "spor"},
    {"url": "https://www.cnnturk.com/feed/rss/bilim-teknoloji/news", "hint": "teknoloji"},
    {"url": "https://www.cnnturk.com/feed/rss/magazin/news", "hint": "magazin"},
    {"url": "https://www.cnnturk.com/feed/rss/otomobil/news", "hint": "otomobil"},
    {"url": "https://www.cnnturk.com/feed/rss/yasam/news", "hint": "yasam"},

    # =========================
    # DOĞRUDAN RSS (INTL) – Çeşitlilik
    # =========================
    {"url": "https://feeds.bbci.co.uk/news/rss.xml", "hint": "dunya"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "hint": "dunya"},
    {"url": "https://feeds.bbci.co.uk/news/business/rss.xml", "hint": "finans"},
    {"url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "hint": "teknoloji"},
    {"url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "hint": "bilim"},
    {"url": "https://feeds.bbci.co.uk/news/health/rss.xml", "hint": "saglik"},

    # The Guardian RSS (genel/tech/business)
    {"url": "https://www.theguardian.com/world/rss", "hint": "dunya"},
    {"url": "https://www.theguardian.com/technology/rss", "hint": "teknoloji"},
    {"url": "https://www.theguardian.com/business/rss", "hint": "finans"},

    # Al Jazeera (English)
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "hint": "dunya"},

    # =========================
    # GOOGLE NEWS RSS – Asıl “kaynak arttırma” motoru
    # (çok site getirir, domain çeşitliliği burada garanti)
    # =========================

    # Genel TR gündem/dünya
    {"url": "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr", "hint": "gundem"},
    {"url": "https://news.google.com/rss/search?q=d%C3%BCnya%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "dunya"},

    # Finans TR (çoklu sorgu)
    {"url": "https://news.google.com/rss/search?q=(borsa%20OR%20BIST%20OR%20hisse%20OR%20temett%C3%BC)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(dolar%20OR%20euro%20OR%20alt%C4%B1n%20OR%20gram%20alt%C4%B1n)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(TCMB%20OR%20faiz%20OR%20enflasyon)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(kripto%20OR%20Bitcoin%20OR%20Ethereum)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "finans"},

    # Finans INTL
    {"url": "https://news.google.com/rss/search?q=(stocks%20OR%20markets%20OR%20inflation%20OR%20interest%20rates)%20when:7d&hl=en&gl=US&ceid=US:en", "hint": "finans"},
    {"url": "https://news.google.com/rss/search?q=(gold%20price%20OR%20oil%20prices%20OR%20dollar%20index)%20when:7d&hl=en&gl=US&ceid=US:en", "hint": "finans"},

    # Spor / Teknoloji / Sağlık / Magazin / Oyun / Otomobil
    {"url": "https://news.google.com/rss/search?q=(s%C3%BCper%20lig%20OR%20transfer%20OR%20ma%C3%A7)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "spor"},
    {"url": "https://news.google.com/rss/search?q=(yapay%20zeka%20OR%20teknoloji%20OR%20android%20OR%20ios)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "teknoloji"},
    {"url": "https://news.google.com/rss/search?q=(sa%C4%9Fl%C4%B1k%20OR%20hastane%20OR%20tedavi%20OR%20a%C5%9F%C4%B1)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "saglik"},
    {"url": "https://news.google.com/rss/search?q=(magazin%20OR%20%C3%BCnl%C3%BC%20OR%20dizi%20OR%20film)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "magazin"},
    {"url": "https://news.google.com/rss/search?q=(mobil%20oyun%20OR%20PlayStation%20OR%20Xbox%20OR%20Steam)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "oyun"},
    {"url": "https://news.google.com/rss/search?q=(otomobil%20OR%20Tesla%20OR%20TOGG%20OR%20muayene)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "otomobil"},

    # Yerel Yalova (çoklu)
    {"url": "https://news.google.com/rss/search?q=Yalova%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Yalova%20Belediyesi%20OR%20Yalova%20Valili%C4%9Fi)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(%C3%87%C4%B1narc%C4%B1k%20OR%20%C3%87iftlikk%C3%B6y%20OR%20Alt%C4%B1nova%20OR%20Termal%20OR%20Armutlu)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
        # Yerel Marmara (Yalova + çevre iller)
    {"url": "https://news.google.com/rss/search?q=(Marmara%20B%C3%B6lgesi)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Kocaeli%20OR%20%C4%B0zmit%20OR%20Gebze)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Sakarya%20OR%20Adapazar%C4%B1)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Bursa%20OR%20Nil%C3%BCfer%20OR%20Osmangazi%20OR%20Y%C4%B1ld%C4%B1r%C4%B1m)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Bal%C4%B1kesir%20OR%20Band%C4%B1rma%20OR%20Edremit)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Tekirda%C4%9F%20OR%20%C3%87orlu%20OR%20%C3%87erkezk%C3%B6y)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(K%C4%B1rklareli%20OR%20L%C3%BCleburgaz)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Edirne)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(%C4%B0stanbul%20trafik%20OR%20%C4%B0stanbul%20belediye%20OR%20%C4%B0BB)%20when:7d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(%C3%87anakkale%20OR%20Biga)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},
    {"url": "https://news.google.com/rss/search?q=(Bilecik)%20when:14d&hl=tr&gl=TR&ceid=TR:tr", "hint": "yerel"},

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
_TRANSLATION_LIMIT = 160

def translate_to_tr(text: str) -> str:
    global _TRANSLATION_CALLS
    t = safe(text)
    if not t:
        return t
    if _TRANSLATION_CALLS >= _TRANSLATION_LIMIT:
        return t
    _TRANSLATION_CALLS += 1

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
# Categories & Keywords (genişletildi)
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
        "borsa","bist","hisse","endeks","temettü","temettu","bedelsiz","bedelli","halka arz",
        "tahvil","bono","eurobond","mevduat","fon","tefas","portföy","portfoy",
        "dolar","euro","sterlin","kur","parite","altın","altin","gram altın","ons",
        "faiz","politika faizi","enflasyon","tcmb","fed","ppk","swap","cds","resesyon",
        "kripto","bitcoin","ethereum","btc","eth","emtia","petrol","brent","wti","doğalgaz",
        "nasdaq","s&p","dow","market","markets","stocks","shares","bond","inflation","rates""finans", "finansal", "piyasa", "piyasalar",
  "borsa", " bist ", "endeks",
  "hisse", "hisseler", "portföy", "portfoy",
  "yatırım", "yatirim", "yatırımcı",
  "fon", "tefas", "emeklilik fonu",
  "altın", "gram altın", "ons altın",
  "döviz", "dolar", "euro", "sterlin",
  "kripto", "bitcoin", "ethereum",
  "tahvil", "bono", "getiri",
  "kredi", "faizli", "temettü"                            
        
    ],
    "yerel": [
        "yalova","çınarcık","cinarcik","çiftlikköy","ciftlikkoy","termal","altınova","altinova","armutlu",
        "yalova belediyesi","yalova valiliği","yalova valiligi","il genel meclisi",
        "imar","altyapı","altyapi","su kesintisi","elektrik kesintisi","trafik düzenlemesi","trafik duzenlemesi",
        "sahil","feribot","iskele","otogar","marmara","kocaeli","izmit","gebze","sakarya","adapazarı","adapazari",
        "bursa","nilüfer","nilufer","osmangazi","yıldırım","yildirim",
        "balıkesir","balikesir","bandırma","bandirma","edremit",
        "tekirdağ","tekirdag","çorlu","corlu","çerkezköy","cerkezkoy",
        "kırklareli","kirklareli","lüleburgaz","luleburgaz",
        "edirne","istanbul","ibb","çanakkale","canakkale","biga","bilecik""imar", "altyapı", "altyapi",
  "su kesintisi", "elektrik kesintisi",
  "yerel etkinlik", "festival", "panayır"

    ],
    "gundem": [
        "son dakika","gündem","gundem","meclis","bakan","bakanlık","bakanlik","valilik","belediye",
        "seçim","secim","mahkeme","yargı","yargi","emniyet","operasyon","gözaltı","gozalti","jandarma","Jandarma"
        "deprem","yangın","yangin","sel","fırtına","firtina","kaza","soruşturma","sorusturma","saldırı","teror","terör","terörist","acil","gelişme","gelisme",
        "açıklama","aciklama","duyurdu","duyuru",
        "karar alındı","karar","resmi gazete",
        "bakan","bakanlık","bakanlik",
        "valilik","belediye","kaymakamlık",
        "meclis","tbmm","komisyon",
        "toplantı","toplanti","basın açıklaması",
        "yasa","kanun","yönetmelik","yonetmelik"
    ],
    "dunya": [
        "world","international","global","ukraine","russia","israel","gaza","iran","china","usa","europe",
        "nato","united nations","g7","g20","sanction","ceasefire","election","summit","conflict","war","afrika","africa","dünya","dunya","uluslararası","uluslararasi",
        "yurt dışı","yurtdışı","yurtdisi",
        "abd","amerika","beyaz saray","pentagon",
        "avrupa","ab","avrupa birliği",
        "nato","bm","birleşmiş milletler",
        "çin","rusya","ukrayna","israil","filistin",
        "orta doğu","asya","palastine"
        "seçim","referandum","hükümet","hukumet","election","referendum"
    ],
    "spor": [
        "spor","maç","mac","lig","süper lig","super lig","şampiyona","sampiyona","gol","transfer","hakem",
        "derbi","futbol","basketbol","voleybol","tenis","formula 1","box","uefa","şampiyonlar ligi","avrupa ligi","spor","maç","mac ","müsabaka","musabaka","karşılaşma","karsilasma",
        "lig","puan durumu","fikstür","fikstur","play-off","playoff",
        "transfer","bonservis","sözleşme","sozlesme","imza attı","imza",
        "teknik direktör","td","antrenör","antrenor"

    ],
    "teknoloji": [
        "teknoloji","yazılım","yazilim","uygulama","güncelleme","guncelleme","telefon","akıllı","akilli","teknoloji", "dijital",
  "yapay zeka", "ai ", "machine learning",
  "kod", "programlama",
  "uygulama", "app",
  "donanım", "donanim",
  "çip", "cip", "işlemci", "islemci",
  "android", "ios", "iphone",
  "google", "apple", "microsoft",
  "siber", "siber güvenlik",
  "internet", "veri", "bulut"
        "android","ios","yapay zeka","ai","robot","çip","cip","işlemci","islemci","donanım","donanim",
        "siber","hack","sızıntı","sizinti","openai","google","microsoft","apple","samsung","tesla"
    ],
    "saglik": [
        "sağlık","saglik","hastane","doktor","virüs","virus","enfeksiyon","kanser","tedavi","ilaç","ilac","sağlık", "saglik", "tıp", "tip",
     "hastane", "doktor", "hekim", "klinik", "hastalık", "hastalik", "tanı", "tani",
     "psikiyatri","beslenme", "sağlık bakanlığı"
        "aşı","asi","covid","koronavirüs","koronavirus","grip","diyet","obezite","psikoloji","ruh sağlığı","ruh sagligi"
    ],
    "ekonomi": [
        "ekonomi","ekonomik","bütçe","butce","vergi","zam","asgari ücret","asgari ucret","memur maaşı","memur maasi","büyüme","daralma","resesyon","cari açık","indirim"
        "ihracat","ithalat","üretim","uretim","sanayi","istihdam","işsizlik","issizlik","kobi","ticaret","turizm geliri","dış ticaret","politika faizi","tcmb","merkez bankası"
    ],
    "magazin": [
        "magazin","ünlü","unlu","şarkıcı","sarkici","oyuncu","dizi","film","evlilik","boşanma","bosanma",
        "aşk","ask","görüntülendi","konser","klip","festival","kırmızı halı","kirmizi hali"
    ],
    "bilim": [
        "bilim","araştırma","arastirma","deney","laboratuvar","keşif","kesif","fizik","kimya","biyoloji","genetik","esa"
        "astronomi","nasa","teleskop","uzay","roket","iklim","deprem araştırması","jeoloji", "bilim", "bilimsel", "araştırma", "arastirma",
        "bilim insanı","akademik",

    ],
    "savunma": [
        "savunma","savunma sanayii","ordu","asker","tatbikat","füze","fuze","tank","savaş uçağı","savas ucagi",
       "hava kuvvetleri","deniz kuvvetleri","operasyon","terör","teror","saldırı","saldiri","nato","güvenlik","guvenlik","savunma", "savunma sanayii",
        "askeri", "ordu", "asker","operasyon", "tatbikat",
       "silah", "füze", "fuze",
       "hava kuvvetleri", "deniz kuvvetleri",
      "savaş uçağı", "tank", "zırhlı", "zirhli",
      "terör", "teror", "güvenlik",
       "nato", "askeri üs"
        "iha","siha","dron","drone"
    ],
    "oyun": [
        "oyun","video oyunu","bilgisayar oyunu","playstation","ps4","ps5","xbox","nintendo","switch","steam","fps"
        "epic games","mobil oyun","battle royale","e-spor","espor","gamer","gaming","call of duty","pubg",
        "fortnite","valorant","cs2","counter strike","league of legends","lol","dota","gta","fifa","efootball"
    ],
    "otomobil": [
        "otomobil","araba","araç","arac","otomotiv","sedan","suv","tesla","bmw","mercedes","renault","hyundai","Fiat","Ferrari","Lamborghini","Alfa-Romeo","Maserati","Lancia","GMC","Lincoln","Ford","Tesla","Chrysler","Jeep","RAM"
        "togg","elektrikli","şarj","sarj","menzil","trafik","otoyol","muayene","lastik","kaza","airbag","Toyota","Suzuki","Mitsubishi","Honda","Subaru","Nissan","Acura","Isuzu","Infiniti","Mazda","Lexus"
        "Hyundai","Kia","Skoda","Dacia","Seat","Lada","Volvo","Audi","BMW","Mercedes","Benz","Mini","Opel","Porsche","Smart","Volkswagen","Renault","Peugeot","Citroen","Bugatti","DS Automobiles","Alpine",
        "motor", "şanzıman","sanziman",
        "trafik","kaza",
        "otoyol","ehliyet",
        "muayene","sigorta"
    ],
    "yasam": [
        "yaşam","yasam","hayat","aile","çocuk","cocuk","evlilik","ilişki","iliski","alışveriş","alisveris",
  "günlük hayat", "gunluk hayat",
  "aile", "çocuk", "cocuk",
  "ev", "ev yaşamı", "ev hayati",
  "seyahat", "tatil", "gezi",
  "alışveriş", "alisveris",
  "yemek", "tarif", "mutfak",
  "dekorasyon", "hobi",
  "kişisel gelişim", "kisisel gelisim"
        "tatil","seyahat","gezi","yemek","tarif","dekorasyon","hobi","günlük","gunluk","psikoloji","eğitim","egitim"
    ],
}

def score_keywords(text: str, cat: str) -> int:
    t = (text or "").lower()
    score = 0
    for k in CATEGORY_KEYWORDS.get(cat, []):
        if k and k.lower() in t:
            score += 1
    return score

def guess_category(title_any: str, summary_any: str, rss_categories: list, hint: str, url: str) -> str:
    text = (a.get("title_tr","") + " " + a.get("summary_tr","")).lower()
    rc = " ".join([safe(x).lower() for x in (rss_categories or []) if safe(x)])

    # 1) Yerel sadece Yalova/ilçe kelimeleri geçiyorsa
    if hint == "yerel" and score_keywords(text, "yerel") > 0:
        return "yerel"

    # 2) Finans hint’i zorlamıyoruz: finans olması için sinyal gerekli
    if hint == "finans":
        if score_keywords(text, "finans") >= 1:
            return "finans"
        if any(k in rc for k in ["business", "finance", "markets", "money", "economy"]):
            return "finans"

    # 3) RSS kategori eşlemesi
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
        if any(k in rc for k in ["entertainment", "culture", "arts"]):
            return "magazin"

    # 4) Keyword scoring
    scores = {cat: score_keywords(text, cat) for cat in CATEGORY_KEYWORDS.keys()}

    if scores.get("yerel", 0) > 0:
        return "yerel"

    fin = scores.get("finans", 0)
    eco = scores.get("ekonomi", 0)

    best_cat = max(scores.items(), key=lambda x: x[1])[0]
    best_score = scores.get(best_cat, 0)

    if best_score > 0:
        if eco > 0 and fin > 0 and fin >= eco:
            return "finans"
        return best_cat

    return "dunya" if is_foreign(url) else "gundem"

# ------------------------------------------------------------
# Modal content generation (telifsiz, analitik uzun özet)
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
    nums = re.findall(r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\b", text or "")
    out = []
    for n in nums:
        if n not in out:
            out.append(n)
    return out[:8]

def extract_locations_like(text: str) -> list:
    words = re.findall(r"\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\b", text or "")
    blacklist = {"Bu","Bir","İçin","Kaynak","Finans","Yerel","Dünya","Gündem","Son","TR"}
    out = []
    for w in words:
        if w in blacklist:
            continue
        if w not in out:
            out.append(w)
        if len(out) >= 8:
            break
    return out

def build_long_summary_tr(title_tr: str, summary_tr: str, category: str, source: str, url: str) -> str:
    title_tr = safe(title_tr)
    summary_tr = safe(summary_tr)

    base_sents = pick_sentences(summary_tr, max_sent=12)  # daha fazla cümle
    nums = extract_numbers(summary_tr)
    locs = extract_locations_like(title_tr + " " + summary_tr)

    cat_label = CATEGORY_LABELS.get(category, "Genel")
    origin = "Türkiye kaynağı" if not is_foreign(url) else "Uluslararası kaynak"

    intro = (
        f"Bu içerik, {cat_label} kategorisinde derlenmiş bir haber özetidir ({origin}, Kaynak: {source}).\n"
        f"Başlık: {title_tr}"
    )

    happened = " ".join(base_sents[:4]) if base_sents else (summary_tr or "Bu haber için kısa özet mevcut değil.")

    detail_bits = []
    if locs:
        detail_bits.append("Öne çıkan yer/başlıklar: " + ", ".join(locs) + ".")
    if nums:
        detail_bits.append("Haberde geçen sayısal veriler: " + ", ".join(nums) + ".")
    if category == "finans":
        detail_bits.append("Finans haberlerinde benzer gelişmeler genellikle veri akışı, politika mesajları ve küresel risk iştahıyla birlikte fiyatlanır.")
        detail_bits.append("Bu nedenle kısa vadeli hareketler görülebilir; karar için kaynağa gidip detay doğrulaması yapmak önemlidir.")
    elif category == "yerel":
        detail_bits.append("Yerel gelişmelerde resmi kurum açıklamaları (belediye/valilik) ve sahadan güncellemeler önemlidir.")
        detail_bits.append("Etkiler; hizmetler, ulaşım, etkinlikler veya yerel gündem başlıklarında netleşebilir.")
    else:
        detail_bits.append("Gelişme, yeni ayrıntılarla güncellenebilir; resmi açıklamalar ve kaynak detayları izlenmelidir.")

    details = " ".join(detail_bits)

    watch = []
    if category == "finans":
        watch.append("İzlenecek başlıklar: ilgili kurum açıklamaları, yeni veri/karar akışı, risk iştahı değişimi ve piyasada oluşabilecek ikinci etkiler.")
    elif category == "yerel":
        watch.append("İzlenecek başlıklar: yerel kurum duyuruları, saha güncellemeleri, ulaşım/hizmet bildirimleri ve yeni resmi açıklamalar.")
    else:
        watch.append("İzlenecek başlıklar: resmi teyitler, zaman çizelgesi ve ek açıklamalar.")
    watch_text = " ".join(watch)

    # Daha uzun format (4–5 paragraf)
    extra_context = ""
    extra_sents = base_sents[4:8]
    if extra_sents:
        extra_context = "Ek bağlam:\n" + " ".join(extra_sents)

    long_text = (
        f"{intro}\n\n"
        f"Ne oldu?\n{happened}\n\n"
        f"Detaylar ve bağlam:\n{details}\n\n"
        f"{extra_context}\n\n"
        f"Ne izlenmeli?\n{watch_text}"
    ).strip()

    # UI için üst sınır
    if len(long_text) > 1800:
        long_text = long_text[:1800].rsplit(" ", 1)[0] + "…"

    return long_text

def make_why_important_tr(title_tr: str, summary_tr: str, category: str) -> list:
    bullets = []
    if category == "finans":
        bullets += [
            "Piyasa fiyatlamaları (kur/altın/borsa/faiz) üzerinde kısa vadeli dalgalanma yaratabilir.",
            "Beklentileri etkileyebilecek veri/karar/söylem içeriyor olabilir.",
            "İlgili sektör/şirketler açısından risk-fırsat dengesini değiştirebilir.",
        ]
    elif category == "yerel":
        bullets += [
            "Yalova ve çevresinde günlük yaşamı etkileyebilecek bir gelişmeye işaret ediyor.",
            "Yerel kurumların alacağı kararlar ve uygulamalar açısından önem taşıyabilir.",
            "Ulaşım/hizmet/etkinlik gibi alanlarda yeni güncellemeler doğurabilir.",
        ]
    else:
        bullets += [
            "Gündemi etkileyebilecek yeni bir bilgi veya gelişme içeriyor.",
            "Kısa vadede kamuoyu ve karar vericiler üzerinde etkisi olabilir.",
        ]

    if re.search(r"\b\d{1,3}([.,]\d{3})*\b", summary_tr):
        bullets.insert(0, "Haberde yer alan sayısal veriler, gelişmenin ölçeğini ve olası etkisini anlamayı kolaylaştırır.")

    out = []
    for b in bullets:
        b = safe(b)
        if b and b not in out:
            out.append(b)
    return out[:4]

def make_background_tr(summary_tr: str, category: str) -> list:
    sents = pick_sentences(summary_tr, max_sent=10)
    out = sents[:3] if sents else ["—"]
    if category == "finans":
        out.append("Benzer finans haberleri genellikle veri takvimi, merkez bankası iletişimi ve küresel risk iştahıyla birlikte yorumlanır.")
    if category == "yerel":
        out.append("Yerel gelişmelerde belediye/valilik duyuruları ve sahadan teyitler kritik önemdedir.")
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
        bullets.append("Yeni haber akışı devam ederse, fiyatlar kısa süreli “haber bazlı” tepkiler verebilir; karar için kaynak detayını doğrulamak gerekir.")
    elif category == "yerel":
        bullets.append("Gelişmenin seyrine göre yerel hizmetler/ulaşım/etkinlikler gibi alanlarda güncellemeler görülebilir.")
    else:
        bullets.append("Gelişme yeni ayrıntılarla güncellenebilir; resmi açıklamalar ve kaynak detayları takip edilmelidir.")

    out = []
    for b in bullets:
        b = safe(b)
        if b and b not in out:
            out.append(b)
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
    out = {"generated_at": now_tr.isoformat(), "articles": articles}

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("Yazıldı:", OUT_PATH, "Toplam:", len(articles))

if __name__ == "__main__":
    main()
