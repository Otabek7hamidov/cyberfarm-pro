# 🤖 AGENT_CONTEXT.md — Antigravity AI Uchun To'liq Loyiha Holati va Qo'llanma

> **Ushbu fayl Antigravity / Gemini AI agenti yangi kompyuterda loyihani darhol 100% tushunishi va davom ettirishi uchun maxsus yozilgan.**

---

## 1. Loyihaning Maqsadi va Vazifasi
Ushbu loyiha — **CyberControl (Apk Qo'riqchi)** referal tizimiga avtomatlashtirilgan tarzda o'rnatishlar sonini yig'ib beruvchi **Virtual Telefon Farmasi va Boshqaruv Tizimi** hisoblanadi.

* **Target QR / Referal:** Papkadagi rasm (`photo_*.jpg`) skaner qilinadi $\rightarrow$ `https://project.cybercontrol.uz/r/ZoGAZU1cAMWHfgxvQmcAYg` $\rightarrow$ Google Play ilovasi `com.baxtiyorov.security` ("Apk Qo'riqchi").
* **Asosiy mexanizm:** Har bir o'rnatish uchun mutlaqo yangi virtual telefon yaratiladi (yangi IMEI, Android ID, MAC, Telefon modeli), referal havola ochiladi, APK o'rnatilib ishga tushiriladi (attribution ping o'tishi uchun 15-20 sek), so'ng telefon o'chiriladi va ma'lumotlar Google Sheets-ga yoziladi.
* **Google Sheet:** `https://docs.google.com/spreadsheets/d/1SeiE-OPG8H3nJz53OibyOkMqOdrFdHKSeKcaCkT-A_g/edit`

---

## 2. Loyiha Tuzilmasi va Fayllar Rolli
1. **`dashboard.py`** — Streamlit asosidagi zamonaviy Web Boshqaruv Paneli (`http://localhost:8501`). Kunlik reja (limit) kiritiladi, jonli progress bar, Start/Pause/Stop tugmalari, terminal loglari va joriy telefon parametrlari ko'rsatiladi.
2. **`app_worker.py`** — Orqa fonda ishlovchi asosiy sikl motori. `worker_state.json` orqali boshqariladi.
3. **`emulator_manager.py`** — `LDPlayer9/ldconsole.exe` CLI buyruqlari orqali emulyator instansiyasini boshqaradi (`add`, `modify`, `launch`, `adb`, `installapp`, `runapp`, `remove`).
4. **`device_generator.py`** — Har bir yangi telefon uchun xalqaro Luhn algoritmi bilan to'g'ri IMEI, Android ID, MAC, O'zbekiston mobil operatorlari (Ucell, Beeline, Mobiuz, Uztelecom) va Samsung/Xiaomi/Pixel modellarini generatsiya qiladi.
5. **`qr_reader.py`** — Papkaga tushgan har qanday yangi rasm formatidagi QR kodni OpenCV orqali o'qib, havolani dinamik ravishda oladi.
6. **`sheets_manager.py`** — Google Sheets API (gspread) orqali `№, Sana/Vaqt, Model, IMEI, Android ID, Link, IP, Holat` qatorlarini yozadi.
7. **`auth_google.py`** — Agar `authorized_user.json` eskirgan bo'lsa, `client_secret.json` orqali bir martalik Google OAuth avtorizatsiyasini o'tkazadi.
8. **`LDPlayer9/`** — Hech qanday o'rnatish talab qilmaydigan, to'liq portativ Android 9 64-bit emulyatori.
9. **`platform-tools/`** — Google rasmiy `adb.exe`.
10. **`com.baxtiyorov.security.apk`** — O'rnatiladigan rasmiy APK paketi (v1.2.15).

---

## 3. Yangi Kompyuterda AI Agenti Bajarishi Kerak Bo'lgan Ishlar (SOP):

1. **Muhitni tekshirish:**
   * Python va pip mavjudligini ko'rish: `python --version`
   * Kutubxonalarni o'rnatish: `pip install -r requirements.txt`
2. **Google Sheets avtorizatsiyasini tekshirish:**
   * `python sheets_manager.py` ni ishga tushirish.
   * Agar token muddati o'tgan bo'lsa, foydalanuvchiga `python auth_google.py` ni ochib brauzerdan ruxsat berishini so'rash.
3. **Dashboard-ni ko'tarish:**
   * `streamlit run dashboard.py --server.port 8501`
4. **Foydalanuvchi buyruqlariga ko'ra yordam berish:**
   * Kunlik limitni sozlash, ishga tushirish (`AppWorker().start(...)`), loglarni tahlil qilish yoki yangi QR kod bo'yicha havolani yangilash.
