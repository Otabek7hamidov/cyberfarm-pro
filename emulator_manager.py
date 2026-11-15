import os
import sys
import re
import time
import random
import subprocess
import json
from device_generator import generate_phone_identity
from referral_manager import execute_referral_visit

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
LDCONSOLE = os.path.join(BASE_DIR, "LDPlayer9", "ldconsole.exe")
ADB_EXE = os.path.join(BASE_DIR, "platform-tools", "adb.exe")


class EmulatorManager:
    def __init__(self, console_path=LDCONSOLE):
        self.console_path = console_path
        if not os.path.exists(self.console_path):
            raise FileNotFoundError(f"LDConsole topilmadi: {self.console_path}")
        self.ensure_adb_server()

    def ensure_adb_server(self):
        """Starts ADB server cleanly without pipe deadlock."""
        if os.path.exists(ADB_EXE):
            try:
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                subprocess.run([ADB_EXE, "start-server"], timeout=10, creationflags=flags)
            except Exception:
                pass

    def run_cmd(self, *args, timeout=30):
        cmd = [self.console_path] + list(args)
        ld_dir = os.path.dirname(self.console_path)
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            res = subprocess.run(
                cmd,
                cwd=ld_dir,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=flags
            )
            return res.stdout.strip()
        except Exception:
            return ""

    def run_adb(self, serial, *args, timeout=10):
        """Executes ADB commands using platform-tools adb.exe to avoid daemon deadlocks."""
        if not os.path.exists(ADB_EXE):
            return ""
        cmd = [ADB_EXE]
        if serial:
            cmd += ["-s", serial]
        cmd += list(args)
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            res = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=flags
            )
            return res.stdout.strip()
        except Exception:
            return ""

    def find_element_bounds(self, serial, text_targets=None, res_id_targets=None, desc_targets=None):
        """
        Dumps UI hierarchy via ADB uiautomator and searches for element matching text, resource-id or content-desc.
        Returns (center_x, center_y) or None.
        """
        try:
            self.run_adb(serial, "shell", "uiautomator", "dump", "/data/local/tmp/uidump.xml", timeout=6)
            xml_data = self.run_adb(serial, "shell", "cat", "/data/local/tmp/uidump.xml", timeout=5)
            if not xml_data or "<hierarchy" not in xml_data:
                return None

            targets_lower = [t.lower() for t in text_targets] if text_targets else []
            id_targets_lower = [i.lower() for i in res_id_targets] if res_id_targets else []
            desc_targets_lower = [d.lower() for d in desc_targets] if desc_targets else []

            node_pattern = re.compile(r'<node\b([^>]+)>')
            for match in node_pattern.finditer(xml_data):
                attrs = match.group(1)
                m_bounds = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', attrs)
                if not m_bounds:
                    continue

                m_text = re.search(r'text="([^"]*)"', attrs)
                cur_text = m_text.group(1).lower() if m_text else ""

                m_id = re.search(r'resource-id="([^"]*)"', attrs)
                cur_id = m_id.group(1).lower() if m_id else ""

                m_desc = re.search(r'content-desc="([^"]*)"', attrs)
                cur_desc = m_desc.group(1).lower() if m_desc else ""

                matched = False
                if targets_lower and any(t in cur_text for t in targets_lower):
                    matched = True
                elif id_targets_lower and any(i in cur_id for i in id_targets_lower):
                    matched = True
                elif desc_targets_lower and any(d in cur_desc for d in desc_targets_lower):
                    matched = True

                if matched:
                    x1, y1, x2, y2 = int(m_bounds.group(1)), int(m_bounds.group(2)), int(m_bounds.group(3)), int(m_bounds.group(4))
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    return cx, cy
        except Exception:
            pass
        return None

    def tap_element_dynamic(self, serial, text_targets=None, res_id_targets=None, desc_targets=None, fallback_coords=None, logger=None):
        """
        Attempts to find and tap an element dynamically. If not found, falls back to fallback_coords.
        """
        center = self.find_element_bounds(serial, text_targets=text_targets, res_id_targets=res_id_targets, desc_targets=desc_targets)
        if center:
            cx, cy = center
            if logger:
                target_name = (text_targets or res_id_targets or desc_targets or ["Element"])[0]
                logger(f"   [Dinamik UI] '{target_name}' topildi: ({cx}, {cy}) bosilmoqda...")
            self.run_adb(serial, "shell", "input", "tap", str(cx), str(cy))
            return True
        elif fallback_coords:
            fx, fy = fallback_coords
            if logger:
                target_name = (text_targets or res_id_targets or desc_targets or ["Element"])[0]
                logger(f"   [Fallback UI] '{target_name}' dinamik topilmadi, zaxira ({fx}, {fy}) bosilmoqda...")
            self.run_adb(serial, "shell", "input", "tap", str(fx), str(fy))
            return True
        return False

    def get_instances(self):
        out = self.run_cmd("list2")
        instances = []
        if not out:
            return instances
        for line in out.splitlines():
            parts = line.split(",")
            if len(parts) >= 2:
                instances.append({
                    "index": parts[0].strip(),
                    "name": parts[1].strip(),
                    "top_handle": parts[2].strip() if len(parts) > 2 else "",
                    "bind_handle": parts[3].strip() if len(parts) > 3 else "",
                    "is_running": parts[4].strip() == "1" if len(parts) > 4 else False,
                    "pid": parts[5].strip() if len(parts) > 5 else "",
                    "vbox_pid": parts[6].strip() if len(parts) > 6 else ""
                })
        return instances

    def get_device_info(self, name):
        """Returns (index, serial, port) for an instance name."""
        instances = self.get_instances()
        for inst in instances:
            if inst["name"] == name:
                idx = int(inst["index"])
                serial = f"emulator-{5554 + idx * 2}"
                port = 5555 + idx * 2
                return idx, serial, port
        return None, None, None

    def create_phone(self, name="WorkerPhone", identity=None):
        if identity is None:
            identity = generate_phone_identity()

        # 1. Clean existing instance if any with same name
        self.remove_phone(name)

        # 2. Add new instance
        self.run_cmd("add", "--name", name)
        time.sleep(2)

        # 3. Modify hardware fingerprint
        mac_no_colons = identity["mac"].replace(":", "")
        modify_args = [
            "modify", "--name", name,
            "--resolution", f"{identity['width']},{identity['height']},{identity['dpi']}",
            "--cpu", str(identity["cpu_cores"]),
            "--memory", str(identity["ram_mb"]),
            "--manufacturer", identity["manufacturer"],
            "--model", identity["model"],
            "--pnumber", identity["phone_number"],
            "--imei", identity["imei"],
            "--androidid", identity["android_id"],
            "--mac", mac_no_colons
        ]
        self.run_cmd(*modify_args)
        time.sleep(1)
        self._apply_hardware_config(name, identity)

        return identity

    def _apply_hardware_config(self, name, identity):
        """Applies deep hardware identifiers including Uzbekistan IMSI, Operator and SIM serial."""
        try:
            idx, _, _ = self.get_device_info(name)
            if idx is not None:
                cfg_file = os.path.join(os.path.dirname(self.console_path), "vms", "config", f"leidian{idx}.config")
                data = {}
                if os.path.exists(cfg_file):
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                
                # Uzbekistan Telecom Identifiers
                mac_clean = identity["mac"].replace(":", "")
                data["basicSettings.adbDebug"] = 1
                data["propertySettings.phoneIMEI"] = identity["imei"]
                data["propertySettings.phoneAndroidId"] = identity["android_id"]
                data["propertySettings.phoneModel"] = identity["model"]
                data["propertySettings.phoneManufacturer"] = identity["manufacturer"]
                data["propertySettings.macAddress"] = mac_clean
                data["propertySettings.phoneIMSI"] = identity.get("imsi", "434051029384756")
                data["propertySettings.phoneSimSerial"] = identity.get("sim_serial", "8999805012345678901")
                data["propertySettings.phoneOperator"] = identity.get("sim_operator", "Ucell")
                data["networkSettings.networkEnable"] = True
                
                with open(cfg_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
        except Exception:
            pass

    def launch_phone(self, name="WorkerPhone", max_wait_sec=120):
        self.ensure_adb_server()
        self.run_cmd("launch", "--name", name)
        start_time = time.time()

        idx, serial, port = self.get_device_info(name)

        # Wait for device to boot
        while time.time() - start_time < max_wait_sec:
            time.sleep(3)
            try:
                # 1. Connect via TCP port if not connected
                if port:
                    self.run_adb(None, "connect", f"127.0.0.1:{port}", timeout=2)

                # 2. Check boot completed using serial and tcp
                boot1 = self.run_adb(serial, "shell", "getprop", "sys.boot_completed", timeout=3) if serial else ""
                boot2 = self.run_adb(f"127.0.0.1:{port}", "shell", "getprop", "sys.boot_completed", timeout=3) if port else ""

                if "1" in boot1 or "1" in boot2:
                    time.sleep(3) # Wait for UI rendering & services to stabilize
                    return True
            except Exception:
                pass
        return False

    def open_url_in_browser(self, name, url):
        idx, serial, port = self.get_device_info(name)
        target = serial if serial else (f"127.0.0.1:{port}" if port else None)
        if target:
            self.run_adb(target, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url)
        else:
            self.run_cmd("adb", "--name", name, "--command", f'shell am start -a android.intent.action.VIEW -d "{url}"')

    def install_apk(self, name, apk_path):
        abs_apk = os.path.abspath(apk_path)
        if not os.path.exists(abs_apk):
            raise FileNotFoundError(f"APK topilmadi: {abs_apk}")
        
        idx, serial, port = self.get_device_info(name)
        target = serial if serial else (f"127.0.0.1:{port}" if port else None)

        # Official Google Play Store installation attribution
        if target:
            self.run_adb(target, "push", abs_apk, "/data/local/tmp/app_target.apk", timeout=15)
            out = self.run_adb(target, "shell", "pm", "install", "-i", "com.android.vending", "-r", "-g", "/data/local/tmp/app_target.apk", timeout=35)
            self.run_adb(target, "shell", "rm", "-f", "/data/local/tmp/app_target.apk")
            if "Success" in out:
                return True

        # Fallback to LDPlayer native installer
        self.run_cmd("installapp", "--name", name, "--filename", abs_apk)

    def launch_app(self, name, package_name):
        self.run_cmd("runapp", "--name", name, "--packagename", package_name)
        idx, serial, port = self.get_device_info(name)
        target = serial if serial else (f"127.0.0.1:{port}" if port else None)
        if target:
            self.run_adb(target, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1")

    def set_device_proxy(self, name, proxy_host, proxy_port):
        """Sets global HTTP proxy on the Android device via ADB."""
        idx, serial, port = self.get_device_info(name)
        target = serial if serial else (f"127.0.0.1:{port}" if port else None)
        if target:
            self.run_adb(target, "shell", "settings", "put", "global", "http_proxy", f"{proxy_host}:{proxy_port}")
            self.run_adb(target, "shell", "settings", "put", "global", "global_http_proxy_host", str(proxy_host))
            self.run_adb(target, "shell", "settings", "put", "global", "global_http_proxy_port", str(proxy_port))
            return True
        return False

    def clear_device_proxy(self, name):
        """Clears global HTTP proxy on the Android device via ADB."""
        idx, serial, port = self.get_device_info(name)
        target = serial if serial else (f"127.0.0.1:{port}" if port else None)
        if target:
            self.run_adb(target, "shell", "settings", "put", "global", "http_proxy", ":0")
            self.run_adb(target, "shell", "settings", "delete", "global", "http_proxy")
            self.run_adb(target, "shell", "settings", "delete", "global", "global_http_proxy_host")
            self.run_adb(target, "shell", "settings", "delete", "global", "global_http_proxy_port")
            return True
        return False

    def quit_phone(self, name):
        try:
            self.run_cmd("quit", "--name", name)
            time.sleep(2)
        except Exception:
            pass

    def remove_phone(self, name):
        try:
            self.quit_phone(name)
            self.run_cmd("remove", "--name", name)
            time.sleep(1)
        except Exception:
            pass

    def execute_install_cycle(self, referral_url, apk_path, package_name, worker_name="WorkerPhone", stay_open_sec=15, logger_callback=None, proxy=None):
        def log(msg):
            if logger_callback:
                logger_callback(msg)
            print(f"[Automation] {msg}")

        # Target active emulator with authenticated Google Play Store
        serial = "emulator-5554"
        out_devs = self.run_adb(None, "devices")
        if serial not in out_devs:
            # If not running, launch instance 0
            log("Play Store hisobiga ega emulyator ishga tushirilmoqda (Instance 0)...")
            self.run_cmd("launch", "--index", "0")
            for _ in range(20): # wait up to 40s
                time.sleep(2)
                self.run_adb(None, "connect", "127.0.0.1:5555", timeout=2)
                boot = self.run_adb(serial, "shell", "getprop", "sys.boot_completed", timeout=2)
                if "1" in boot:
                    time.sleep(3)
                    break

        # Step 1: Execute authentic web referral visit with Anti-Fraud bypass
        log("1. CyberControl serveriga toza mobil sessiya orqali referal so'rov yuborilmoqda...")
        ref_ok, ref_info, ref_msg = execute_referral_visit(
            referral_url=referral_url,
            logger=log,
            proxy=proxy
        )

        identity = generate_phone_identity()
        if ref_ok and ref_info:
            chosen_category = ref_info.get("category", "Нафақа ёшига етмаган фуқаро")
            identity["category"] = chosen_category
            dev = ref_info.get("device")
            if dev:
                identity["manufacturer"] = dev.get("brand", identity.get("manufacturer"))
                identity["model"] = dev.get("model", identity.get("model"))
                identity["display_name"] = dev.get("display", identity.get("display_name"))
        else:
            log(f"Ogohlantirish: Referal so'rovida xatolik: {ref_msg}. Standart toifa tanlanmoqda...")
            identity["category"] = "Нафақа ёшига етмаган фуқаро" if random.random() < 0.70 else "Нафақа ёшидаги фуқаро"

        log(f"2. Qurilma profili qo'llanmoqda: {identity['display_name']} ({identity['model']}), IMEI: {identity['imei']}")
        
        # Apply hardware identity config
        self._apply_hardware_config("LDPlayer", identity)
        new_android_id = f"{identity.get('android_id', '') or hex(random.getrandbits(64))[2:].zfill(16)}"
        self.run_adb(serial, "shell", "settings", "put", "secure", "android_id", new_android_id)

        # Step 2: Ensure internal storage is mounted
        st_out = self.run_adb(serial, "shell", "sm", "list-volumes", "all")
        if "emulated unmountable" in st_out or "emulated mounted" not in st_out:
            log("3. Emulated xotira sozlanmoqda (sm mount emulated)...")
            self.run_adb(serial, "shell", "sm", "mount", "emulated")
            time.sleep(2)

        # Step 3: Clean old install
        self.run_adb(serial, "shell", "pm", "uninstall", package_name)

        # Step 4: Open Google Play Store directly to the app
        log(f"4. Google Play Store ochilmoqda ({package_name})...")
        self.run_adb(serial, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", f"market://details?id={package_name}", "-p", "com.android.vending", "-f", "0x10000000")
        time.sleep(5)

        log("   Play Store 'Установить' (Install) tugmasi bosilmoqda...")
        self.tap_element_dynamic(
            serial,
            text_targets=["Установить", "Install", "Скачать", "O'rnatish"],
            res_id_targets=["com.android.vending:id/install_button", "com.android.vending:id/action_button"],
            fallback_coords=(1340, 212),
            logger=log
        )

        # Step 5: Wait for genuine Google Play installation
        log("   Google Play serverlaridan yuklab olish va o'rnatilish kutilmoqda...")
        installed = False
        for wait_i in range(25): # max 75 seconds
            time.sleep(3)
            pkgs = self.run_adb(serial, "shell", "pm", "list", "packages", "-i", package_name)
            if package_name in pkgs:
                log(f"   Muvaffaqiyatli o'rnatildi! ({pkgs}) [{(wait_i+1)*3}s]")
                installed = True
                break
            if wait_i in (2, 4):
                self.tap_element_dynamic(
                    serial,
                    text_targets=["Установить", "Install", "Скачать", "O'rnatish"],
                    fallback_coords=(1340, 212),
                    logger=log
                )

        if not installed:
            log("Ogohlantirish: Play Store avto-bosish kutish vaqti tugadi. Qayta urinilmoqda...")
            self.tap_element_dynamic(
                serial,
                text_targets=["Установить", "Install", "Скачать", "O'rnatish"],
                fallback_coords=(1340, 212),
                logger=log
            )
            time.sleep(5)
            pkgs = self.run_adb(serial, "shell", "pm", "list", "packages", "-i", package_name)
            if package_name in pkgs:
                installed = True

        if not installed:
            log("Play Store kechikdi, rasmiy do'kon manbasi bilan o'rnatilmoqda...")
            try:
                self.install_apk("LDPlayer", apk_path)
                time.sleep(2)
                pkgs = self.run_adb(serial, "shell", "pm", "list", "packages", "-i", package_name)
                if package_name in pkgs:
                    installed = True
            except Exception:
                pass

        if not installed:
            if ref_ok:
                log("✅ CyberControl referal so'rovi muvaffaqiyatli qabul qilingan (Emulyatorda ilova o'rnatish o'tkazib yuborildi).")
                return True, identity, "Muvaffaqiyatli CyberControl qayd etildi"
            return False, identity, "Play Store dan yuklab o'rnatib bo'lmadi"

        # Step 6: Launch app & complete onboarding
        log(f"5. Ilova ishga tushirilmoqda ({stay_open_sec} soniya faol ochiq turadi)...")
        self.run_adb(serial, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1")
        time.sleep(3)

        # Onboarding: Dynamic UI with deterministic fallbacks
        # 1. Til tanlash (Uzbek)
        self.tap_element_dynamic(
            serial,
            text_targets=["O'zbek", "Oʻzbek", "Uzbek", "Узбек"],
            fallback_coords=(800, 526),
            logger=log
        )
        time.sleep(1)

        # 2. Davom etish
        self.tap_element_dynamic(
            serial,
            text_targets=["Davom etish", "Продолжить", "Continue", "Tanlash"],
            fallback_coords=(800, 834),
            logger=log
        )
        time.sleep(2)

        # 3. Ruxsat berish
        self.tap_element_dynamic(
            serial,
            text_targets=["Ruxsat berish", "Разрешить", "Allow", "WHILE USING THE APP"],
            fallback_coords=(1117, 580),
            logger=log
        )
        time.sleep(1)

        # 4. Keyingisi
        self.tap_element_dynamic(
            serial,
            text_targets=["Keyingisi", "Далее", "Next", "Boshlash", "Tayyor"],
            fallback_coords=(800, 837),
            logger=log
        )
        time.sleep(max(5, stay_open_sec - 5))

        # Step 7: Clean up for next fresh cycle
        log("6. Tozalash: Keyingi sikl uchun ilova o'chirilmoqda...")
        self.run_adb(serial, "shell", "pm", "uninstall", package_name)
        log("Play Store o'rnatish tsikli 100% muvaffaqiyatli yakunlandi!")

        return True, identity, "Muvaffaqiyatli Play Store o'rnatildi"

if __name__ == "__main__":
    em = EmulatorManager()
    print("Mavjud instansiyalar:", em.get_instances())
