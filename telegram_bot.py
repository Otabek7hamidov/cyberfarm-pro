import os
import sys
import time
import json
import requests
from datetime import datetime
from sheets_manager import SheetsManager

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "telegram_config.json")

def load_config():
    default_config = {
        "bot_token": "",
        "admin_chat_ids": [],
        "notify_on_install": True,
        "web_panel_url": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_config.update(data)
                return default_config
        except Exception:
            pass
    return default_config

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Telegram] Konfiguratsiya saqlashda xato: {e}")

def send_telegram_broadcast(message, parse_mode="HTML"):
    """
    Sends notification to all admin chat IDs configured in telegram_config.json.
    """
    cfg = load_config()
    token = cfg.get("bot_token", "").strip()
    admins = cfg.get("admin_chat_ids", [])
    if not token or not admins:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    success = False
    for chat_id in admins:
        try:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            resp = requests.post(url, json=payload, timeout=6)
            if resp.status_code == 200:
                success = True
        except Exception:
            pass
    return success

class CyberFarmTelegramBot:
    def __init__(self):
        self.sheets = SheetsManager()
        self.last_update_id = 0
        self.running = True

    def get_api_url(self, method):
        cfg = load_config()
        token = cfg.get("bot_token", "").strip()
        return f"https://api.telegram.org/bot{token}/{method}"

    def send_message(self, chat_id, text, reply_markup=None, parse_mode="HTML"):
        url = self.get_api_url("sendMessage")
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            resp = requests.post(url, json=payload, timeout=8)
            return resp.json()
        except Exception as e:
            print(f"[Telegram] send_message xatosi: {e}")
            return None

    def edit_message(self, chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
        url = self.get_api_url("editMessageText")
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            resp = requests.post(url, json=payload, timeout=8)
            return resp.json()
        except Exception as e:
            print(f"[Telegram] edit_message xatosi: {e}")
            return None

    def answer_callback(self, callback_id, text=None, alert=False):
        url = self.get_api_url("answerCallbackQuery")
        payload = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = alert
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass

    def is_admin(self, chat_id):
        cfg = load_config()
        admins = cfg.get("admin_chat_ids", [])
        if not admins:
            # If no admins configured, auto-authorize the first user who starts the bot
            admins.append(chat_id)
            cfg["admin_chat_ids"] = admins
            save_config(cfg)
            return True
        return chat_id in admins or str(chat_id) in [str(a) for a in admins]

    def handle_start(self, chat_id):
        cfg = load_config()
        web_url = cfg.get("web_panel_url", "")
        msg = (
            "⚡ <b>CYBERFARM PRO — MARKAZIY BOSHQARUV BOTI</b>\n\n"
            "Ushbu bot orqali siz barcha filial kompyuterlarini (Fleet Nodes) "
            "dunyoning istalgan nuqtasidan turib, asosiy kompyuteringiz o'chiq bo'lsa ham "
            "24/7 online kuzatishingiz va boshqarishingiz mumkin.\n\n"
            "📋 <b>Asosiy Buyruqlar:</b>\n"
            "• /status — Barcha kompyuterlar holati va faolligi\n"
            "• /nodes — Kompyuterlarni masofadan boshqarish (Start, Pause, Stop, Bloklash)\n"
            "• /today — Bugungi umumiy hisobot va statistika\n"
            "• /help — Yordam va sozlamalar"
        )
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📊 Kompyuterlar Holati (/status)", "callback_data": "cmd_status"},
                    {"text": "🎮 Tugunlarni Boshqarish (/nodes)", "callback_data": "cmd_nodes"}
                ],
                [
                    {"text": "📈 Bugungi Hisobot", "callback_data": "cmd_today"}
                ]
            ]
        }
        if web_url:
            keyboard["inline_keyboard"].append([
                {"text": "🌐 Online Web Panelni Ochish", "web_app": {"url": web_url}}
            ])

        self.send_message(chat_id, msg, reply_markup=keyboard)

    def handle_status(self, chat_id, message_id=None):
        nodes = self.sheets.get_all_fleet_nodes()
        if not nodes:
            msg = "⚠️ <b>Hozircha birorta ham ulangan kompyuter topilmadi.</b>\nGoogle Sheets jadvalini tekshiring."
            reply_markup = {"inline_keyboard": [[{"text": "🔄 Yangilash", "callback_data": "cmd_status"}]]}
            if message_id:
                self.edit_message(chat_id, message_id, msg, reply_markup=reply_markup)
            else:
                self.send_message(chat_id, msg, reply_markup=reply_markup)
            return

        online_count = sum(1 for n in nodes if n["is_online"])
        total_completed = sum(n["completed"] for n in nodes)

        msg = (
            f"📊 <b>KOMPYUTERLAR FERMASI HOLATI (FLEET)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <b>Aktiv tugunlar:</b> {online_count} / {len(nodes)} ta\n"
            f"🎯 <b>Jami o'rnatishlar:</b> {total_completed} ta\n"
            f"🕒 <b>Oxirgi yangilanish:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        for n in nodes:
            status_icon = "🟢" if n["is_online"] else "🔴"
            lic_icon = "🔒" if n["license_status"] == "BLOCKED" else ("⏸️" if n["license_status"] == "PAUSED" else "✅")
            ago_str = f"{n['seconds_ago']} soniya oldin" if n['seconds_ago'] < 120 else f"{n['seconds_ago']//60} daqiqa oldin"
            
            msg += (
                f"{status_icon} <b>{n['node_name']}</b> ({lic_icon} {n['license_status']})\n"
                f"   • HWID: <code>{n['hwid']}</code>\n"
                f"   • IP: <code>{n['public_ip']}</code> ({n['network_mode']})\n"
                f"   • O'rnatishlar: <b>{n['completed']}</b> ta (Xato: {n['failed']})\n"
                f"   • Oxirgi aloqa: {ago_str}\n\n"
            )

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🔄 Yangilash", "callback_data": "cmd_status"},
                    {"text": "🎮 Boshqarish Pulti", "callback_data": "cmd_nodes"}
                ]
            ]
        }

        if message_id:
            self.edit_message(chat_id, message_id, msg, reply_markup=reply_markup)
        else:
            self.send_message(chat_id, msg, reply_markup=reply_markup)

    def handle_nodes_menu(self, chat_id, message_id=None):
        nodes = self.sheets.get_all_fleet_nodes()
        if not nodes:
            msg = "⚠️ Boshqarish uchun kompyuterlar ro'yxati bo'sh."
            if message_id:
                self.edit_message(chat_id, message_id, msg)
            else:
                self.send_message(chat_id, msg)
            return

        msg = "🎮 <b>MASOFAVIY BOSHQARUV PULTI</b>\nQuyidagi kompyuterlardan birini tanlang:"
        keyboard = []
        for n in nodes:
            st_dot = "🟢" if n["is_online"] else "⚪"
            btn_text = f"{st_dot} {n['node_name']} ({n['completed']} ta)"
            keyboard.append([{"text": btn_text, "callback_data": f"node_detail:{n['hwid']}"}])

        keyboard.append([{"text": "⬅️ Orqaga", "callback_data": "cmd_start"}])
        reply_markup = {"inline_keyboard": keyboard}

        if message_id:
            self.edit_message(chat_id, message_id, msg, reply_markup=reply_markup)
        else:
            self.send_message(chat_id, msg, reply_markup=reply_markup)

    def handle_node_detail(self, chat_id, message_id, hwid):
        nodes = self.sheets.get_all_fleet_nodes()
        target = next((n for n in nodes if n["hwid"] == hwid or n["node_name"] == hwid), None)
        if not target:
            self.handle_nodes_menu(chat_id, message_id)
            return

        st_text = "🟢 ONLINE" if target["is_online"] else "🔴 OFFLINE"
        msg = (
            f"🖥️ <b>TUGUN: {target['node_name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• Holat: <b>{st_text}</b>\n"
            f"• Litsenziya: <b>{target['license_status']}</b>\n"
            f"• Kalit: <code>{target['license_key']}</code>\n"
            f"• Apparat ID: <code>{target['hwid']}</code>\n"
            f"• Joriy IP: <code>{target['public_ip']}</code>\n"
            f"• Muvaffaqiyatli: <b>{target['completed']} ta</b>\n"
            f"• Xatoliklar: {target['failed']} ta\n"
            f"• Izoh: {target['note']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Masofaviy buyruq tanlang:</i>"
        )

        buttons = [
            [
                {"text": "▶️ Boshlash (Start)", "callback_data": f"cmd_act:{hwid}:START"},
                {"text": "⏸️ Pauza", "callback_data": f"cmd_act:{hwid}:PAUSE"}
            ],
            [
                {"text": "⏹️ To'xtatish (Stop)", "callback_data": f"cmd_act:{hwid}:STOP"}
            ]
        ]

        if target["license_status"] == "BLOCKED":
            buttons.append([{"text": "🔓 Blokdan Chiqarish", "callback_data": f"cmd_lic:{hwid}:ACTIVE"}])
        else:
            buttons.append([{"text": "🚫 Kompyuterni Bloklash", "callback_data": f"cmd_lic:{hwid}:BLOCKED"}])

        buttons.append([{"text": "⬅️ Ro'yxatga Qaytish", "callback_data": "cmd_nodes"}])

        reply_markup = {"inline_keyboard": buttons}
        self.edit_message(chat_id, message_id, msg, reply_markup=reply_markup)

    def handle_node_action(self, chat_id, message_id, callback_id, hwid, action):
        ok = self.sheets.send_remote_command(hwid, action)
        if ok:
            action_names = {
                "START": "▶️ ISHGA TUSHIRISH buyrug'i yuborildi!",
                "PAUSE": "⏸️ PAUZA buyrug'i yuborildi!",
                "STOP": "⏹️ TO'XTATISH buyrug'i yuborildi!"
            }
            self.answer_callback(callback_id, action_names.get(action, "Buyruq yuborildi!"), alert=False)
        else:
            self.answer_callback(callback_id, "Xatolik: Buyruqni yuborib bo'lmadi!", alert=True)
        time.sleep(1)
        self.handle_node_detail(chat_id, message_id, hwid)

    def handle_license_action(self, chat_id, message_id, callback_id, hwid, new_status):
        ok = self.sheets.set_node_license_status(hwid, new_status)
        if ok:
            alert_msg = "🚫 Kompyuter bloklandi! Uning dasturi bir zumda o'chadi." if new_status == "BLOCKED" else "🔓 Kompyuter qulfdan chiqarildi!"
            self.answer_callback(callback_id, alert_msg, alert=True)
        else:
            self.answer_callback(callback_id, "Xato: Litsenziyani yangilab bo'lmadi!", alert=True)
        time.sleep(1)
        self.handle_node_detail(chat_id, message_id, hwid)

    def handle_today(self, chat_id, message_id=None):
        today_count = self.sheets.get_today_count()
        msg = (
            f"📈 <b>BUGUNGI UMUMIY HISOBOT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 Sana: <b>{datetime.now().strftime('%Y-%m-%d')}</b>\n"
            f"✅ Jami muvaffaqiyatli o'rnatishlar: <b>{today_count} ta</b>\n"
            f"🔗 Google Sheet: <a href='https://docs.google.com/spreadsheets/d/{self.sheets.spreadsheet_id}/edit'>Jadvalni Ko'rish</a>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        reply_markup = {"inline_keyboard": [[{"text": "🔄 Yangilash", "callback_data": "cmd_today"}, {"text": "⬅️ Menyuga Qaytish", "callback_data": "cmd_start"}]]}
        if message_id:
            self.edit_message(chat_id, message_id, msg, reply_markup=reply_markup)
        else:
            self.send_message(chat_id, msg, reply_markup=reply_markup)

    def process_updates(self):
        url = self.get_api_url("getUpdates")
        params = {"offset": self.last_update_id + 1, "timeout": 20}
        try:
            resp = requests.get(url, params=params, timeout=25)
            if resp.status_code != 200:
                return
            data = resp.json()
            for item in data.get("result", []):
                self.last_update_id = item["update_id"]

                # 1. Message handling
                if "message" in item:
                    msg = item["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "").strip()

                    if not self.is_admin(chat_id):
                        self.send_message(chat_id, "⛔ <b>Ruxsat berilmagan!</b> Siz ushbu botning administratori emassiz.")
                        continue

                    if text == "/start":
                        self.handle_start(chat_id)
                    elif text == "/status":
                        self.handle_status(chat_id)
                    elif text in ("/nodes", "/control"):
                        self.handle_nodes_menu(chat_id)
                    elif text == "/today":
                        self.handle_today(chat_id)
                    elif text == "/help":
                        self.send_message(chat_id, "ℹ️ <b>Yordam:</b>\n/start - Asosiy menyu\n/status - Tugunlar holati\n/nodes - Boshqarish pulti\n/today - Bugungi statistika")

                # 2. Callback query handling (Inline buttons)
                elif "callback_query" in item:
                    cb = item["callback_query"]
                    cb_id = cb["id"]
                    chat_id = cb["message"]["chat"]["id"]
                    msg_id = cb["message"]["message_id"]
                    data = cb.get("data", "")

                    if not self.is_admin(chat_id):
                        self.answer_callback(cb_id, "Ruxsat yo'q!", alert=True)
                        continue

                    if data == "cmd_start":
                        self.handle_start(chat_id)
                        self.answer_callback(cb_id)
                    elif data == "cmd_status":
                        self.handle_status(chat_id, message_id=msg_id)
                        self.answer_callback(cb_id)
                    elif data == "cmd_nodes":
                        self.handle_nodes_menu(chat_id, message_id=msg_id)
                        self.answer_callback(cb_id)
                    elif data == "cmd_today":
                        self.handle_today(chat_id, message_id=msg_id)
                        self.answer_callback(cb_id)
                    elif data.startswith("node_detail:"):
                        hwid = data.split(":", 1)[1]
                        self.handle_node_detail(chat_id, message_id=msg_id, hwid=hwid)
                        self.answer_callback(cb_id)
                    elif data.startswith("cmd_act:"):
                        _, hwid, act = data.split(":", 2)
                        self.handle_node_action(chat_id, msg_id, cb_id, hwid, act)
                    elif data.startswith("cmd_lic:"):
                        _, hwid, st = data.split(":", 2)
                        self.handle_license_action(chat_id, msg_id, cb_id, hwid, st)

        except Exception as e:
            time.sleep(2)

    def start_polling(self):
        cfg = load_config()
        token = cfg.get("bot_token", "").strip()
        if not token:
            print("[Telegram Bot] DIQQAT: 'telegram_config.json' faylida 'bot_token' kiritilmagan!")
            print("Telegramda @BotFather ga o'tib, yangi bot yarating va tokenni kiriting.")
            return

        print("=== CYBERFARM TELEGRAM BOT ISHGA TUSHDI ===")
        print("Bot xabarlarni tinglamoqda...")
        while self.running:
            self.process_updates()

if __name__ == "__main__":
    bot = CyberFarmTelegramBot()
    bot.start_polling()
