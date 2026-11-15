import os
import sys
import json
import time
import datetime
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
AUTHORIZED_USER_FILE = os.path.join(BASE_DIR, "authorized_user.json")
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "service_account.json")

SPREADSHEET_ID = "1SeiE-OPG8H3nJz53OibyOkMqOdrFdHKSeKcaCkT-A_g"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

FLEET_HEADERS = [
    "Node ID",
    "HWID",
    "Litsenziya Kaliti",
    "Holati",
    "Tarmoq Rejimi",
    "Oxirgi IP",
    "Emulyator",
    "Muvaffaqiyatli",
    "Xatolik",
    "Oxirgi Aloqa",
    "Masofaviy Buyruq",
    "Izoh"
]

class SheetsManager:
    def __init__(self, spreadsheet_id=SPREADSHEET_ID):
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.sheet = None
        self.worksheet = None
        self.fleet_worksheet = None

    def get_credentials(self, interactive=False):
        creds = None
        # 0. Try Streamlit Secrets (for 24/7 Streamlit Community Cloud deployment)
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                from google.oauth2.service_account import Credentials as ServiceCredentials
                sa_info = dict(st.secrets["gcp_service_account"])
                creds = ServiceCredentials.from_service_account_info(sa_info, scopes=SCOPES)
                return creds
        except Exception:
            pass

        # 1. Try enterprise-grade Service Account (most secure, no personal Drive access leak)
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            try:
                from google.oauth2.service_account import Credentials as ServiceCredentials
                creds = ServiceCredentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
                return creds
            except Exception as sa_err:
                print(f"[Sheets] Service account faylida ogohlantirish: {sa_err}")
                creds = None

        # 2. Try authorized_user.json (Personal OAuth token)
        if os.path.exists(AUTHORIZED_USER_FILE):
            try:
                with open(AUTHORIZED_USER_FILE, "r") as f:
                    info = json.load(f)
                creds = Credentials.from_authorized_user_info(info, SCOPES)
                # Verify if token is valid or refreshable
                from google.auth.transport.requests import Request
                if creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        with open(AUTHORIZED_USER_FILE, "w") as f:
                            f.write(creds.to_json())
                    except Exception as refresh_err:
                        print(f"[Sheets] Token yangilashda vaqtinchalik tarmoq xatosi: {refresh_err}")
            except Exception as e:
                print(f"[Sheets] Token faylida xato: {e}")
                creds = None

        # 2. If invalid and interactive, trigger OAuth flow using client_secret.json
        if not creds and os.path.exists(CLIENT_SECRET_FILE):
            if interactive:
                print("[Sheets] Brauzer orqali yangi avtorizatsiya boshlanmoqda...")
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(AUTHORIZED_USER_FILE, "w") as f:
                    f.write(creds.to_json())
                print("[Sheets] Yangi authorized_user.json saqlandi!")

        return creds

    def connect(self, interactive=False):
        creds = self.get_credentials(interactive=interactive)
        if not creds:
            return False, "Google avtorizatsiyasi mavjud emas yoki token muddati o'tgan."

        try:
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(self.spreadsheet_id)
            self.worksheet = self.sheet.get_worksheet(0)
            self._ensure_header()
            self._ensure_fleet_worksheet()
            return True, f"Google Sheet ga ulandi: {self.sheet.title}"
        except Exception as e:
            return False, f"Ulanishda xatolik: {e}"

    def _ensure_header(self):
        headers = ["№", "Sana / Vaqt", "Telefon Modeli", "IMEI", "Android ID", "Referal Link", "Tanlangan Toifa", "IP Manzil", "Holati"]
        try:
            current_headers = self.worksheet.row_values(1)
            if not current_headers:
                self.worksheet.append_row(headers)
            elif "Tanlangan Toifa" not in current_headers:
                if "Referal Link" in current_headers:
                    ref_idx = current_headers.index("Referal Link") + 1
                    self.worksheet.insert_cols([["Tanlangan Toifa"]], col=ref_idx + 1)
                else:
                    self.worksheet.update("A1:I1", [headers])
        except Exception as e:
            print(f"[Sheets] Header tekshirishda ogohlantirish: {e}")

    def _ensure_fleet_worksheet(self):
        try:
            titles = [w.title for w in self.sheet.worksheets()]
            if "Fleet_Nodes" in titles:
                self.fleet_worksheet = self.sheet.worksheet("Fleet_Nodes")
            else:
                self.fleet_worksheet = self.sheet.add_worksheet(title="Fleet_Nodes", rows=100, cols=12)
                self.fleet_worksheet.append_row(FLEET_HEADERS)
        except Exception as e:
            print(f"[Sheets] Fleet_Nodes varag'ini tekshirishda xato: {e}")

    def log_installation(self, model, imei, android_id, referral_url, category="Nafaqa yoshiga yetmagan fuqaro", ip_address=None, status="MUVAFFAQINLI"):
        if not self.worksheet:
            ok, msg = self.connect()
            if not ok:
                raise ConnectionError(msg)

        if not ip_address or ip_address in ("127.0.0.1", "localhost", "None", ""):
            try:
                from ip_manager import get_public_ip
                ip_address = get_public_ip() or "Mobil IP"
            except Exception:
                ip_address = "Mobil IP"

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        last_err = None
        for attempt in range(3):
            try:
                # Fast row count using only first column instead of fetching entire sheet
                try:
                    row_num = len(self.worksheet.col_values(1))
                except Exception:
                    row_num = ""

                row = [
                    str(row_num),
                    now_str,
                    str(model),
                    str(imei),
                    str(android_id),
                    str(referral_url),
                    str(category),
                    str(ip_address),
                    str(status)
                ]
                self.worksheet.append_row(row)
                return row
            except Exception as e:
                last_err = e
                time.sleep(2)
                try:
                    self.connect()
                except Exception:
                    pass

        if last_err:
            raise last_err

    def get_today_count(self):
        try:
            if not self.worksheet:
                ok, _ = self.connect()
                if not ok:
                    return 0
            rows = self.worksheet.get_all_values()
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            count = 0
            for r in rows[1:]:
                if len(r) > 1 and r[1].startswith(today_str) and any("MUVAFFAQ" in str(x).upper() for x in r[6:]):
                    count += 1
            return count
        except Exception:
            return 0

    # ==========================================
    # FLEET MANAGEMENT & REMOTE LICENSE CONTROLS
    # ==========================================
    def sync_fleet_heartbeat(self, node_name, hwid, license_key, public_ip, network_mode, status_label, emulator_name, completed_today, failed_count, note=""):
        """
        Sends heartbeat from any machine node to Google Sheets.
        Reads remote control command and verifies license status.
        Returns: dict {"license_status": "ACTIVE"|"BLOCKED"|"PAUSED", "command": "NONE"|"STOP"|"START"|"PAUSE"}
        """
        if not self.fleet_worksheet:
            ok, msg = self.connect()
            if not ok:
                return {"license_status": "ACTIVE", "command": "NONE", "error": msg}

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            all_rows = self.fleet_worksheet.get_all_values()
            target_row_idx = None

            # Look for existing node by HWID (col 1 -> index 1) or node_name (col 0)
            for idx, r in enumerate(all_rows):
                if idx == 0:
                    continue
                if len(r) > 1 and (r[1].strip() == hwid.strip() or r[0].strip() == node_name.strip()):
                    target_row_idx = idx + 1 # 1-based index in gspread
                    break

            if target_row_idx is not None:
                # Node exists in sheet
                cur_row = all_rows[target_row_idx - 1]
                # Check current license status assigned by Admin
                sheet_license_status = cur_row[3].strip() if len(cur_row) > 3 else "ACTIVE"
                # Check pending remote command
                remote_command = cur_row[10].strip() if len(cur_row) > 10 else "NONE"
                if remote_command not in ("NONE", "", "-"):
                    # Consume command by resetting cell to NONE
                    try:
                        self.fleet_worksheet.update_cell(target_row_idx, 11, "NONE")
                    except Exception:
                        pass
                else:
                    remote_command = "NONE"

                # Update row data
                updated_row = [
                    node_name,
                    hwid,
                    license_key or (cur_row[2] if len(cur_row) > 2 else "DEFAULT"),
                    sheet_license_status, # Preserve admin license decision
                    network_mode,
                    public_ip,
                    emulator_name,
                    str(completed_today),
                    str(failed_count),
                    now_str,
                    "NONE", # Command consumed
                    note or (cur_row[11] if len(cur_row) > 11 else "")
                ]
                self.fleet_worksheet.update(f"A{target_row_idx}:L{target_row_idx}", [updated_row])
                return {"license_status": sheet_license_status, "command": remote_command}
            else:
                # New machine node connected for the first time
                new_row = [
                    node_name,
                    hwid,
                    license_key or "AUTO-REGISTERED",
                    "ACTIVE",
                    network_mode,
                    public_ip,
                    emulator_name,
                    str(completed_today),
                    str(failed_count),
                    now_str,
                    "NONE",
                    note or "Yangi ulangan tugun"
                ]
                self.fleet_worksheet.append_row(new_row)
                return {"license_status": "ACTIVE", "command": "NONE"}
        except Exception as e:
            return {"license_status": "ACTIVE", "command": "NONE", "error": str(e)}

    def get_all_fleet_nodes(self):
        """
        Retrieves all registered nodes from Google Sheets with parsed online/offline status.
        """
        if not self.fleet_worksheet:
            ok, msg = self.connect()
            if not ok:
                return []

        nodes = []
        try:
            all_rows = self.fleet_worksheet.get_all_values()
            if len(all_rows) <= 1:
                return []

            now = datetime.datetime.now()
            for r in all_rows[1:]:
                if not any(r):
                    continue
                node_name = r[0] if len(r) > 0 else "Noma'lum"
                hwid = r[1] if len(r) > 1 else "-"
                lic_key = r[2] if len(r) > 2 else "-"
                lic_status = r[3].strip() if len(r) > 3 else "ACTIVE"
                net_mode = r[4] if len(r) > 4 else "Lokal"
                public_ip = r[5] if len(r) > 5 else "-"
                emulator = r[6] if len(r) > 6 else "-"
                completed = int(r[7]) if len(r) > 7 and r[7].isdigit() else 0
                failed = int(r[8]) if len(r) > 8 and r[8].isdigit() else 0
                last_seen_str = r[9] if len(r) > 9 else ""
                remote_cmd = r[10] if len(r) > 10 else "NONE"
                note = r[11] if len(r) > 11 else ""

                # Compute is_online
                is_online = False
                seconds_ago = 999999
                if last_seen_str:
                    try:
                        last_seen_dt = datetime.datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
                        seconds_ago = int((now - last_seen_dt).total_seconds())
                        if seconds_ago <= 120: # Heartbeat within last 2 minutes
                            is_online = True
                    except Exception:
                        pass

                nodes.append({
                    "node_name": node_name,
                    "hwid": hwid,
                    "license_key": lic_key,
                    "license_status": lic_status,
                    "network_mode": net_mode,
                    "public_ip": public_ip,
                    "emulator": emulator,
                    "completed": completed,
                    "failed": failed,
                    "last_seen_str": last_seen_str,
                    "seconds_ago": seconds_ago,
                    "is_online": is_online,
                    "remote_cmd": remote_cmd,
                    "note": note
                })
        except Exception as e:
            print(f"[Sheets] get_all_fleet_nodes xatosi: {e}")

        return nodes

    def send_remote_command(self, target_hwid, command):
        """
        Sends a remote command (START, PAUSE, STOP) to a node via Google Sheets.
        """
        if not self.fleet_worksheet:
            ok, _ = self.connect()
            if not ok:
                return False

        try:
            all_rows = self.fleet_worksheet.get_all_values()
            for idx, r in enumerate(all_rows):
                if idx == 0:
                    continue
                if len(r) > 1 and (r[1].strip() == target_hwid.strip() or r[0].strip() == target_hwid.strip()):
                    self.fleet_worksheet.update_cell(idx + 1, 11, command.upper())
                    return True
        except Exception as e:
            print(f"[Sheets] Buyruq yuborishda xato: {e}")
        return False

    def set_node_license_status(self, target_hwid, new_status):
        """
        Updates node license status: ACTIVE, BLOCKED, PAUSED.
        """
        if not self.fleet_worksheet:
            ok, _ = self.connect()
            if not ok:
                return False

        try:
            all_rows = self.fleet_worksheet.get_all_values()
            for idx, r in enumerate(all_rows):
                if idx == 0:
                    continue
                if len(r) > 1 and (r[1].strip() == target_hwid.strip() or r[0].strip() == target_hwid.strip()):
                    self.fleet_worksheet.update_cell(idx + 1, 4, new_status.upper())
                    return True
        except Exception as e:
            print(f"[Sheets] Litsenziya holatini yangilashda xato: {e}")
        return False

if __name__ == "__main__":
    mgr = SheetsManager()
    ok, msg = mgr.connect(interactive=False)
    print("Status:", ok, msg)
