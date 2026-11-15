import os
import sys
import re
import time
import json
import random
import subprocess
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
ADB_EXE = os.path.join(BASE_DIR, "platform-tools", "adb.exe")
PROXIES_CACHE_FILE = os.path.join(BASE_DIR, "free_proxies_cache.json")

IP_CHECK_SERVICES = [
    "https://api.ipify.org",
    "https://icanhazip.com",
    "https://checkip.amazonaws.com",
    "http://ifconfig.me/ip",
    "http://api.ipify.org"
]

def is_valid_ipv4(ip_str):
    if not ip_str:
        return False
    parts = ip_str.strip().split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit() or not (0 <= int(p) <= 255):
            return False
    return True

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=all&ssl=all&anonymity=all"
]

def get_public_ip(proxy=None, timeout=6):
    """Fetches the external public IP address."""
    proxies_dict = None
    if proxy:
        if isinstance(proxy, str):
            p_url = proxy if "://" in proxy else f"http://{proxy}"
            proxies_dict = {"http": p_url, "https": p_url}
        elif isinstance(proxy, dict):
            host = proxy.get("host")
            port = proxy.get("port")
            if host and port:
                p_url = f"http://{host}:{port}"
                proxies_dict = {"http": p_url, "https": p_url}

    for svc in IP_CHECK_SERVICES:
        try:
            resp = requests.get(svc, proxies=proxies_dict, timeout=timeout, verify=False)
            if resp.status_code == 200:
                ip = resp.text.strip()
                if is_valid_ipv4(ip):
                    return ip
        except Exception:
            continue
    return None

def find_physical_android_device(adb_path=ADB_EXE, logger=None):
    """
    Finds a real physical Android phone connected via USB.
    Ignores virtual emulators (emulator-*, 127.0.0.1:*, localhost:*).
    Returns serial string or None.
    """
    if not os.path.exists(adb_path):
        return None

    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        res = subprocess.run([adb_path, "devices"], capture_output=True, text=True, timeout=5, creationflags=flags)
        for raw_line in res.stdout.strip().splitlines():
            line = raw_line.strip()
            if not line or "List of devices attached" in line or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0].strip()
                status = parts[1].strip()
                # Skip emulators
                if serial.startswith("emulator-") or serial.startswith("127.0.0.1:") or serial.startswith("localhost:"):
                    continue

                if status == "unauthorized":
                    if logger:
                        logger(f"[DIQQAT] USB telefon topildi ({serial}), ammo ruxsat berilmagan! Telefoningiz ekranida 'Har doim ruxsat berish' (Allow USB Debugging) tugmasini bosing.")
                    return None
                elif status == "device":
                    return serial
    except Exception:
        pass
    return None

def toggle_airplane_and_data(adb_path, phone_serial, logger=None):
    """Executes multi-method airplane mode and mobile data toggle via ADB."""
    def log(msg):
        if logger:
            logger(msg)
        print(f"[ADB Phone] {msg}", flush=True)

    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    log(f"Mobil internetni yangilash boshlandi (Qurilma: {phone_serial})...")

    # Method 1: cmd connectivity airplane-mode
    try:
        subprocess.run([adb_path, "-s", phone_serial, "shell", "cmd", "connectivity", "airplane-mode", "enable"], timeout=6, creationflags=flags)
    except Exception:
        pass

    # Method 2: Global setting & broadcast
    try:
        subprocess.run([adb_path, "-s", phone_serial, "shell", "settings", "put", "global", "airplane_mode_on", "1"], timeout=4, creationflags=flags)
        subprocess.run([adb_path, "-s", phone_serial, "shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "true"], timeout=4, creationflags=flags)
    except Exception:
        pass

    # Method 3: Mobile Data off
    try:
        subprocess.run([adb_path, "-s", phone_serial, "shell", "svc", "data", "disable"], timeout=4, creationflags=flags)
    except Exception:
        pass

    log("Parvoz rejimi yoqildi, 4 soniya kutilmoqda...")
    time.sleep(4)

    # Disable airplane mode
    try:
        subprocess.run([adb_path, "-s", phone_serial, "shell", "cmd", "connectivity", "airplane-mode", "disable"], timeout=6, creationflags=flags)
    except Exception:
        pass

    try:
        subprocess.run([adb_path, "-s", phone_serial, "shell", "settings", "put", "global", "airplane_mode_on", "0"], timeout=4, creationflags=flags)
        subprocess.run([adb_path, "-s", phone_serial, "shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "false"], timeout=4, creationflags=flags)
    except Exception:
        pass

    # Enable mobile data
    try:
        subprocess.run([adb_path, "-s", phone_serial, "shell", "svc", "data", "enable"], timeout=4, creationflags=flags)
    except Exception:
        pass

    log("Parvoz rejimi o'chirildi, mobil internet qayta ulanmoqda...")

def rotate_mobile_ip(adb_path=ADB_EXE, old_ip=None, max_wait_sec=35, logger=None):
    """1-usul: Mobil Internet + Parvoz rejimi rotatsiyasi."""
    def log(msg):
        if logger:
            logger(msg)
        print(f"[IP Rotator] {msg}", flush=True)

    if not old_ip:
        old_ip = get_public_ip()
    log(f"Joriy IP manzil: {old_ip or 'Aniqlanmadi'}")

    phone_serial = find_physical_android_device(adb_path, logger=logger)

    if phone_serial:
        log(f"✅ Jismoniy Android telefon ulandi ({phone_serial}). Avtomatik parvoz rejimi ishga tushirildi...")
        toggle_airplane_and_data(adb_path, phone_serial, logger=logger)
    else:
        log("⚠️ Diqqat: USB orqali boshqariladigan telefon ulanmagan. Hozirgi tarmoq orqali davom etilmoqda.")
        cur_ip = get_public_ip() or old_ip
        log(f"Aktiv IP holati: {cur_ip}")
        return cur_ip

    log("Yangi O'zbekiston mobil IP manzili qabul qilinishi kutilmoqda...")
    start_t = time.time()
    while time.time() - start_t < max_wait_sec:
        time.sleep(2)
        new_ip = get_public_ip(timeout=4)
        if new_ip and new_ip != old_ip:
            log(f"🎉 YANGI MOBIL IP OLINDI: {new_ip} (Oldingi IP: {old_ip})")
            return new_ip

    final_ip = get_public_ip()
    if final_ip == old_ip and old_ip is not None:
        log(f"⚠️ Ogohlantirish: IP manzili o'zgarmadi ({final_ip}). Parvoz rejimini qayta urinish...")
        if phone_serial:
            toggle_airplane_and_data(adb_path, phone_serial, logger=logger)
            time.sleep(5)
            final_ip = get_public_ip() or old_ip

    log(f"Aktiv IP holati: {final_ip}")
    return final_ip or old_ip

class FreeProxyManager:
    """3-usul: Bepul ochiq proksilarni internetdan yig'uvchi va tekshiruvchi modul."""
    def __init__(self):
        self.working_proxies = []
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(PROXIES_CACHE_FILE):
            try:
                with open(PROXIES_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.working_proxies = json.load(f)
            except Exception:
                self.working_proxies = []

    def _save_cache(self):
        try:
            with open(PROXIES_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.working_proxies[:100], f, indent=2)
        except Exception:
            pass

    def scrape_proxies(self, max_candidates=200):
        candidates = []
        for src in PROXY_SOURCES:
            try:
                resp = requests.get(src, timeout=5, verify=False)
                if resp.status_code == 200:
                    for line in resp.text.splitlines():
                        line = line.strip()
                        if ":" in line and not line.startswith("#"):
                            candidates.append(line)
                            if len(candidates) >= max_candidates:
                                break
            except Exception:
                continue
            if len(candidates) >= max_candidates:
                break
        random.shuffle(candidates)
        return candidates

    def test_single_proxy(self, proxy_str, timeout=3):
        parts = proxy_str.split(":")
        if len(parts) != 2:
            return None
        host, port = parts[0], parts[1]
        p_dict = {"http": f"http://{host}:{port}", "https": f"http://{host}:{port}"}
        start = time.time()
        try:
            resp = requests.get("http://api.ipify.org", proxies=p_dict, timeout=timeout, verify=False)
            if resp.status_code == 200:
                ip = resp.text.strip()
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                    latency = int((time.time() - start) * 1000)
                    return {"host": host, "port": port, "ip": ip, "latency": latency}
        except Exception:
            pass
        return None

    def refresh_pool(self, target_count=5, logger=None):
        def log(msg):
            if logger:
                logger(msg)
            print(f"[ProxyScraper] {msg}", flush=True)

        log("Internetdan yangi bepul proksilar yuklanmoqda...")
        candidates = self.scrape_proxies(max_candidates=150)
        log(f"{len(candidates)} ta proksi tekshirilmoqda...")

        new_working = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_proxy = {executor.submit(self.test_single_proxy, p): p for p in candidates}
            for future in as_completed(future_to_proxy):
                res = future.result()
                if res:
                    new_working.append(res)
                    log(f"Ishlaydigan proksi topildi: {res['host']}:{res['port']} (IP: {res['ip']}, {res['latency']}ms)")
                    if len(new_working) >= target_count:
                        break

        if new_working:
            self.working_proxies.extend(new_working)
            self._save_cache()
            return True
        return False

    def get_working_proxy(self, logger=None):
        # Clean cached list
        if self.working_proxies:
            proxy = self.working_proxies.pop(0)
            self._save_cache()
            return proxy

        # If cache empty, fetch new
        ok = self.refresh_pool(target_count=3, logger=logger)
        if ok and self.working_proxies:
            proxy = self.working_proxies.pop(0)
            self._save_cache()
            return proxy
        return None

free_proxy_mgr = FreeProxyManager()

def prepare_network_for_cycle(mode="USB_MOBILE", emulator=None, worker_name="CyberWorker", old_ip=None, logger=None):
    """
    3 ta rejimni boshqaruvchi asosiy funksiya:
    - 'USB_MOBILE': Mobil Internet + Parvoz rejimi (1-usul)
    - 'DIRECT': Kompyuter tarmog'i (2-usul)
    - 'AUTO_PROXY': Bepul Avtomatik Proxy (3-usul)
    """
    def log(msg):
        if logger:
            logger(msg)
        print(f"[NetworkManager] {msg}", flush=True)

    mode = (mode or "USB_MOBILE").upper()

    if mode == "DIRECT":
        log("Rejim: Kompyuter tarmog'i (To'g'ridan-to'g'ri). Proksisiz ishga tushiriladi.")
        if emulator:
            emulator.clear_device_proxy(worker_name)
        ip = get_public_ip()
        return ip, None

    elif mode == "AUTO_PROXY":
        log("Rejim: Bepul Avtomatik Proxy. Internetdan ishlaydigan proksi qidirilmoqda...")
        proxy = free_proxy_mgr.get_working_proxy(logger=logger)
        if proxy and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", str(proxy.get("ip", "")).strip()):
            log(f"Yangi proksi tayinlandi: {proxy['host']}:{proxy['port']} (Tashqi IP: {proxy['ip']})")
            return proxy["ip"], proxy
        else:
            log("Ogohlantirish: Bepul proksi topilmadi, to'g'ridan-to'g'ri tarmoqdan foydalanilmoqda.")
            if emulator:
                emulator.clear_device_proxy(worker_name)
            return get_public_ip(), None

    else: # USB_MOBILE
        log("Rejim: Mobil Internet (USB + Parvoz rejimi).")
        if emulator:
            emulator.clear_device_proxy(worker_name)
        new_ip = rotate_mobile_ip(old_ip=old_ip, logger=logger)
        return new_ip, None

if __name__ == "__main__":
    print("Joriy Host IP:", get_public_ip())
    print("USB Telefon:", find_physical_android_device())
    p = free_proxy_mgr.get_working_proxy()
    print("Test Proxy:", p)
