import feedparser
import json
import hashlib
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse

# --- AYARLAR ---
OUTPUT_FILE = "news/latest.json"
MAX_ARTICLES = 300
TIMEOUT = 12
HEADERS = {
    "User-Agent": "HaberRobotuBot/1.0 (+https://newest-resu.github.io)"
}

# --- RSS KAYNAKLARI ---
RSS_SOURCES = [
    ("https://www.trthaber.com/rss/anasayfa.xml", "TRT Haber"),
    ("https://www.aa.com.tr/tr/rss/default?cat=guncel", "Anadolu Ajansı"),
    ("https://www.cnnturk.com/feed/rss/all/news", "CNN Türk"),
    ("https://www.ntv.com.tr/rss", "NTV"),
    ("https://www.istanbul.gov.tr/rss", "İstanbul Valiliği"),
    ("https://feeds.bbci.co.uk/news/rss.xml", "BBC"),
    ("https://rss.cnn.com/rss/edition.rss", "CNN Intl"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
    ("https://feeds.reuters.com/reuters/topNews", "Reuters"),
    # =========================
    # DOĞRUDAN RSS (TR) – Çeşitlilik
    # =========================
    ("https://www.hurriyet.com.tr/rss/anasayfa"),
    ("https://www.milliyet.com.tr/rss/rssnew/gundemrss.xml"),
    ("https://www.sozcu.com.tr/feed/"),
    ("https://www.ntv.com.tr/son-dakika.rss"),
    ("https://www.trthaber.com/rss/sondakika.rss"),
    ("https://www.haberturk.com/rss"),
    ("https://www.tgrthaber.com.tr/rss"),

    # Ekonomi/Finans (TR)
    ("https://www.hurriyet.com.tr/rss/ekonomi"),
    ("https://www.trthaber.com/rss/ekonomi.rss"),

    # Spor (TR)
    ("https://www.trthaber.com/rss/spor.rss"),
    ("https://www.ntv.com.tr/sporskor.rss"),

    # Teknoloji/Bilim (TR)
    ("https://www.ntv.com.tr/teknoloji.rss"),
    ("https://www.trthaber.com/rss/bilim-teknoloji.rss"),

    # Sağlık (TR)
    ("https://www.trthaber.com/rss/saglik.rss"),

    # Magazin (TR)
    ("https://www.ntv.com.tr/yasam.rss"),

    # CNN Türk (sende vardı, korudum)
    ("https://www.cnnturk.com/feed/rss/all/news"),
    ("https://www.cnnturk.com/feed/rss/ekonomi/news"),
    ("https://www.cnnturk.com/feed/rss/spor/news"),
    ("https://www.cnnturk.com/feed/rss/bilim-teknoloji/news"),
    ("https://www.cnnturk.com/feed/rss/magazin/news"),
    ("https://www.cnnturk.com/feed/rss/otomobil/news"),
    ("https://www.cnnturk.com/feed/rss/yasam/news"),

    # =========================
    # DOĞRUDAN RSS (INTL) – Çeşitlilik
    # =========================
    ("https://feeds.bbci.co.uk/news/rss.xml"),
    ("https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("https://feeds.bbci.co.uk/news/health/rss.xml"),

    # The Guardian RSS (genel/tech/business)
    ("https://www.theguardian.com/world/rss"),
    ("https://www.theguardian.com/technology/rss"),
    ("https://www.theguardian.com/business/rss"),

    # Al Jazeera (English)
    ("https://www.aljazeera.com/xml/rss/all.xml"),

    # =========================
    # GOOGLE NEWS RSS – Asıl “kaynak arttırma” motoru
    # (çok site getirir, domain çeşitliliği burada garanti)
    # =========================

    # Genel TR gündem/dünya
    ("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=d%C3%BCnya%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),

    # Finans TR (çoklu sorgu)
    ("https://news.google.com/rss/search?q=(borsa%20OR%20BIST%20OR%20hisse%20OR%20temett%C3%BC)%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(dolar%20OR%20euro%20OR%20alt%C4%B1n%20OR%20gram%20alt%C4%B1n)%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(TCMB%20OR%20faiz%20OR%20enflasyon)%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(kripto%20OR%20Bitcoin%20OR%20Ethereum)%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),

    # Finans INTL
    ("https://news.google.com/rss/search?q=(stocks%20OR%20markets%20OR%20inflation%20OR%20interest%20rates)%20when:7d&hl=en&gl=US&ceid=US:en"),
    ("https://news.google.com/rss/search?q=(gold%20price%20OR%20oil%20prices%20OR%20dollar%20index)%20when:7d&hl=en&gl=US&ceid=US:en"),

    # Spor / Teknoloji / Sağlık / Magazin / Oyun / Otomobil
    ("https://news.google.com/rss/search?q=(s%C3%BCper%20lig%20OR%20transfer%20OR%20ma%C3%A7)%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(yapay%20zeka%20OR%20teknoloji%20OR%20android%20OR%20ios)%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(sa%C4%9Fl%C4%B1k%20OR%20hastane%20OR%20tedavi%20OR%20a%C5%9F%C4%B1)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(magazin%20OR%20%C3%BCnl%C3%BC%20OR%20dizi%20OR%20film)%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(mobil%20oyun%20OR%20PlayStation%20OR%20Xbox%20OR%20Steam)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(otomobil%20OR%20Tesla%20OR%20TOGG%20OR%20muayene)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),

    # Yerel Yalova (çoklu)
    ("https://news.google.com/rss/search?q=Yalova%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(Yalova%20Belediyesi%20OR%20Yalova%20Valili%C4%9Fi)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(%C3%87%C4%B1narc%C4%B1k%20OR%20%C3%87iftlikk%C3%B6y%20OR%20Alt%C4%B1nova%20OR%20Termal%20OR%20Armutlu)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
        # Yerel Marmara (Yalova + çevre iller)
    ("https://news.google.com/rss/search?q=(Marmara%20B%C3%B6lgesi)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(Kocaeli%20OR%20%C4%B0zmit%20OR%20Gebze)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(Sakarya%20OR%20Adapazar%C4%B1)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(Bursa%20OR%20Nil%C3%BCfer%20OR%20Osmangazi%20OR%20Y%C4%B1ld%C4%B1r%C4%B1m)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(Bal%C4%B1kesir%20OR%20Band%C4%B1rma%20OR%20Edremit)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(Tekirda%C4%9F%20OR%20%C3%87orlu%20OR%20%C3%87erkezk%C3%B6y)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(K%C4%B1rklareli%20OR%20L%C3%BCleburgaz)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(Edirne)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(%C4%B0stanbul%20trafik%20OR%20%C4%B0stanbul%20belediye%20OR%20%C4%B0BB)%20when:7d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(%C3%87anakkale%20OR%20Biga)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
    ("https://news.google.com/rss/search?q=(Bilecik)%20when:14d&hl=tr&gl=TR&ceid=TR:tr"),
]

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

# --- YARDIMCILAR ---
def domain_of(url):
    try:
        return urlparse(url).hostname.lower()
    except:
        return ""

def classify_source(url):
    d = domain_of(url)
    if not d:
        return {"label": "Bilinmeyen", "type": "intl"}
    return {"label": d, "type": "tr" if d.endswith(".tr") else "intl"}

def find_best_category(text, url):
    lower = text.lower()

    # Yerel domain + içerik
    dom = domain_of(url)
    if dom.endswith(".tr"):
        for w in CATEGORY_KEYWORDS["yerel"]:
            if w in lower:
                return "yerel"

    # Keyword skoru
    best_cat, best_score = None, 0
    for cat, keys in CATEGORY_KEYWORDS.items():
        score = sum(k in lower for k in keys)
        if score > best_score:
            best_cat, best_score = cat, score

    if best_cat and best_score > 0:
        return best_cat

    # Fallback
    return "dunya" if not dom.endswith(".tr") else "gundem"

def make_long_summary(summary):
    if not summary or len(summary) < 120:
        return summary
    return summary.strip() + " Bu gelişme kamuoyu ve ilgili sektörler açısından kritik öneme sahiptir."

def why_important_text(cat):
    base = {
        "finans": ["Piyasa hareketlerinde etkili olabilir.", "Yatırımcı davranışını tetikleyebilir."],
        "ekonomi": ["Vatandaşın finansal durumunu etkileyebilir.", "Ekonomik denge üzerinde rol oynayabilir."],
        "yerel": ["Yerel halkı doğrudan ilgilendirir.", "Yerel yönetim kararlarını etkileyebilir."]
    }
    return base.get(cat, ["Kamuoyunu ilgilendiren bir gelişmedir."])

# --- ÜRETİM ---
def generate_news():
    articles = []
    seen = set()

    for feed_url, source in RSS_SOURCES:
        try:
            r = requests.get(feed_url, headers=HEADERS, timeout=TIMEOUT)
            feed = feedparser.parse(r.content)
        except Exception:
            continue

        for entry in feed.entries:
            link = getattr(entry, "link", "")
            if not link:
                continue

            uid = hashlib.md5(link.encode()).hexdigest()
            if uid in seen:
                continue
            seen.add(uid)

            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "").strip()

            text = f"{title} {summary}"

            cat = find_best_category(text, link)
            src_info = classify_source(link)

            article = {
                "id": uid,
                "title": title,
                "title_tr": title,
                "summary_tr": summary[:300],
                "summary_tr_long": make_long_summary(summary[:300]),
                "url": link,
                "image": "",
                "source": source,
                "published_at": getattr(entry, "published", ""),
                "category": cat,
                "why_important": why_important_text(cat),
                "background": ["Haber Robotu tarafından RSS ile otomatik derlenmiştir."],
                "possible_impacts": ["Bu haberin ilgili taraflara etkileri olabilir."]
            }

            articles.append(article)
            if len(articles) >= MAX_ARTICLES:
                break

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"{len(articles)} haber başarıyla üretildi.")

if __name__ == "__main__":
    generate_news()
