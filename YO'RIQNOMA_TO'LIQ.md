# 🍏 CyberFarm Pro — To'liq Foydalanish Qo'llanmasi

> **Ushbu hujjat CyberFarm Pro tizimining barcha bo'limlari, 3 ta tarmoq rejimi, Google Sheets integratsiyasi va boshqa kompyuterlarda xavfsiz ishlatish bo'yicha to'liq yo'riqnomadir.**

---

## 📋 Mundarija
1. [Loyiha Haqida va Asosiy Imkoniyatlar](#1-loyiha-haqida)
2. [Boshqaruv Paneli (Apple HIG Dizayn)](#2-boshqaruv-paneli)
3. [Tarmoq va IP Rejimlari (3 xil usul)](#3-tarmoq-va-ip-rejimlari)
   * [1-usul: Mobil Internet (USB + Parvoz rejimi)](#1-usul-mobil-internet)
   * [2-usul: Kompyuter Tarmog'i (Oddiy / To'g'ridan-to'g'ri)](#2-usul-kompyuter-tarmogi)
   * [3-usul: Bepul Avtomatik Proxy (Scraper)](#3-usul-bepul-avtomatik-proxy)
4. [Boshqaruv Pulti (Boshlash, Pauza, Limit, Reset)](#4-boshqaruv-pulti)
5. [QR Kodni Yangilash / Almashtirish](#5-qr-kodni-yangilash)
6. [Google Sheets Hisobotini Sozlash](#6-google-sheets-hisoboti)
7. [Boshqa Kompyuterlarda Ishlatish (Resurs Sarflamaslik)](#7-boshqa-kompyuterlarda-ishlatish)
8. [Kodni Himoyalash (.exe holati)](#8-kodni-himoyalash)
9. [Tez-tez So'raladigan Savollar (FAQ)](#9-faq)

---

## 1. Loyiha Haqida
**CyberFarm Pro** — "Apk Qo'riqchi" (`com.baxtiyorov.security`) ilovasi referal tizimiga o'rnatishlarni avtomatlashtirilgan tarzda yig'uvchi virtual telefon farmasidir.

* Har bir siklda mutlaqo yangi virtual telefon yaratiladi (yangi IMEI, Android ID, MAC, Model, SIM operator).
* Referal havola ochiladi va APK o'rnatiladi.
* Attribution (hisobga olinish) signali serverga yetib borishi uchun ilova 15 soniya faol ochiq turadi.
* Virtual telefon to'liq o'chirilib, xotira tozalanadi va barcha ma'lumotlar Google Sheets jadvaliga qayd etiladi.

---

## 2. Boshqaruv Paneli
Web panel manzili: **`http://localhost:8501`**
Panel Apple kompaniyasining zamonaviy **Human Interface Guidelines (HIG)** uslubida yaratilgan:
* **Yuqori sarlavha (Hero):** Tizim holati (🟢 ISHLAMOQDA, 🟡 PAUZADA, ⚪ TAYYOR) va faol tashqi IP manzil.
* **Statistika kartalari:** Bugungi reja, muvaffaqiyatli o'rnatishlar, xatoliklar va foiz ko'rsatkichi.
* **Faol Qurilma Profili:** Oxirgi virtual telefonning barcha apparat identifikatorlari (Model, IMEI, MAC, Operator, IP).
* **macOS Tizim Terminali:** Real vaqt rejimida fon robotining har bir qadamini ko'rsatib turuvchi oynasi.

---

## 3. Tarmoq va IP Rejimlari

Dashboard-ning chap panelidagi **"🌐 Tarmoq & IP Rejimi"** bo'limi orqali xohlagan rejimingizni tanlashingiz mumkin:

### 1-usul: Mobil Internet (USB Tethering + Parvoz rejimi) — ⭐ TAVSIYA ETILADI
* **Mo'ljallangan:** CyberControl serveriga 100% haqiqiy O'zbekiston mobil operatorlari (Mobiuz, Ucell, Beeline, Uztelecom) IP-sini berish uchun.
* **Qanday ishlatiladi:**
  1. Android telefoningizni kompyuterga USB kabel orqali ulang.
  2. Telefonda **"Sozlamalar" -> "Ulanishlar" -> "USB modem" (USB Tethering)** ni yoqing.
  3. (Avtomatik rejim uchun) Telefon sozlamalarida "Dasturchi parametrlari" (Developer Options) ichidan **"USB orqali sozlash" (USB Debugging)** ni yoqing.
  4. Har bir virtual telefon tugagach, dastur telefoningizdagi parvoz rejimini 3 soniyaga yoqib-o'chiradi va yangi mobil IP oladi.
  5. Agar USB Debugging yoqilmagan bo'lsa, tizim kutadi va siz telefonda parvoz rejimini qo'lda yoqib-o'chirasiz.

### 2-usul: Kompyuter Tarmog'i (Oddiy / To'g'ridan-to'g'ri)
* **Mo'ljallangan:** Boshqa kompyuterlarda, ofislarda yoki tezkor sinovlarda ortiqcha sozlamalarsiz ishlatish uchun.
* **Qanday ishlatiladi:**
  1. Shunchaki radio tugmadan **"Kompyuter Tarmog'i"** ni tanlaysiz.
  2. Kompyuteringiz qaysi provayderga (Ethernet yoki Wi-Fi) ulangan bo'lsa, o'sha internet orqali eng yuqori tezlikda ishlaydi.

### 3-usul: Bepul Avtomatik Proxy (Scraper)
* **Mo'ljallangan:** Kompyuteringiz bitta joyda turgan holda internetdan turli xil xalqaro IP-lar orqali ishlash uchun.
* **Qanday ishlatiladi:**
  1. Radio tugmadan **"Bepul Auto-Proxy"** ni tanlaysiz.
  2. Dastur internetdagi ochiq proksilar bazasini avtomatik skanerlab, tezkor va ishlaydigan proksini tanlaydi va virtual telefonga o'rnatadi.
  3. Sizdan hech qanday fayl yoki sozlama talab qilinmaydi.

---

## 4. Boshqaruv Pulti
* **Kunlik maqsad (Limit):** Qancha o'rnatish kerakligini kiriting (masalan, `50`).
* **▶️ BOSHLASH:** Jarayonni ishga tushiradi.
* **⏸️ PAUZA:** Jarayonni vaqtincha to'xtatib turadi.
* **▶️ DAVOM ETTIRISH:** To'xtatilgan joyidan davom ettiradi.
* **⏹️ TO'XTATISH:** Jarayonni butunlay to'xtatadi va emulyatorni yopadi.
* **🔄 Qayta O'rnatish (Reset):** Bugungi hisoblagichlar va loglarni tozalaydi.

---

## 5. QR Kodni Yangilash
* Agar yangi referal QR kod berilsa, uni kompyuteringizga rasm (`.jpg`, `.png`) sifatida saqlang.
* Dashboard-ning chap yon panelidagi **"Yangi QR kod yuklash"** tugmasi orqali yuklang.
* Tizim yangi havolani OpenCV orqali darhol taniydi va yangi linkka avtomatik o'tadi.

---

## 6. Google Sheets Hisoboti
* Har bir muvaffaqiyatli yoki xatolikli o'rnatish quyidagi jadvalga real vaqtda tushadi:  
  `https://docs.google.com/spreadsheets/d/1SeiE-OPG8H3nJz53OibyOkMqOdrFdHKSeKcaCkT-A_g/edit`
* Ustunlar: `№ | Sana / Vaqt | Telefon Modeli | IMEI | Android ID | Referal Link | Tashqi IP | Holati`.
* Agar avtorizatsiya muddati o'tsa, chap paneldagi **"🔑 Google OAuth orqali ulanish"** tugmasini bosing.

---

## 7. Boshqa Kompyuterlarda Ishlatish
O'z kompyuteringizning resursi va elektr energiyasini sarflamaslik uchun:
1. `D:\apk` papkasini arxivlab (ZIP), fleshka yoki bulut orqali boshqa kompyuterga tashlang.
2. U kompyuterda shunchaki **`setup_environment.bat`** faylini 2 marta bosing.
3. Kerakli muhit o'zi o'rnatiladi va brauzerda Dashboard ochiladi.
4. Barcha turli kompyuterlar bitta umumiy Google Sheets jadvalingizga natijalarni to'playdi.

---

## 8. Kodni Himoyalash (.exe holati)
Dasturni boshqa begona shaxslarga berganda kodingiz va g'oyangiz o'g'irlanmasligi uchun loyiha yopiq **`.exe` (mashina kodi)** fayliga kompilyatsiya qilingan. Unda:
* Python fayllari (`.py`) berilmaydi.
* Shaxsiy Google hisob tokenlari tozalangan.
* Bloknotda ochib bo'lmaydi (C/C++ ikkilik formati).

---

## 9. FAQ (Tez-tez so'raladigan savollar)

**S: Nega virtual telefon yuklanishi 1-2 daqiqa vaqt olyapti?**  
J: Tizim har bir siklda toza, yangi Android tizimini noldan yuklaydi va apparat parametrlarini o'rnatadi. Bu anti-fraud tizimlaridan o'tish uchun zarur.

**S: Kompyuterimda virtualizatsiya yoqilganini qanday tekshiraman?**  
J: `Ctrl + Shift + Esc` (Task Manager) -> `Performance` -> `CPU` bo'limida `Virtualization: Enabled` ekanligini ko'ring.

**S: Streamlit boshqaruv paneli ochilmasa nima qilish kerak?**  
J: Papkadagi `run_dashboard.bat` faylini bosing yoki brauzerda `http://localhost:8501` manziliga kiring.
