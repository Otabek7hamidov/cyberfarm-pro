import os
import sys
import json
import webbrowser
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import InstalledAppFlow
import gspread

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
AUTHORIZED_USER_FILE = os.path.join(BASE_DIR, "authorized_user.json")
OAUTH_URL_FILE = os.path.join(BASE_DIR, "oauth_url.txt")
CODE_FILE = os.path.join(BASE_DIR, "oauth_code.txt")
PORT = 8088

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

received_code = None
server_instance = None

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        global received_code
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if "code" in qs:
            received_code = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>CyberControl - Ruxsat Berildi</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #F8FAFC; }
                    .card { background: white; padding: 2.5rem; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; max-width: 480px; }
                    h2 { color: #16A34A; margin-bottom: 0.5rem; }
                    p { color: #475569; font-size: 1.05rem; }
                    .btn { display: inline-block; margin-top: 1.5rem; padding: 0.75rem 1.5rem; background: #2563EB; color: white; border-radius: 8px; text-decoration: none; font-weight: 600; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>Avtorizatsiya muvaffaqiyatli yakunlandi!</h2>
                    <p>Google Sheets jadvaliga ulanish uchun ruxsat saqlandi.</p>
                    <p>Ushbu oynani yopishingiz va Boshqaruv Paneliga qaytishingiz mumkin.</p>
                    <a class="btn" href="http://localhost:8501">Boshqaruv Paneliga o'tish</a>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Xatolik: Kod olinmadi.")

def run_oauth_flow():
    global received_code, server_instance

    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"[XATO] {CLIENT_SECRET_FILE} topilmadi!", flush=True)
        return False

    if os.path.exists(CODE_FILE):
        try:
            os.remove(CODE_FILE)
        except Exception:
            pass

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    flow.redirect_uri = f"http://localhost:{PORT}/"
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")

    with open(OAUTH_URL_FILE, "w", encoding="utf-8") as f:
        f.write(auth_url)

    print("\n" + "=" * 76, flush=True)
    print("[OAUTH] GOOGLE SHEETS OAUTH HAVOLASI (YANGI):", flush=True)
    print(auth_url, flush=True)
    print("=" * 76 + "\n", flush=True)

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    try:
        server_instance = HTTPServer(("localhost", PORT), OAuthCallbackHandler)
    except Exception as e:
        print(f"[XATO] Port {PORT} ga ulanishda xato: {e}", flush=True)
        return False

    server_thread = threading.Thread(target=server_instance.serve_forever, daemon=True)
    server_thread.start()
    print(f"Server http://localhost:{PORT}/ manzilida javob kutmoqda...", flush=True)

    start_wait = time.time()
    max_wait = 300

    while time.time() - start_wait < max_wait:
        if received_code:
            break
        if os.path.exists(CODE_FILE):
            try:
                with open(CODE_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    if "code=" in content:
                        received_code = content.split("code=")[-1].split("&")[0]
                    else:
                        received_code = content
                    break
            except Exception:
                pass
        time.sleep(1)

    if not received_code:
        print("[XATO] Vaqt tugadi: Hech qanday avtorizatsiya kodi olinmadi.", flush=True)
        server_instance.shutdown()
        return False

    print("\nKod qabul qilindi, token olinmoqda...", flush=True)
    try:
        flow.fetch_token(code=received_code)
        creds = flow.credentials

        with open(AUTHORIZED_USER_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        print(f"[SUCCESS] Yangi {AUTHORIZED_USER_FILE} saqlandi!", flush=True)

        for temp_f in [OAUTH_URL_FILE, CODE_FILE]:
            if os.path.exists(temp_f):
                try:
                    os.remove(temp_f)
                except Exception:
                    pass

        gc = gspread.authorize(creds)
        sh = gc.open_by_key("1SeiE-OPG8H3nJz53OibyOkMqOdrFdHKSeKcaCkT-A_g")
        print(f"[SUCCESS] Google Sheet jadvaliga muvaffaqiyatli ulandi: '{sh.title}'", flush=True)
        return True
    except Exception as err:
        print(f"[XATO] Token olishda xatolik: {err}", flush=True)
        return False
    finally:
        server_instance.shutdown()

if __name__ == "__main__":
    run_oauth_flow()
