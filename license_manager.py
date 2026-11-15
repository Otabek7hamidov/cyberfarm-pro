import os
import sys
import json
import uuid
import socket
import hashlib
import random
import string

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "node_config.json")

def get_hwid() -> str:
    """Generates a persistent, deterministic Hardware ID (HWID) based on machine cryptography and motherboard/host."""
    raw_id = ""
    if sys.platform == "win32":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            guid = winreg.QueryValueEx(k, "MachineGuid")[0]
            raw_id += guid
        except Exception:
            pass

    if not raw_id:
        # Fallback to MAC and Hostname
        mac = uuid.getnode()
        raw_id = f"{mac}:{socket.gethostname()}"
    else:
        raw_id += f":{socket.gethostname()}"

    h = hashlib.sha256(raw_id.encode("utf-8")).hexdigest().upper()
    return f"HWID-{h[:4]}-{h[4:8]}-{h[8:12]}"

def generate_license_key(prefix: str = "CFARM") -> str:
    """Generates an aesthetic license key: CFARM-XXXX-YYYY-ZZZZ"""
    def chunk(n=4):
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))
    return f"{prefix}-{chunk()}-{chunk()}-{chunk()}"

def get_node_config() -> dict:
    """Loads existing node configuration or initializes a new one."""
    current_hwid = get_hwid()
    hostname = socket.gethostname()
    default_config = {
        "node_name": f"PC-{hostname.replace('DESKTOP-', '')[:10].upper()}",
        "hwid": current_hwid,
        "license_key": "ADMIN-MASTER-KEY",
        "note": "Asosiy boshqaruv tuguni"
    }

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["hwid"] = current_hwid # Always enforce real HWID
                if not data.get("license_key"):
                    data["license_key"] = default_config["license_key"]
                if not data.get("node_name"):
                    data["node_name"] = default_config["node_name"]
                return data
        except Exception:
            pass

    # Save default config
    save_node_config(default_config)
    return default_config

def save_node_config(config: dict):
    """Saves node configuration to node_config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[LicenseManager] Konfiguratsiya saqlashda xato: {e}")

if __name__ == "__main__":
    cfg = get_node_config()
    print("Node Config:", cfg)
    print("Namuna Litsenziya Kaliti:", generate_license_key())
