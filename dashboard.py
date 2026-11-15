import streamlit as st
import os
import sys
import json
import time
import subprocess
import re
import html
from qr_reader import decode_qr, get_latest_qr_image
from sheets_manager import SheetsManager, SPREADSHEET_ID
from app_worker import (
    load_state,
    save_state,
    start_worker,
    pause_worker,
    resume_worker,
    stop_worker,
    is_pid_alive,
    BASE_DIR
)
from ip_manager import get_public_ip, find_physical_android_device
from license_manager import get_node_config, save_node_config, generate_license_key

def sanitize_ip(val):
    if not val:
        return "89.104.102.91"
    s = str(val).strip()
    m = re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", s)
    return m.group(0) if m else "89.104.102.91"

st.set_page_config(
    page_title="CyberFarm Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

state = load_state()

# Health check
pid = state.get("worker_pid")
if state.get("status") in ("RUNNING", "PAUSED"):
    if not is_pid_alive(pid):
        state["status"] = "IDLE"
        state["worker_pid"] = None
        state["current_step"] = "Kutishda"
        save_state(state)

cur_status = state.get("status", "IDLE")
net_mode = state.get("network_mode", "USB_MOBILE")
theme_mode = state.get("theme_mode", "light")

# Read QR Info
try:
    qr_info = decode_qr()
    ref_url = qr_info.get("raw_url", "")
    pkg_name = qr_info.get("package_name", "com.baxtiyorov.security")
    image_file = qr_info.get("image_file", "")
except Exception:
    ref_url = state.get("referral_url", "https://project.cybercontrol.uz/r/...")
    pkg_name = "com.baxtiyorov.security"
    image_file = ""

# ==========================================
# DUAL-THEME ENGINE (APPLE LIGHT & DARK HIG)
# ==========================================
if theme_mode == "light":
    css_vars = """
    :root {
        --bg-main: #F5F5F7;
        --bg-card: #FFFFFF;
        --bg-elevated: #F9F9FB;
        --border: rgba(0, 0, 0, 0.08);
        --border-hover: rgba(0, 0, 0, 0.16);
        --text-primary: #1D1D1F;
        --text-muted: #86868B;
        --accent-blue: #0071E3;
        --accent-green: #34C759;
        --accent-amber: #FF9500;
        --accent-red: #FF3B30;
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.04);
        --shadow-md: 0 6px 24px -2px rgba(0, 0, 0, 0.06), 0 2px 6px -1px rgba(0, 0, 0, 0.02);
        --shadow-hover: 0 14px 34px -4px rgba(0, 0, 0, 0.1), 0 4px 12px rgba(0, 0, 0, 0.03);
        --sidebar-bg: #EAEAEF;
        --term-bg: #1C1C1E;
        --term-bar: #2C2C2E;
        --btn-sec-bg: #FFFFFF;
        --btn-sec-text: #1D1D1F;
    }
    """
else:
    css_vars = """
    :root {
        --bg-main: #080C14;
        --bg-card: #0E1422;
        --bg-elevated: #151D30;
        --border: rgba(255, 255, 255, 0.08);
        --border-hover: rgba(255, 255, 255, 0.18);
        --text-primary: #F8FAFC;
        --text-muted: #64748B;
        --accent-blue: #3B82F6;
        --accent-green: #10B981;
        --accent-amber: #F59E0B;
        --accent-red: #EF4444;
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 6px 24px -2px rgba(0, 0, 0, 0.5);
        --shadow-hover: 0 14px 34px -4px rgba(0, 0, 0, 0.7);
        --sidebar-bg: #070A10;
        --term-bg: #04060A;
        --term-bar: #0B0F17;
        --btn-sec-bg: #151D30;
        --btn-sec-text: #FFFFFF;
    }
    """

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    {css_vars}

    html, body, [class*="css"], .stApp {{
        background-color: var(--bg-main) !important;
        color: var(--text-primary) !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important;
        transition: background-color 0.3s ease, color 0.3s ease;
    }}

    .block-container {{
        padding-top: 1.2rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 1400px !important;
    }}

    header[data-testid="stHeader"] {{
        display: none !important;
    }}

    /* Top Command Bar */
    .top-bar {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 12px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: var(--shadow-md);
        height: 58px;
    }}
    .top-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .top-title {{
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.02em;
    }}
    .top-badge {{
        font-size: 0.65rem;
        font-weight: 700;
        color: var(--accent-blue);
        background: rgba(0, 113, 227, 0.1);
        padding: 2px 7px;
        border-radius: 5px;
        border: 1px solid rgba(0, 113, 227, 0.2);
    }}
    .top-meta {{
        display: flex;
        align-items: center;
        gap: 20px;
    }}
    .meta-block {{
        text-align: right;
    }}
    .meta-tag {{
        font-size: 0.62rem;
        color: var(--text-muted);
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }}
    .meta-val {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-primary);
    }}

    /* Status Pill */
    .pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
    }}
    .pill-green {{
        background: rgba(52, 199, 89, 0.12);
        color: var(--accent-green);
        border: 1px solid rgba(52, 199, 89, 0.3);
    }}
    .pill-gray {{
        background: rgba(142, 142, 147, 0.12);
        color: var(--text-muted);
        border: 1px solid rgba(142, 142, 147, 0.25);
    }}
    .pill-amber {{
        background: rgba(255, 149, 0, 0.12);
        color: var(--accent-amber);
        border: 1px solid rgba(255, 149, 0, 0.3);
    }}
    .dot-pulse {{
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: currentColor;
    }}

    /* Referral Link Strip */
    .referral-strip {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 8px 16px;
        margin: 12px 0 14px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: var(--shadow-sm);
    }}
    .ref-left {{
        display: flex;
        align-items: center;
        gap: 10px;
        overflow: hidden;
    }}
    .ref-tag {{
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        white-space: nowrap;
    }}
    .ref-link {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: var(--accent-blue);
        text-decoration: none;
        font-weight: 600;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .ref-link:hover {{
        text-decoration: underline;
    }}
    .ref-pkg {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        background: rgba(0, 113, 227, 0.08);
        color: var(--accent-blue);
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid rgba(0, 113, 227, 0.2);
        white-space: nowrap;
    }}

    /* KPI Cards */
    .metric-box {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: var(--shadow-md);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .metric-box:hover {{
        border-color: var(--border-hover);
        transform: translateY(-2px);
        box-shadow: var(--shadow-hover);
    }}
    .metric-label {{
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 6px;
    }}
    .metric-number {{
        font-size: 1.65rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.03em;
        line-height: 1;
    }}
    .metric-bar {{
        width: 100%;
        height: 3px;
        background: rgba(0, 0, 0, 0.05);
        border-radius: 2px;
        margin-top: 10px;
        overflow: hidden;
    }}
    .metric-fill {{
        height: 100%;
        background: var(--accent-blue);
        border-radius: 2px;
    }}

    /* Workspace */
    .panel-box {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 18px;
        box-shadow: var(--shadow-md);
    }}
    .panel-head {{
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        padding-bottom: 10px;
        margin-bottom: 12px;
        border-bottom: 1px solid var(--border);
    }}

    .spec-item {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid var(--border);
        font-size: 0.8rem;
    }}
    .spec-item:last-child {{
        border-bottom: none;
    }}
    .spec-k {{ color: var(--text-muted); font-weight: 500; }}
    .spec-v {{ font-family: 'JetBrains Mono', monospace; color: var(--text-primary); font-weight: 600; }}

    /* Device Spec Ribbon (Full-Width) */
    .device-strip {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px 18px;
        margin-bottom: 12px;
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 12px;
        box-shadow: var(--shadow-sm);
    }}
    .dev-item {{
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }}
    .d-k {{
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--text-muted);
        letter-spacing: 0.05em;
        margin-bottom: 2px;
    }}
    .d-v {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--text-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    /* macOS Developer Terminal (Full-Width to Sidebar) */
    .term-window {{
        width: 100% !important;
        background: var(--term-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        overflow: hidden;
        box-shadow: var(--shadow-md);
    }}
    .term-bar {{
        background: var(--term-bar);
        padding: 10px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }}
    .term-dots {{
        display: flex;
        gap: 7px;
    }}
    .t-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }}
    .td-r {{ background: #FF5F56; }}
    .td-y {{ background: #FFBD2E; }}
    .td-g {{ background: #27C93F; }}
    .term-tag {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #8E8E93;
    }}
    .term-text {{
        height: 480px !important;
        padding: 16px 20px;
        overflow-y: auto;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        line-height: 1.6;
        color: #38BDF8;
        white-space: pre-wrap;
    }}

    /* Buttons with Apple Tactile Depth */
    div.stButton > button {{
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        padding: 7px 16px !important;
        background: var(--btn-sec-bg) !important;
        border: 1px solid var(--border) !important;
        color: var(--btn-sec-text) !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}
    div.stButton > button:hover {{
        border-color: var(--border-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: var(--shadow-md) !important;
    }}
    button[kind="primary"] {{
        background: var(--accent-blue) !important;
        border-color: var(--accent-blue) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 14px rgba(0, 113, 227, 0.3) !important;
    }}
    button[kind="primary"]:hover {{
        background: #0077ED !important;
        box-shadow: 0 6px 20px rgba(0, 113, 227, 0.4) !important;
    }}

    /* Sidebar & Inputs */
    section[data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border) !important;
    }}
    .stTextInput input, .stNumberInput input, div[data-baseweb="input"] {{
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border-color: var(--border) !important;
        border-radius: 9px !important;
    }}
    div[data-testid="stRadio"] > div {{
        background: var(--bg-card);
        border-radius: 9px;
        border: 1px solid var(--border);
        padding: 5px;
    }}

    /* Apple HIG Tabs */
    button[data-baseweb="tab"] {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        color: var(--text-muted) !important;
        padding: 10px 18px !important;
        background: transparent !important;
        border: none !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: var(--accent-blue) !important;
        border-bottom: 2px solid var(--accent-blue) !important;
    }}

    /* Fleet Card Styling */
    .fleet-card {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
    }}
    .fleet-card:hover {{
        border-color: var(--border-hover);
        box-shadow: var(--shadow-md);
    }}
    .fleet-top {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        border-bottom: 1px solid var(--border);
        padding-bottom: 10px;
    }}
    .fleet-title {{
        font-size: 0.98rem;
        font-weight: 700;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .fleet-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 12px;
    }}
    .fleet-item {{
        display: flex;
        flex-direction: column;
    }}
    .f-k {{
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--text-muted);
        letter-spacing: 0.05em;
        margin-bottom: 2px;
    }}
    .f-v {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.84rem;
        font-weight: 600;
        color: var(--text-primary);
    }}
</style>
""", unsafe_allow_html=True)

# ====================
# SIDEBAR (SETTINGS ONLY, THEME REMOVED)
# ====================
with st.sidebar:
    st.markdown("""
    <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 8px;">
        Tarmoq Rejimi
    </div>
    """, unsafe_allow_html=True)

    mode_options = ["USB_MOBILE", "DIRECT", "AUTO_PROXY"]
    mode_names = {
        "USB_MOBILE": "Mobil Internet (USB)",
        "DIRECT": "Kompyuter Tarmog'i",
        "AUTO_PROXY": "Avtomatik Proxy"
    }

    selected_mode = st.radio(
        "Rejim:",
        mode_options,
        index=mode_options.index(net_mode) if net_mode in mode_options else 0,
        format_func=lambda x: mode_names.get(x, x),
        label_visibility="collapsed"
    )

    if selected_mode != net_mode:
        state["network_mode"] = selected_mode
        save_state(state)
        st.toast(f"Rejim: {mode_names[selected_mode]}")
        time.sleep(0.3)
        st.rerun()

    active_ip = sanitize_ip(state.get("current_ip") or get_public_ip())
    st.markdown(f"""
    <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 9px; padding: 10px; margin: 12px 0; box-shadow: var(--shadow-sm);">
        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Faol IP</div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.92rem; font-weight: 700; color: var(--accent-blue); margin-top: 2px;">
            {active_ip}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if selected_mode == "USB_MOBILE":
        phone_id = find_physical_android_device()
        if phone_id:
            st.success(f"📱 Telefon: `{phone_id}` (Avto-Parvoz Faol)")
        else:
            st.warning("⚠️ Telefon topilmadi: USB kabel bilan ulang, 'USB modem' va 'USB sozlash' (Debugging) yoqing.")

    if st.button("IP Yangilash", use_container_width=True):
        state["current_ip"] = get_public_ip()
        save_state(state)
        st.rerun()

    st.markdown("---")

    # QR Code & Sheets
    if image_file:
        st.caption(f"QR Fayl: `{image_file}`")
        latest_img = get_latest_qr_image()
        if latest_img and os.path.exists(latest_img):
            st.image(latest_img, use_container_width=True)

    uploaded_qr = st.file_uploader("QR yangilash", type=["jpg", "png"], label_visibility="collapsed")
    if uploaded_qr:
        save_path = os.path.join(BASE_DIR, uploaded_qr.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_qr.getbuffer())
        st.rerun()

    st.markdown("---")

    sheets_mgr = SheetsManager()
    connected, _ = sheets_mgr.connect(interactive=False)
    if connected:
        st.markdown(f'<a href="https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit" target="_blank" style="color: var(--accent-blue); font-size: 0.78rem; font-weight: 600; text-decoration: none;">Google Sheets Ochish ↗</a>', unsafe_allow_html=True)
    else:
        if st.button("Google OAuth", use_container_width=True):
            subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "auth_google.py")], cwd=BASE_DIR)

# ====================
# TOP BAR WITH CONVENIENT THEME TOGGLE
# ====================
status_uz = {
    "RUNNING": ("Ishlamoqda", "pill-green"),
    "PAUSED": ("Pauzada", "pill-amber"),
    "COMPLETED": ("Tugatildi", "pill-green"),
    "IDLE": ("Kutishda", "pill-gray")
}.get(cur_status, ("Kutishda", "pill-gray"))

c_top_info, c_top_theme = st.columns([5.8, 1.2])

with c_top_info:
    st.markdown(f"""
    <div class="top-bar">
        <div class="top-brand">
            <span class="top-title">CyberFarm</span>
            <span class="top-badge">STUDIO</span>
        </div>
        <div class="top-meta">
            <div class="meta-block">
                <div class="meta-tag">Gateway IP</div>
                <div class="meta-val" style="color: var(--accent-blue);">{sanitize_ip(state.get('current_ip') or active_ip)}</div>
            </div>
            <div class="meta-block">
                <div class="meta-tag">Rejim</div>
                <div class="meta-val">{net_mode}</div>
            </div>
            <div>
                <span class="pill {status_uz[1]}">
                    <span class="dot-pulse"></span> {status_uz[0]}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c_top_theme:
    st.write("")
    theme_btn_text = "🌙 Qorong'u" if theme_mode == "light" else "☀️ Yorug'"
    if st.button(theme_btn_text, use_container_width=True):
        state["theme_mode"] = "dark" if theme_mode == "light" else "light"
        save_state(state)
        st.rerun()

# ====================
# VISIBLE REFERRAL LINK STRIP
# ====================
st.markdown(f"""
<div class="referral-strip">
    <div class="ref-left">
        <span class="ref-tag">🔗 Faol Referal Havola:</span>
        <a class="ref-link" href="{ref_url}" target="_blank">{ref_url}</a>
    </div>
    <span class="ref-pkg">{pkg_name}</span>
</div>
""", unsafe_allow_html=True)

tab_local, tab_fleet, tab_license = st.tabs([
    "⚡ Lokal Qurilma",
    "🌐 Markaziy Ferma (Barcha Kompyuterlar)",
    "🔑 Litsenziya va Himoya"
])

# ====================
# TAB 1: LOCAL DEVICE
# ====================
with tab_local:
    # KPI METRICS
    target = max(state.get("target_limit", 1), 1)
    completed = state.get("completed_today", 0)
    failed = state.get("failed_count", 0)
    progress_ratio = min(completed / target, 1.0)
    progress_pct = int(progress_ratio * 100)

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Holat</div>
            <div class="metric-number">{status_uz[0].upper()}</div>
            <div class="metric-bar"><div class="metric-fill" style="width: 100%;"></div></div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Reja</div>
            <div class="metric-number">{completed} <span style="font-size: 0.92rem; color: var(--text-muted); font-weight: 500;">/ {target}</span></div>
            <div class="metric-bar"><div class="metric-fill" style="width: {progress_pct}%;"></div></div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Muvaffaqiyatli</div>
            <div class="metric-number" style="color: var(--accent-green);">{completed}</div>
            <div class="metric-bar"><div class="metric-fill" style="width: {progress_pct}%; background: var(--accent-green);"></div></div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Xatoliklar</div>
            <div class="metric-number" style="color: {'var(--accent-red)' if failed > 0 else 'var(--text-muted)'};">{failed}</div>
            <div class="metric-bar"><div class="metric-fill" style="width: {'100%' if failed > 0 else '0%'}; background: var(--accent-red);"></div></div>
        </div>
        """, unsafe_allow_html=True)

    # ACTION CONTROLS
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    b1, b2, b3, b4 = st.columns([1.5, 1.2, 1.2, 1])

    with b1:
        new_limit = st.number_input("Limit", min_value=1, max_value=5000, value=int(state.get("target_limit", 20)), label_visibility="collapsed")

    with b2:
        if cur_status == "RUNNING":
            if st.button("Pauza", use_container_width=True):
                pause_worker()
                time.sleep(0.3)
                st.rerun()
        elif cur_status == "PAUSED":
            if st.button("Davom", type="primary", use_container_width=True):
                resume_worker()
                time.sleep(0.3)
                st.rerun()
        else:
            if st.button("Boshlash", type="primary", use_container_width=True):
                start_worker(target_limit=new_limit)
                time.sleep(0.3)
                st.rerun()

    with b3:
        if cur_status in ("RUNNING", "PAUSED"):
            if st.button("To'xtatish", use_container_width=True):
                stop_worker()
                time.sleep(0.3)
                st.rerun()
        else:
            if st.button("Tozalash", use_container_width=True):
                state["completed_today"] = 0
                state["failed_count"] = 0
                state["logs"] = []
                save_state(state)
                time.sleep(0.3)
                st.rerun()

    with b4:
        if st.button("Yangilash", use_container_width=True):
            st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # WORKSPACE (FULL-WIDTH DEVICE RIBBON & EXTENDED TERMINAL)
    curr_dev = state.get("current_device")
    if curr_dev:
        st.markdown(f"""
        <div class="device-strip">
            <div class="dev-item"><span class="d-k">Model</span><span class="d-v">{curr_dev.get('display_name')}</span></div>
            <div class="dev-item"><span class="d-k">IMEI</span><span class="d-v">{curr_dev.get('imei')}</span></div>
            <div class="dev-item"><span class="d-k">Android ID</span><span class="d-v">{curr_dev.get('android_id')}</span></div>
            <div class="dev-item"><span class="d-k">MAC</span><span class="d-v">{curr_dev.get('mac')}</span></div>
            <div class="dev-item"><span class="d-k">Operator</span><span class="d-v" style="color: var(--accent-green);">{curr_dev.get('sim_operator')}</span></div>
            <div class="dev-item"><span class="d-k">Toifa</span><span class="d-v" style="color: var(--accent-amber); font-weight: 600;">{curr_dev.get('category', 'Nafaqa yoshiga yetmagan')}</span></div>
            <div class="dev-item"><span class="d-k">Raqam</span><span class="d-v">{curr_dev.get('phone_number')}</span></div>
            <div class="dev-item"><span class="d-k">IP</span><span class="d-v" style="color: var(--accent-blue);">{sanitize_ip(state.get('current_ip', '-'))}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # Full-Width Terminal stretching all the way across to the left sidebar menu
    logs = state.get("logs", [])
    clean_logs = [re.sub(r"<[^>]+>", "", str(l)) for l in logs[-60:]]
    log_content = html.escape("\n".join(clean_logs)) if clean_logs else "[Tizim] Kutishda..."
    st.markdown(f"""
    <div class="term-window">
        <div class="term-bar">
            <div class="term-dots">
                <span class="t-dot td-r"></span>
                <span class="t-dot td-y"></span>
                <span class="t-dot td-g"></span>
            </div>
            <span class="term-tag">terminal.log — live stream</span>
        </div>
        <div class="term-text">{log_content}</div>
    </div>
    """, unsafe_allow_html=True)

    if cur_status == "RUNNING":
        time.sleep(2)
        st.rerun()

# ====================
# TAB 2: CENTRAL FLEET MONITOR
# ====================
with tab_fleet:
    fleet_mgr = SheetsManager()
    f_conn, _ = fleet_mgr.connect(interactive=False)

    c_fl_head, c_fl_btn = st.columns([5, 1.2])
    with c_fl_head:
        st.markdown("""
        <div style="margin-bottom: 12px;">
            <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">🌐 Markaziy Ferma Tarmog'i</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">Barcha kompyuterlar va devayslar real vaqtda Google Cloud orqali sinxronlashadi.</div>
        </div>
        """, unsafe_allow_html=True)
    with c_fl_btn:
        st.write("")
        if st.button("🔄 Ro'yxatni Yangilash", key="btn_fl_sync", use_container_width=True):
            st.rerun()

    if not f_conn:
        st.warning("Google Sheets bilan aloqa yo'q. Chap paneldagi 'Google OAuth' orqali hisobni ulang.")
    else:
        nodes = fleet_mgr.get_all_fleet_nodes()

        # If no nodes yet, ensure local heartbeat is registered
        if not nodes:
            l_cfg = get_node_config()
            fleet_mgr.sync_fleet_heartbeat(
                node_name=l_cfg.get("node_name", "PC-ASOSIY"),
                hwid=l_cfg.get("hwid", "HWID-DEFAULT"),
                license_key=l_cfg.get("license_key", "ADMIN-MASTER-KEY"),
                public_ip=state.get("current_ip") or active_ip or "127.0.0.1",
                network_mode=net_mode,
                status_label=status_uz[0],
                emulator_name="LDPlayer_0",
                completed_today=completed,
                failed_count=failed,
                note=l_cfg.get("note", "Asosiy kompyuter")
            )
            nodes = fleet_mgr.get_all_fleet_nodes()

        # Fleet KPI Summary
        f_total = len(nodes)
        f_online = sum(1 for n in nodes if n.get("is_online"))
        f_refs = sum(n.get("completed", 0) for n in nodes)
        f_active_lic = sum(1 for n in nodes if n.get("license_status") == "ACTIVE")

        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Jami Kompyuterlar</div>
                <div class="metric-number">{f_total} <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 500;">ta tugun</span></div>
                <div class="metric-bar"><div class="metric-fill" style="width: 100%;"></div></div>
            </div>
            """, unsafe_allow_html=True)
        with fc2:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Onlayn Devayslar</div>
                <div class="metric-number" style="color: var(--accent-green);">{f_online} <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 500;">faol</span></div>
                <div class="metric-bar"><div class="metric-fill" style="width: {int((f_online / max(f_total, 1)) * 100)}%; background: var(--accent-green);"></div></div>
            </div>
            """, unsafe_allow_html=True)
        with fc3:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Tizim Jami Referallari</div>
                <div class="metric-number" style="color: var(--accent-blue);">{f_refs} <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 500;">ta</span></div>
                <div class="metric-bar"><div class="metric-fill" style="width: 100%; background: var(--accent-blue);"></div></div>
            </div>
            """, unsafe_allow_html=True)
        with fc4:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Faol Litsenziyalar</div>
                <div class="metric-number">{f_active_lic} <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 500;">/ {f_total}</span></div>
                <div class="metric-bar"><div class="metric-fill" style="width: {int((f_active_lic / max(f_total, 1)) * 100)}%;"></div></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # Fleet Node Cards
        for node in nodes:
            n_hwid = html.escape(str(node.get("hwid", "-")))
            n_name = html.escape(str(node.get("node_name", "Noma'lum")))
            n_online = node.get("is_online", False)
            n_lic_st = node.get("license_status", "ACTIVE")
            n_sec = node.get("seconds_ago", 9999)
            time_txt = f"{n_sec}s oldin" if n_sec < 60 else (f"{n_sec // 60}m oldin" if n_sec < 3600 else html.escape(str(node.get("last_seen_str", "-"))))
            n_key = html.escape(str(node.get('license_key', '-')))
            n_ip = sanitize_ip(node.get('public_ip', '-'))
            n_net = html.escape(str(node.get('network_mode', 'Lokal')))
            n_emu = html.escape(str(node.get('emulator', '-')))
            n_note = html.escape(str(node.get('note', '') or 'Izohsiz'))

            if n_lic_st == "BLOCKED":
                p_badge = '<span class="pill pill-red">🔴 BLOKLANGAN</span>'
            elif n_online:
                p_badge = f'<span class="pill pill-green"><span class="dot-pulse"></span> ONLAYN ({time_txt})</span>'
            else:
                p_badge = f'<span class="pill pill-gray">⚪ OFLAYN ({time_txt})</span>'

            st.markdown(f"""
            <div class="fleet-card">
                <div class="fleet-top">
                    <div class="fleet-title">🖥️ {n_name}</div>
                    <div>{p_badge}</div>
                </div>
                <div class="fleet-grid">
                    <div class="fleet-item">
                        <span class="f-k">Hardware ID (HWID)</span>
                        <span class="f-v" style="font-size: 0.78rem;">{n_hwid}</span>
                        <span style="font-size: 0.72rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;">Kalit: {n_key}</span>
                    </div>
                    <div class="fleet-item">
                        <span class="f-k">Tarmoq & IP</span>
                        <span class="f-v" style="color: var(--accent-blue);">{n_ip}</span>
                        <span style="font-size: 0.72rem; color: var(--text-muted);">{n_net}</span>
                    </div>
                    <div class="fleet-item">
                        <span class="f-k">Qurilma / Emulyator</span>
                        <span class="f-v">{n_emu}</span>
                        <span style="font-size: 0.72rem; color: var(--text-muted);">{n_note}</span>
                    </div>
                    <div class="fleet-item">
                        <span class="f-k">Bugungi Natija</span>
                        <span class="f-v" style="color: var(--accent-green); font-size: 1.05rem;">{node.get('completed', 0)} <span style="font-size: 0.72rem; color: var(--text-muted); font-weight: 400;">referal</span></span>
                        <span style="font-size: 0.72rem; color: var(--text-muted);">Xatoliklar: {node.get('failed', 0)}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            ca1, ca2, ca3, ca4 = st.columns([1, 1, 1, 1.4])
            with ca1:
                if st.button("▶️ Ishga tushirish", key=f"f_start_{n_hwid}", use_container_width=True):
                    fleet_mgr.send_remote_command(n_hwid, "START")
                    st.toast(f"{n_name} ga START buyrug'i yuborildi")
                    time.sleep(0.3)
                    st.rerun()
            with ca2:
                if st.button("⏸️ Pauza", key=f"f_pause_{n_hwid}", use_container_width=True):
                    fleet_mgr.send_remote_command(n_hwid, "PAUSE")
                    st.toast(f"{n_name} ga PAUZA buyrug'i yuborildi")
                    time.sleep(0.3)
                    st.rerun()
            with ca3:
                if st.button("⏹️ To'xtatish", key=f"f_stop_{n_hwid}", use_container_width=True):
                    fleet_mgr.send_remote_command(n_hwid, "STOP")
                    st.toast(f"{n_name} ga TO'XTATISH buyrug'i yuborildi")
                    time.sleep(0.3)
                    st.rerun()
            with ca4:
                if n_lic_st == "ACTIVE":
                    if st.button("🚫 Bloklash", key=f"f_block_{n_hwid}", use_container_width=True):
                        fleet_mgr.set_node_license_status(n_hwid, "BLOCKED")
                        st.toast(f"{n_name} BLOKLANDI")
                        time.sleep(0.3)
                        st.rerun()
                else:
                    if st.button("✅ Faollashtirish", key=f"f_act_{n_hwid}", type="primary", use_container_width=True):
                        fleet_mgr.set_node_license_status(n_hwid, "ACTIVE")
                        st.toast(f"{n_name} FAOLLASHTIRILDI")
                        time.sleep(0.3)
                        st.rerun()

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ====================
# TAB 3: LICENSE & PROTECTION
# ====================
with tab_license:
    st.markdown("""
    <div style="margin-bottom: 12px;">
        <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">🔑 Litsenziya va Himoya Markazi</div>
        <div style="font-size: 0.78rem; color: var(--text-muted);">Kompyuterlarni apparat darajasida (HWID) biriktirish va litsenziyalarni boshqarish.</div>
    </div>
    """, unsafe_allow_html=True)

    local_cfg = get_node_config()
    st.markdown("##### 🖥️ Ushbu Kompyuterning Identifikatori")
    cfg_c1, cfg_c2 = st.columns(2)
    with cfg_c1:
        edit_name = st.text_input("Kompyuter Nomi (Node ID):", value=local_cfg.get("node_name", "PC-ASOSIY"))
        st.text_input("Hardware ID (Ushbu mashinaning unikal kodi):", value=local_cfg.get("hwid", ""), disabled=True)
    with cfg_c2:
        edit_key = st.text_input("Litsenziya Kaliti:", value=local_cfg.get("license_key", "ADMIN-MASTER-KEY"))
        edit_note = st.text_input("Mas'ul Shaxs / Izoh:", value=local_cfg.get("note", "Asosiy boshqaruv kompyuteri"))

    if st.button("Sozlamalarni Saqlash", type="primary", key="btn_save_loc_cfg"):
        local_cfg["node_name"] = edit_name
        local_cfg["license_key"] = edit_key
        local_cfg["note"] = edit_note
        save_node_config(local_cfg)
        st.toast("Sozlamalar saqlandi!")
        time.sleep(0.3)
        st.rerun()

    st.markdown("---")
    st.markdown("##### ➕ Yangi Kompyuterlar Uchun Kalit Generatori")
    st.caption("Boshqa kompyuterlarga tarqatish uchun unikal litsenziya kaliti yaratish.")

    if "generated_key" not in st.session_state:
        st.session_state["generated_key"] = generate_license_key()

    gk_c1, gk_c2 = st.columns([3.5, 1.5])
    with gk_c1:
        st.text_input("Yangi kalit:", value=st.session_state["generated_key"], key="gen_key_inp", disabled=True)
    with gk_c2:
        st.write("")
        if st.button("Yangi Kalit Yaratish", key="btn_create_new_key", use_container_width=True):
            st.session_state["generated_key"] = generate_license_key()
            st.rerun()

    st.markdown("""
    <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; margin-top: 14px; box-shadow: var(--shadow-sm); font-size: 0.82rem; line-height: 1.6;">
        <b style="color: var(--accent-blue);">Boshqa kompyuterga dasturni o'rnatish va boshqarish yo'riqnomasi:</b>
        <ol style="margin-top: 6px; padding-left: 20px;">
            <li><b>D:\\apkbek</b> papkasini (yoki arxivini) boshqa kompyuterga ko'chirasiz.</li>
            <li>U kompyuterdagi <code>node_config.json</code> faylini ochib, <code>license_key</code> qatoriga yuqorida generatsiya qilingan kalitni yozib qo'yasiz.</li>
            <li>U yerda <code>ISHGA_TUSHIRISH.bat</code> bosilganda, yangi kompyuter avtomatik ravishda ushbu <b>Markaziy Ferma</b> oynangizda paydo bo'ladi.</li>
            <li>Agar o'sha kompyuterdagi dasturni to'xtatmoqchi yoki butunlay o'chirmoqchi bo'lsangiz, shunchaki <b>"Bloklash"</b> tugmasini bosishingiz kifoya!</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

