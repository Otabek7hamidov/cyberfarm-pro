import time
import random
import re
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MODELS = [
    {"brand": "Samsung", "model": "SM-S918B", "display": "Galaxy S23 Ultra", "android": "14", "ver": "14.0.0", "type": "samsung"},
    {"brand": "Samsung", "model": "SM-A546B", "display": "Galaxy A54 5G", "android": "14", "ver": "14.0.0", "type": "samsung"},
    {"brand": "Samsung", "model": "SM-A346B", "display": "Galaxy A34 5G", "android": "14", "ver": "14.0.0", "type": "samsung"},
    {"brand": "Samsung", "model": "SM-A145F", "display": "Galaxy A14", "android": "13", "ver": "13.0.0", "type": "samsung"},
    {"brand": "Xiaomi", "model": "23049PCD8G", "display": "POCO F5", "android": "13", "ver": "13.0.0", "type": "xiaomi"},
    {"brand": "Xiaomi", "model": "22101316G", "display": "Redmi Note 12 Pro", "android": "13", "ver": "13.0.0", "type": "xiaomi"},
    {"brand": "Xiaomi", "model": "21091116UG", "display": "Redmi Note 11", "android": "12", "ver": "12.0.0", "type": "xiaomi"},
    {"brand": "OPPO", "model": "CPH2359", "display": "Reno8 5G", "android": "13", "ver": "13.0.0", "type": "webview"},
    {"brand": "vivo", "model": "V2219", "display": "Vivo Y35", "android": "13", "ver": "13.0.0", "type": "webview"},
]

def generate_mobile_session(proxy=None):
    """Creates an authentic mobile browsing session mimicking Uzbekistan smartphones."""
    dev = random.choice(MODELS)
    chrome_major = random.choice([126, 127, 128])
    chrome_patch = random.randint(6000, 6999)
    chrome_sub = random.randint(10, 190)
    chrome_ver = f"{chrome_major}.0.{chrome_patch}.{chrome_sub}"

    if dev["type"] == "samsung":
        sb_major = random.choice(["23.0", "24.0"])
        ua = f"Mozilla/5.0 (Linux; Android {dev['android']}; SAMSUNG {dev['model']}) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/{sb_major} Chrome/115.0.0.0 Mobile Safari/537.36"
        sec_brand = f'"Samsung Internet";v="{sb_major.split(".")[0]}", "Chromium";v="115"'
    elif dev["type"] == "xiaomi":
        ua = f"Mozilla/5.0 (Linux; U; Android {dev['android']}; ru-ru; {dev['model']} Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_ver} Mobile Safari/537.36 XiaoMi/MiuiBrowser/14.8.5-gn"
        sec_brand = f'"Chromium";v="{chrome_major}", "Not;A=Brand";v="24"'
    else:
        # High quality In-App QR scanner / WebView
        ua = f"Mozilla/5.0 (Linux; Android {dev['android']}; {dev['model']}; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_ver} Mobile Safari/537.36"
        sec_brand = f'"Chromium";v="{chrome_major}", "Not;A=Brand";v="24"'

    headers = {
        "Host": "project.cybercontrol.uz",
        "Connection": "keep-alive",
        "sec-ch-ua": sec_brand,
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-ch-ua-platform-version": f'"{dev["ver"]}"',
        "sec-ch-ua-model": f'"{dev["model"]}"',
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8,en;q=0.7",
    }

    session = requests.Session()
    if proxy:
        if isinstance(proxy, str):
            p_url = proxy if "://" in proxy else f"http://{proxy}"
            session.proxies = {"http": p_url, "https": p_url}
        elif isinstance(proxy, dict):
            host = proxy.get("host")
            port = proxy.get("port")
            if host and port:
                p_url = f"http://{host}:{port}"
                session.proxies = {"http": p_url, "https": p_url}

    return session, headers, dev

def execute_referral_visit(referral_url="https://project.cybercontrol.uz/r/ZoGAZU1cAMWHfgxvQmcAYg", logger=None, proxy=None):
    """
    Executes a complete, genuine mobile referral funnel to CyberControl.
    Anti-fraud compliant:
      1. Clean fresh session & unique visitor ID (aq_vid).
      2. Genuine mobile device identity & matching client hints.
      3. 70% 'yosh' / 30% 'nafaqa' category distribution (0% iiv).
      4. Natural human reading delay (4.5 - 6.5s).
      5. Verification of HTTP 302 redirect to Google Play Store.
    """
    def log(msg):
        if logger:
            logger(msg)
        print(f"[ReferralManager] {msg}", flush=True)

    session, headers, dev = generate_mobile_session(proxy=proxy)
    log(f"📱 Mobil Profil: {dev['display']} ({dev['brand']} {dev['model']}), Android {dev['android']}")

    # Category selection: 70% yosh, 30% nafaqa, 0% iiv
    if random.random() < 0.70:
        cat_key = "yosh"
        cat_label = "Нафақа ёшига етмаган фуқаро"
        prob_str = "70%"
    else:
        cat_key = "nafaqa"
        cat_label = "Нафақа ёшидаги фуқаро"
        prob_str = "30%"

    log(f"🎯 Tanlanadigan toifa: '{cat_label}' (Ehtimollik: {prob_str})")

    # Step 1: Open landing page (with connection retry)
    log(f"1. Referal sahifa ochilmoqda: {referral_url}")
    r1 = None
    for attempt in range(4):
        try:
            r1 = session.get(referral_url, headers=headers, verify=False, allow_redirects=False, timeout=15)
            if r1.status_code in (200, 302):
                break
        except Exception as e:
            if attempt < 3:
                log(f"Tarmoq ulanishini qayta urinish ({attempt+1}/3)...")
                time.sleep(2.5)
            else:
                log(f"Xatolik: Referal sahifani ochib bo'lmadi: {e}")
                return False, None, f"Ulanish xatosi: {e}"

    if not r1:
        return False, None, "Serverga ulanib bo'lmadi"

    if r1.status_code != 200:
        log(f"Ogohlantirish: Kutilmagan server javobi (Status: {r1.status_code}, Location: {r1.headers.get('Location')})")
        # If server immediately 302 redirects to Play Store, it might still have counted or bypassed
        if r1.status_code == 302 and "play.google.com" in (r1.headers.get("Location") or ""):
            return True, {
                "category": cat_label,
                "category_key": cat_key,
                "device": dev,
                "redirect_url": r1.headers.get("Location"),
                "status": "MUVAFFAQINLI"
            }, "Server to'g'ridan-to'g'ri yo'naltirdi"
        return False, None, f"Server xatosi: {r1.status_code}"

    # Extract javob link for chosen category
    # Pattern: href="(/r/<ref_code>/javob/<token>/<cat_key>)"
    m = re.search(rf'href="(/r/[^/]+/javob/[^"]+/{cat_key})"', r1.text)
    if not m:
        # Fallback to any javob link if specific key not matched
        m = re.search(r'href="(/r/[^/]+/javob/[^"]+/(yosh|nafaqa))"', r1.text)
        if not m:
            log("Xatolik: Referal javob tugmasi HTML ichidan topilmadi!")
            return False, None, "Javob havolasi topilmadi"

    javob_path = m.group(1)
    javob_url = f"https://project.cybercontrol.uz{javob_path}"
    log(f"   Referal so'rovnoma havolasi topildi: {javob_url}")

    # Natural human reading delay (4.5 to 6.5s) to satisfy anti-speed filters
    reading_delay = random.uniform(4.5, 6.5)
    log(f"⏳ Tabiiy insoniy o'qish vaqti kutilmoqda ({reading_delay:.1f} soniya)...")
    time.sleep(reading_delay)

    # Step 2: Submit category answer (with connection retry)
    headers["Referer"] = referral_url
    headers["Sec-Fetch-Site"] = "same-origin"

    log(f"2. Toifa tanlash yuborilmoqda: '{cat_label}'...")
    r2 = None
    for attempt in range(4):
        try:
            r2 = session.get(javob_url, headers=headers, verify=False, allow_redirects=False, timeout=15)
            if r2.status_code in (200, 302):
                break
        except Exception as e:
            if attempt < 3:
                log(f"Javob yuborishni qayta urinish ({attempt+1}/3)...")
                time.sleep(2.5)
            else:
                log(f"Xatolik: Javob yuborishda xato: {e}")
                return False, None, f"Javob yuborish xatosi: {e}"

    if not r2:
        return False, None, "Serverga javob yuborib bo'lmadi"

    log(f"   Server javob kodi: {r2.status_code}")
    loc = r2.headers.get("Location", "")
    log(f"   Yo'naltirish manzili: {loc}")

    if r2.status_code == 302 and "play.google.com" in loc:
        log(f"✅ CyberControl referal javobini qabul qildi va Google Play Store ga yo'naltirdi!")
        return True, {
            "category": cat_label,
            "category_key": cat_key,
            "device": dev,
            "redirect_url": loc,
            "status": "MUVAFFAQINLI"
        }, "Muvaffaqiyatli qabul qilindi"
    else:
        log(f"Xato: Kutilmagan javob: {r2.status_code}, matn: {r2.text[:200]}")
        return False, None, f"Javob xatosi: {r2.status_code}"

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    ok, info, msg = execute_referral_visit()
    print("Natija:", ok, info, msg)
