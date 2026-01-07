import feedparser
import json
import datetime
from pathlib import Path
import html
import re
import requests

OUTPUT = Path("news/raw_news.json")

RSS_FEEDS = [
    
    ("NTV", "https://www.ntv.com.tr/gundem.rss"),
    ("Habertürk", "https://www.haberturk.com/rss"),
    
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    
    ("Anadolu Ajansı Yerel", "https://www.aa.com.tr/tr/rss/default?cat=yerel"),
    ("TRT Haber", "https://www.trthaber.com/rss/turkiye.rss"),
    ("Bursa Hakimiyet", "https://www.bursahakimiyet.com.tr/rss"),
    ("Yalova Gazetesi", "https://www.yalovagazetesi.com/rss"),
    
    ("ESPN", "https://www.espn.com/espn/rss/news"),
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml"),
    
    ("Webtekno", "https://www.webtekno.com/rss.xml"),
    ("ShiftDelete", "https://shiftdelete.net/feed"),
    
    ("Sağlık Bakanlığı", "https://www.saglik.gov.tr/TR/rss"),
    ("Medimagazin", "https://www.medimagazin.com.tr/rss"),
    
    ("Dünya Gazetesi", "https://www.dunya.com/rss"),
    ("Bloomberg HT", "https://www.bloomberght.com/rss"),
    
    ("Investing TR", "https://tr.investing.com/rss/news_25.rss"),
    ("Foreks", "https://www.foreks.com/rss"),
    
    ("Onedio", "https://onedio.com/rss"),
    ("Elle", "https://www.elle.com/rss/all.xml"),
    
    ("Popular Science", "https://www.popsci.com/feed"),
    ("Science Daily", "https://www.sciencedaily.com/rss/all.xml"),
   
    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
    ("Breaking Defense", "https://breakingdefense.com/feed/"),
    
    ("IGN", "https://feeds.ign.com/ign/all"),
    ("GameSpot", "https://www.gamespot.com/feeds/news/"),
    
    ("Motor1", "https://tr.motor1.com/rss/news/all/"),
    ("Autocar", "https://www.autocar.co.uk/rss"),
]

INTL_CATEGORY_KEYWORDS = {
    "dunya": ["war", "conflict", "attack", "peace", "border", "un", "nato"],
    "ekonomi": ["economy", "inflation", "market", "bank", "oil", "gas"],
    "savunma": ["military", "army", "defense", "missile", "weapon"],
    "teknoloji": ["ai", "artificial intelligence", "tech", "google", "apple"],
    "spor": ["match", "goal", "league", "tournament"]
}

CATEGORY_KEYWORDS = {
    "yerel": ["belediye", "valilik", "kaymakam","istanbul", "bursa", "kocaeli", "sakarya", "yalova","çınarcık","cinarcik","çiftlikköy","ciftlikkoy","termal","altınova","altinova","armutlu",
        "yalova belediyesi","yalova valiliği","yalova valiligi","il genel meclisi",
        "imar","altyapı","altyapi","su kesintisi","elektrik kesintisi","trafik düzenlemesi","trafik duzenlemesi",
        "sahil","feribot","iskele","otogar","marmara","kocaeli","izmit","gebze",
        "bursa","nilüfer","nilufer","osmangazi","yıldırım","yildirim","istanbul","ibb","imar", "altyapı", "altyapi","su kesintisi", "elektrik kesintisi","yerel etkinlik", "festival", "panayır"],
    "gundem": ["bakan", "meclis", "cumhurbaşkanı", "seçim", "son dakika","gündem","gundem","meclis","bakan","bakanlık","bakanlik","valilik","belediye",
        "seçim","secim","mahkeme","yargı","yargi","emniyet","operasyon","gözaltı","gozalti","jandarma","Jandarma"
        "deprem","yangın","yangin","sel","fırtına","firtina","kaza","soruşturma","sorusturma","saldırı","teror","terör","terörist","acil","gelişme","gelisme",
        "açıklama","aciklama","duyurdu","duyuru","karar alındı","karar","resmi gazete","bakanlık","bakanlik","tbmm","komisyon","toplantı","toplanti","basın açıklaması","yasa","kanun","yönetmelik","yonetmelik"],
    "dunya": ["ukraine", "israel", "gaza", "usa", "china", "russia", "world","international","global","iran","europe",
        "nato","united nations","g7","g20","sanction","ceasefire","election","summit","conflict","war","afrika","africa","dünya","dunya","uluslararası","uluslararasi","yurt dışı","yurtdışı","yurtdisi",
        "abd","amerika","beyaz saray","pentagon","avrupa","ab","avrupa birliği","bm","birleşmiş milletler","palastine","seçim","referandum","election","referendum"],
    "spor": ["maç", "transfer", "gol", "lig","spor","mac","süper lig","super lig","şampiyona","sampiyona","hakem",
        "derbi","futbol","basketbol","voleybol","tenis","formula 1","box","uefa","şampiyonlar ligi","avrupa ligi","spor","maç","mac ","müsabaka","musabaka","karşılaşma","karsilasma",
        "lig","puan durumu","fikstür","fikstur","play-off","playoff","transfer","bonservis","sözleşme","sozlesme","imza attı","imza","teknik direktör","td","antrenör","antrenor"],
    "ekonomi": ["enflasyon", "dolar", "borsa", "faiz", "ekonomi","ekonomik","bütçe","butce","vergi","zam","asgari ücret","asgari ucret","memur maaşı","memur maasi","büyüme","daralma","resesyon","cari açık","indirim",
        "ihracat","ithalat","üretim","uretim","sanayi","istihdam","işsizlik","issizlik","kobi","ticaret","turizm geliri","dış ticaret","politika faizi","tcmb","merkez bankası"],
    "teknoloji": ["yapay zeka", "ai", "apple", "google","yazılım","yazilim","uygulama","güncelleme","guncelleme","telefon","akıllı","akilli","teknoloji", "dijital",
        "machine learning","kod", "programlama","uygulama", "app","donanım", "donanim","çip", "cip", "işlemci", "islemci","android", "ios", "iphone","microsoft",
        "siber", "siber güvenlik","internet", "veri", "bulut","android","robot","siber","hack","sızıntı","sizinti","openai","google","samsung","tesla"],
   "finans": [ "borsa","bist","hisse","endeks","temettü","temettu","bedelsiz","bedelli","halka arz","tahvil","bono","eurobond","mevduat","fon","tefas","portföy","portfoy","dolar","euro","sterlin","kur","parite","altın","altin","gram altın","ons",
        "faiz","politika faizi","enflasyon","tcmb","fed","ppk","swap","cds","resesyon",
        "kripto","bitcoin","ethereum","btc","eth","emtia","petrol","brent","wti","doğalgaz",
        "nasdaq","s&p","dow","market","markets","stocks","shares","bond","inflation","rates","finans", "finansal", "piyasa", "piyasalar"],
    "saglik": ["sağlık","saglik","hastane","doktor","virüs","virus","enfeksiyon","kanser","tedavi","ilaç","ilac","sağlık", "saglik", "tıp", "tip",
     "hastane", "doktor", "hekim", "klinik", "hastalık", "hastalik", "tanı", "tani","psikiyatri","beslenme", "sağlık bakanlığı", "aşı","asi","covid","koronavirüs","koronavirus", "grip","diyet","obezite","psikoloji","ruh sağlığı","ruh sagligi"],
   "bilim": ["bilim","araştırma","arastirma","deney","laboratuvar","keşif","kesif","fizik","kimya","biyoloji","genetik","esa",
        "astronomi","nasa","teleskop","uzay","roket","iklim","deprem araştırması","jeoloji", "bilim", "bilimsel", "araştırma", "arastirma","bilim insanı","akademik"],
    "savunma": ["savunma","savunma sanayii","ordu","asker","tatbikat","füze","fuze","tank","savaş uçağı","savas ucagi",
       "hava kuvvetleri","deniz kuvvetleri","operasyon","terör","teror","saldırı","saldiri","nato","güvenlik","guvenlik","savunma", "savunma sanayii",
        "askeri", "ordu", "asker","operasyon", "tatbikat","silah", "füze", "fuze","hava kuvvetleri", "deniz kuvvetleri","savaş uçağı", "tank", "zırhlı", "zirhli","terör", "teror", "güvenlik",
       "nato", "askeri üs","iha","siha","dron","drone"],
    "oyun": ["oyun","video oyunu","bilgisayar oyunu","playstation","ps4","ps5","xbox","nintendo","switch","steam","fps",
        "epic games","mobil oyun","battle royale","e-spor","espor","gamer","gaming","call of duty","pubg",
        "fortnite","valorant","cs2","counter strike","league of legends","lol","dota","gta","fifa","efootball"],
    "otomobil": ["otomobil","araba","araç","arac","otomotiv","sedan","suv","tesla","bmw","mercedes","renault","hyundai","Fiat","Ferrari","Lamborghini","Alfa-Romeo","Maserati","Lancia","GMC","Lincoln","Ford","Tesla","Chrysler","Jeep","RAM",
        "togg","elektrikli","şarj","sarj","menzil","trafik","otoyol","muayene","lastik","kaza","airbag","Toyota","Suzuki","Mitsubishi","Honda","Subaru","Nissan","Acura","Isuzu","Infiniti","Mazda","Lexus",
        "Hyundai","Kia","Skoda","Dacia","Seat","Lada","Volvo","Audi","BMW","Mercedes","Benz","Mini","Opel","Porsche","Smart","Volkswagen","Renault","Peugeot","Citroen","Bugatti","DS Automobiles","Alpine",
        "motor", "şanzıman","sanziman","trafik","kaza","otoyol","ehliyet","muayene","sigorta"],
    "yasam": ["yaşam","yasam","hayat","aile","çocuk","cocuk","evlilik","ilişki","iliski","alışveriş","alisveris","günlük hayat", "gunluk hayat","aile", "çocuk", "cocuk","ev", "ev yaşamı", "ev hayati",
        "seyahat", "tatil", "gezi","alışveriş", "alisveris","yemek", "tarif", "mutfak","dekorasyon", "hobi","kişisel gelişim", "kisisel gelisim",
        "tatil","seyahat","gezi","yemek","tarif","dekorasyon","hobi","günlük","gunluk","psikoloji","eğitim","egitim"],
    }

INTL_LABELS_TR = {
    "savunma": "Savunma",
    "ekonomi": "Ekonomi",
    "teknoloji": "Teknoloji",
    "spor": "Spor",
    "dunya": "Dünya"
}

def translate_en_to_tr(text):
    if not text or len(text.strip()) < 10:
        return text

    try:
        r = requests.post(
            "https://libretranslate.de/translate",
            data={
                "q": text,
                "source": "en",
                "target": "tr",
                "format": "text"
            },
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("translatedText", text)
    except Exception:
        pass

    return text

def clean_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r"<[^>]+>", "", text).strip()

def detect_intl_category(text):
    t = text.lower()
    for cat in ["savunma", "ekonomi", "teknoloji", "spor", "dunya"]:
        if any(k in t for k in INTL_CATEGORY_KEYWORDS.get(cat, [])):
            return cat
    return "dunya"

def detect_category(text):
    t = text.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if any(k in t for k in keys):
            return cat
    return "gundem"

def extract_image(entry):
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key)
        if isinstance(media, list) and media:
            return media[0].get("url", "")
    for e in entry.get("enclosures", []):
        if e.get("type", "").startswith("image"):
            return e.get("href", "")
    return ""

articles = []

for source, url in RSS_FEEDS:
    feed = feedparser.parse(url)
    source_type = "intl" if source in ("BBC", "Al Jazeera") else "tr"

    for e in feed.entries[:30]:
        title = clean_html(e.get("title", ""))
        link = e.get("link", "")
        published = e.get("published", "")
        summary = clean_html(e.get("summary") or e.get("description") or "")
        summary = summary or f"{title} ile ilgili gelişmeler aktarıldı."

        if source_type == "intl":
           title = translate_en_to_tr(title)
           summary = translate_en_to_tr(summary)

        combined = f"{title} {summary}"
        image = extract_image(e)

        if source_type == "intl":
            intl_category = detect_intl_category(combined)
            category = "dunya"
            label_tr = f"Dünya • {INTL_LABELS_TR[intl_category]}"
        else:
            intl_category = None
            category = detect_category(combined)
            label_tr = category.capitalize()

        articles.append({
            "title": title,
            "summary": summary,
            "url": link,
            "image": image,
            "source": source,
            "published_at": published,
            "category": category,
            "intl_category": intl_category,
            "label_tr": label_tr,
            "source_type": source_type
        })

OUTPUT.parent.mkdir(exist_ok=True)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "articles": articles
    }, f, ensure_ascii=False, indent=2)
