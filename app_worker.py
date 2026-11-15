import os
import sys
import time
import json
import datetime
import subprocess
import argparse
import re
import html
from qr_reader import decode_qr
from emulator_manager import EmulatorManager
from sheets_manager import SheetsManager
from device_generator import generate_phone_identity
from ip_manager import prepare_network_for_cycle, get_public_ip
from license_manager import get_node_config

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "worker_state.json")
DEFAULT_APK = os.path.join(BASE_DIR, "com.baxtiyorov.security.apk")

def load_state(retries=3, delay=0.05):
    default_state = {
        "status": "IDLE", # IDLE, RUNNING, PAUSED, COMPLETED, STOPPED, ERROR
        "worker_pid": None,
        "target_limit": 20,
        "completed_today": 0,
        "failed_count": 0,
        "current_step": "Kutilmoqda",
        "current_device": None,
        "current_ip": None,
        "network_mode": "USB_MOBILE",
        "referral_url": "",
        "logs": []
    }
    if os.path.exists(STATE_FILE):
        for attempt in range(retries):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        raise ValueError("Bo'sh fayl o'qildi")
                    data = json.loads(content)
                    default_state.update(data)
                    return default_state
            except (json.JSONDecodeError, ValueError, IOError):
                if attempt < retries - 1:
                    time.sleep(delay)
            except Exception:
                pass
    return default_state

def save_state(state, retries=3, delay=0.05):
    """
    Atomik yozish mexanizmi:
    Ma'lumot avval vaqtinchalik unikal faylga yoziladi, diskka to'liq flush/fsync qilinadi,
    so'ngra os.replace orqali atomik almashtiriladi.
    Bu parallel jarayonlar (Dashboard va Worker) chala yoki bo'sh fayl o'qishini 100% oldini oladi.
    """
    tmp_file = f"{STATE_FILE}.tmp.{os.getpid()}_{time.time_ns()}"
    for attempt in range(retries):
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
            os.replace(tmp_file, STATE_FILE)
            return True
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print(f"[Worker] Holatni saqlashda xato: {e}")
        finally:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
    return False

def is_pid_alive(pid):
    if not pid:
        return False
    try:
        res = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return f'"{pid}"' in res.stdout
    except Exception:
        return False

def start_worker(target_limit=None):
    state = load_state()
    pid = state.get("worker_pid")
    if pid and is_pid_alive(pid):
        state["status"] = "RUNNING"
        if target_limit is not None:
            state["target_limit"] = int(target_limit)
        save_state(state)
        return True, "Ishlayotgan jarayon faollashtirildi."

    if target_limit is not None:
        state["target_limit"] = int(target_limit)
    state["status"] = "RUNNING"
    state["current_step"] = "Ishga tushirilmoqda..."
    save_state(state)

    cmd = [sys.executable, os.path.join(BASE_DIR, "app_worker.py"), "--run"]
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP
    log_file = open(os.path.join(BASE_DIR, "worker_output.log"), "a", encoding="utf-8")
    subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_file, stderr=log_file, creationflags=flags)
    return True, "Yangi worker jarayoni ishga tushirildi."

def pause_worker():
    state = load_state()
    state["status"] = "PAUSED"
    state["current_step"] = "Vaqtincha to'xtatilgan (PAUSE)"
    save_state(state)
    return True, "Jarayon to'xtatib turildi."

def resume_worker():
    return start_worker()

def stop_worker():
    state = load_state()
    pid = state.get("worker_pid")
    state["status"] = "IDLE"
    state["current_step"] = "To'xtatildi"
    state["worker_pid"] = None
    save_state(state)
    if pid and is_pid_alive(pid):
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid), "/T"], capture_output=True, timeout=5)
        except Exception:
            pass
    try:
        em = EmulatorManager()
        em.remove_phone("CyberWorker")
    except Exception:
        pass
    return True, "Jarayon to'xtatildi."

class AppWorker:
    def __init__(self, apk_path=DEFAULT_APK):
        self.apk_path = os.path.abspath(apk_path)
        self.emulator = EmulatorManager()
        self.sheets = SheetsManager()
        self.should_stop = False
        self.state = load_state()
        self.node_cfg = get_node_config()

    def add_log(self, message):
        clean_msg = re.sub(r"<[^>]+>", "", str(message))
        if len(clean_msg) > 300:
            clean_msg = clean_msg[:300] + "..."
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {clean_msg}"
        print(entry, flush=True)
        self.state = load_state()
        if "logs" not in self.state:
            self.state["logs"] = []
        self.state["logs"].append(entry)
        if len(self.state["logs"]) > 200:
            self.state["logs"] = self.state["logs"][-200:]
        save_state(self.state)

    def send_heartbeat(self, status_label="Ishlamoqda", emulator_name="LDPlayer_0"):
        try:
            active_ip = self.state.get("current_ip") or get_public_ip() or "127.0.0.1"
            net_mode = self.state.get("network_mode", "USB_MOBILE")
            res = self.sheets.sync_fleet_heartbeat(
                node_name=self.node_cfg.get("node_name", "PC-NODE"),
                hwid=self.node_cfg.get("hwid", "HWID-DEFAULT"),
                license_key=self.node_cfg.get("license_key", "DEFAULT"),
                public_ip=active_ip,
                network_mode=net_mode,
                status_label=status_label,
                emulator_name=emulator_name,
                completed_today=self.state.get("completed_today", 0),
                failed_count=self.state.get("failed_count", 0),
                note=self.node_cfg.get("note", "")
            )

            # 1. License check (Killswitch)
            lic_st = res.get("license_status", "ACTIVE")
            if lic_st == "BLOCKED":
                self.add_log("[XAVFSIZLIK] Ushbu kompyuter litsenziyasi administrator tomonidan BLOKLANGAN!")
                self.should_stop = True
                self.state["status"] = "STOPPED"
                save_state(self.state)
                return False

            # 2. Remote command check
            cmd = res.get("command", "NONE")
            if cmd == "STOP":
                self.add_log("[MASOFAVIY BUYRUQ] Markaziy serverdan TO'XTATISH buyrug'i olindi.")
                self.should_stop = True
                self.state["status"] = "STOPPED"
                save_state(self.state)
                return False
            elif cmd == "PAUSE":
                self.add_log("[MASOFAVIY BUYRUQ] Markaziy serverdan PAUZA buyrug'i olindi.")
                self.state["status"] = "PAUSED"
                save_state(self.state)
            elif cmd == "START":
                if self.state.get("status") == "PAUSED":
                    self.add_log("[MASOFAVIY BUYRUQ] Markaziy serverdan ISHGA TUSHIRISH buyrug'i olindi.")
                    self.state["status"] = "RUNNING"
                    save_state(self.state)

            return True
        except Exception:
            return True

    def run_loop(self, stay_open_sec=15, delay_between=10):
        self.state = load_state()
        self.state["worker_pid"] = os.getpid()
        self.state["status"] = "RUNNING"
        save_state(self.state)

        self.add_log(f"=== CYBERCONTROL FARM ISHGA TUSHDI (PID: {os.getpid()}) ===")

        try:
            while not self.should_stop:
                self.state = load_state()
                status = self.state.get("status", "IDLE")

                if status in ("IDLE", "STOPPED"):
                    self.add_log("To'xtatish buyrug'i olindi.")
                    break

                if status == "PAUSED":
                    self.add_log("Jarayon PAUZA holatida kutilmoqda...")
                    while not self.should_stop:
                        time.sleep(1)
                        self.state = load_state()
                        cur_st = self.state.get("status")
                        if cur_st == "RUNNING":
                            self.add_log("Pauza bekor qilindi, ish davom ettirilmoqda.")
                            break
                        elif cur_st in ("IDLE", "STOPPED"):
                            self.should_stop = True
                            break
                    if self.should_stop:
                        break

                # Check limit
                completed = self.state.get("completed_today", 0)
                limit = self.state.get("target_limit", 20)
                if completed >= limit:
                    self.add_log(f"Kunlik reja to'liq bajarildi! ({completed}/{limit})")
                    self.state["status"] = "COMPLETED"
                    self.state["current_step"] = "Reja bajarildi"
                    save_state(self.state)
                    break

                # 1. Decode QR Code (Dynamic)
                try:
                    qr_info = decode_qr()
                    ref_url = qr_info["raw_url"]
                    pkg_name = qr_info["package_name"]
                    self.state["referral_url"] = ref_url
                    save_state(self.state)
                    self.add_log(f"QR kod tekshirildi: {qr_info['image_file']} -> {ref_url}")
                except Exception as e:
                    self.add_log(f"Xatolik: QR kodni o'qib bo'lmadi: {e}")
                    time.sleep(5)
                    continue

                # 2. IP va Tarmoqni tayyorlash (Foydalanuvchi tanlagan rejim)
                iteration_num = self.state.get("completed_today", 0) + 1
                net_mode = self.state.get("network_mode", "USB_MOBILE")
                self.add_log(f">>> {iteration_num}-telefon bo'yicha ish boshlandi (Reja: {limit} ta | Rejim: {net_mode})")
                self.state["current_step"] = f"{iteration_num}-qurilma uchun tarmoq tayyorlanmoqda"
                save_state(self.state)

                if not self.send_heartbeat(status_label=f"{iteration_num}-qurilma sozlanmoqda"):
                    break

                old_ip = self.state.get("current_ip")
                active_ip, active_proxy = prepare_network_for_cycle(
                    mode=net_mode,
                    emulator=self.emulator,
                    worker_name="CyberWorker",
                    old_ip=old_ip,
                    logger=lambda m: self.add_log(m)
                )
                self.state = load_state()
                clean_ip = None
                if active_ip:
                    m_ip = re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", str(active_ip))
                    if m_ip:
                        clean_ip = m_ip.group(0)
                verified_ip = clean_ip or get_public_ip() or "Aniqlanmadi"
                self.state["current_ip"] = verified_ip
                self.state["current_step"] = f"{iteration_num}-qurilma sozlanmoqda (IP: {verified_ip})"
                save_state(self.state)

                # 3. Execute install cycle
                def logger(m):
                    self.add_log(m)

                try:
                    ok, identity, msg = self.emulator.execute_install_cycle(
                        referral_url=ref_url,
                        apk_path=self.apk_path,
                        package_name=pkg_name,
                        worker_name="CyberWorker",
                        stay_open_sec=stay_open_sec,
                        logger_callback=logger,
                        proxy=active_proxy
                    )
                    self.state = load_state()
                    self.state["current_device"] = identity

                    # 4. Log to Google Sheets (Haqiqiy alohida IP bilan)
                    final_ip_recorded = verified_ip if verified_ip != "Aniqlanmadi" else (get_public_ip() or "Mobil IP")
                    status_str = "MUVAFFAQINLI" if ok else f"XATO: {msg}"
                    chosen_cat = identity.get("category", "Nafaqa yoshiga yetmagan fuqaro")
                    try:
                        self.sheets.log_installation(
                            model=f"{identity['manufacturer'].title()} {identity['model']}",
                            imei=identity["imei"],
                            android_id=identity["android_id"],
                            referral_url=ref_url,
                            category=chosen_cat,
                            ip_address=final_ip_recorded,
                            status=status_str
                        )
                        self.add_log(f"Google Sheets jadvaliga muvaffaqiyatli yozildi (Toifa: {chosen_cat} | IP: {final_ip_recorded})!")
                    except Exception as sheet_err:
                        self.add_log(f"Google Sheets yozishda ogohlantirish (Token muddati yoki ruxsat): {sheet_err}")

                    if ok:
                        self.state["completed_today"] = self.state.get("completed_today", 0) + 1
                    else:
                        self.state["failed_count"] = self.state.get("failed_count", 0) + 1

                    # 5. Telegram Push Notification
                    try:
                        from telegram_bot import send_telegram_broadcast
                        node_name = self.node_cfg.get("node_name", "PC-NODE")
                        now_time = datetime.datetime.now().strftime("%H:%M:%S")
                        if ok:
                            tg_text = (
                                f"🚀 <b>YANGI REFERAL QAYD ETILDI!</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"🖥️ <b>Tugun:</b> <code>{node_name}</code>\n"
                                f"📱 <b>Model:</b> {identity.get('display_name') or identity.get('model')}\n"
                                f"🌐 <b>IP:</b> <code>{final_ip_recorded}</code>\n"
                                f"🎯 <b>Toifa:</b> {chosen_cat}\n"
                                f"📊 <b>Progress:</b> {self.state.get('completed_today', 0)} / {limit} ta\n"
                                f"🕒 <b>Vaqt:</b> {now_time}"
                            )
                        else:
                            tg_text = (
                                f"⚠️ <b>REFERALDA XATOLIK</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"🖥️ <b>Tugun:</b> <code>{node_name}</code>\n"
                                f"❌ <b>Sabab:</b> {msg}\n"
                                f"🕒 <b>Vaqt:</b> {now_time}"
                            )
                        send_telegram_broadcast(tg_text)
                    except Exception:
                        pass

                    save_state(self.state)
                    self.send_heartbeat(status_label="Kutishda")

                except Exception as ex:
                    self.add_log(f"O'rnatish siklida kutilmagan xatolik: {ex}")
                    self.state = load_state()
                    self.state["failed_count"] = self.state.get("failed_count", 0) + 1
                    save_state(self.state)

                # Delay between cycles (responsive)
                self.state = load_state()
                if self.state.get("status") == "RUNNING" and self.state.get("completed_today", 0) < self.state.get("target_limit", 20):
                    self.add_log(f"Keyingi telefon ochilishidan oldin {delay_between} soniya tabiiy kechikish kutilmoqda...")
                    for _ in range(delay_between):
                        time.sleep(1)
                        st = load_state()
                        if st.get("status") in ("IDLE", "STOPPED", "PAUSED"):
                            break

        finally:
            self.state = load_state()
            self.state["worker_pid"] = None
            if self.state.get("status") == "RUNNING":
                self.state["status"] = "IDLE"
            self.state["current_step"] = "To'xtatilgan"
            save_state(self.state)
            self.send_heartbeat(status_label="To'xtatilgan")
            self.add_log("Worker jarayoni yakunlandi.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CyberControl Device Farm Worker")
    parser.add_argument("--run", action="store_true", help="Start the worker automation loop")
    parser.add_argument("--limit", type=int, default=None, help="Set target limit")
    parser.add_argument("--stay-open", type=int, default=15, help="Seconds app stays open")
    parser.add_argument("--delay", type=int, default=10, help="Delay between devices in seconds")
    parser.add_argument("--status", action="store_true", help="Print current status")
    parser.add_argument("--pause", action="store_true", help="Pause worker")
    parser.add_argument("--resume", action="store_true", help="Resume worker")
    parser.add_argument("--stop", action="store_true", help="Stop worker")
    parser.add_argument("--set-key", type=str, default=None, help="Set license key")
    parser.add_argument("--set-name", type=str, default=None, help="Set node name")
    parser.add_argument("--node-info", action="store_true", help="Print node HWID and license info")

    args = parser.parse_args()

    if args.set_key or args.set_name:
        from license_manager import save_node_config
        cfg = get_node_config()
        if args.set_key:
            cfg["license_key"] = args.set_key.strip()
            print(f"[Litsenziya] Yangi kalit saqlandi: {cfg['license_key']}")
        if args.set_name:
            cfg["node_name"] = args.set_name.strip()
            print(f"[Tugun] Yangi nom saqlandi: {cfg['node_name']}")
        save_node_config(cfg)
        sys.exit(0)
    elif args.node_info:
        cfg = get_node_config()
        print("========================================")
        print("  CYBERFARM TUGUN MA'LUMOTLARI")
        print("========================================")
        print(f"  Kompyuter Nomi (Node ID): {cfg.get('node_name')}")
        print(f"  Apparat Kodi (HWID):      {cfg.get('hwid')}")
        print(f"  Litsenziya Kaliti:        {cfg.get('license_key')}")
        print(f"  Izoh / Mas'ul:            {cfg.get('note')}")
        print("========================================")
        sys.exit(0)

    if args.status:
        st = load_state()
        pid = st.get("worker_pid")
        alive = is_pid_alive(pid)
        st_uz = {"RUNNING": "Ishlamoqda", "PAUSED": "Pauzada", "COMPLETED": "Tugatildi", "IDLE": "Kutishda"}.get(st.get('status'), "Kutishda")
        print(f"Holat: {st_uz} | PID: {pid} (Tirik: {alive}) | Bajarilgan: {st.get('completed_today')}/{st.get('target_limit')}")
    elif args.pause:
        pause_worker()
        print("Pauza buyrug'i yuborildi.")
    elif args.resume:
        resume_worker()
        print("Davom ettirish buyrug'i yuborildi.")
    elif args.stop:
        stop_worker()
        print("To'xtatish buyrug'i yuborildi.")
    elif args.run:
        if args.limit:
            st = load_state()
            st["target_limit"] = args.limit
            save_state(st)
        w = AppWorker()
        w.run_loop(stay_open_sec=args.stay_open, delay_between=args.delay)
    else:
        st = load_state()
        print("CyberControl AppWorker tayyor. Buyruqlar: --run, --status, --pause, --resume, --stop")
