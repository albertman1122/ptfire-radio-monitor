# -*- coding: utf-8 -*-
import os
import base64
import streamlit as st
import streamlit_authenticator as stauth
import gspread
import pandas as pd
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import json

def _b64_asset(rel_path):
    full = os.path.join(os.path.dirname(__file__), rel_path)
    with open(full, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

MASCOT_B64 = _b64_asset("assets/login-mascot.jpg")

st.set_page_config(page_title="無線電中繼台AI通訊監控平台", page_icon="📡", layout="wide")

st.markdown("""
<style>
/* ── 全域 ── */
.stApp { background:#111827; color:#e5e7eb; }
.block-container { padding:1rem 2rem !important; max-width:1380px; }
h1,h2,h3,p,span,div { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }

/* ── 站台卡片 ── */
.st-card {
  background:#1e2432; border:1px solid #2d3748; border-radius:10px;
  padding:14px 16px; cursor:pointer; transition:border 0.15s,box-shadow 0.15s;
  min-height:100px; box-sizing:border-box;
}
.st-card:hover { border-color:#4b5563; }
.st-card.selected { border:2px solid #3b82f6; box-shadow:0 0 0 1px #3b82f633; }
.st-card.offline  { border-left:3px solid #ef4444; border-top:1px solid #2d3748;
                    border-right:1px solid #2d3748; border-bottom:1px solid #2d3748; }
.st-card.offline.selected { border-left:3px solid #ef4444; border-top:2px solid #3b82f6;
                             border-right:2px solid #3b82f6; border-bottom:2px solid #3b82f6; }
.card-name  { color:#9ca3af; font-size:0.82rem; margin-bottom:6px; }
.card-volt  { font-size:1.9rem; font-weight:700; line-height:1.1; letter-spacing:-0.5px; }
.card-volt.green  { color:#4ade80; }
.card-volt.red    { color:#f87171; }
.card-volt.yellow { color:#fbbf24; }
.card-footer { display:flex; justify-content:space-between; align-items:center; margin-top:8px; }
.badge { font-size:0.74rem; font-weight:600; padding:2px 8px;
         border-radius:4px; display:inline-block; }
.badge.green  { background:#14532d; color:#4ade80; }
.badge.red    { background:#7f1d1d; color:#fca5a5; }
.badge.yellow { background:#78350f; color:#fcd34d; }
.card-time  { color:#6b7280; font-size:0.76rem; }

/* ── 卡片下方選取按鈕（小條狀）── */
div[data-testid="stButton"] > button {
  background:#1e2432 !important; border:1px solid #2d3748 !important;
  color:#4b5563 !important; font-size:0.72rem !important;
  padding:2px 6px !important; border-radius:0 0 8px 8px !important;
  width:100% !important; margin-top:-2px !important;
  transition:all 0.15s !important;
}
div[data-testid="stButton"] > button:hover {
  background:#2d3748 !important; color:#9ca3af !important; border-color:#4b5563 !important;
}
/* 重新整理、登出、分析 按鈕覆寫回正常樣式 */
div[data-testid="stButton"]:has(button[kind="primary"]) > button,
div[data-testid="stButton"]:has(button[kind="secondary"]) > button {
  border-radius:8px !important; padding:6px 14px !important; margin-top:0 !important;
}

/* ── 分頁標籤（圓角按鈕樣式）── */
div[data-testid="stTabs"] button[data-baseweb="tab"] {
  background:#1e2432 !important; border:1px solid #374151 !important;
  border-radius:8px !important; color:#9ca3af !important;
  font-size:0.85rem !important; padding:6px 18px !important;
  margin-right:8px !important; transition:all 0.15s;
}
div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
  border-color:#6b7280 !important; color:#e5e7eb !important;
}
div[data-testid="stTabs"] button[aria-selected="true"][data-baseweb="tab"] {
  background:#1e3a5f !important; border-color:#3b82f6 !important;
  color:#93c5fd !important;
}
div[data-testid="stTabs"] [data-testid="stTabsContent"] { border:none !important; }
div[data-testid="stTabs"] > div:first-child { border-bottom:none !important; }

/* ── 量測值卡片 ── */
div[data-testid="metric-container"] {
  background:#1e2432; border:1px solid #2d3748; border-radius:8px; padding:12px 16px;
}
div[data-testid="metric-container"] label {
  color:#6b7280 !important; font-size:0.8rem !important; font-weight:500 !important;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
  color:#facc15 !important; font-size:1.3rem !important; font-weight:700 !important;
}
div[data-testid="metric-container"]:not(:first-child) div[data-testid="stMetricValue"] {
  color:#e5e7eb !important;
}

/* ── selectbox ── */
div[data-testid="stSelectbox"] > div > div {
  background:#1e2432 !important; border-color:#374151 !important; color:#d1d5db !important;
  border-radius:8px !important; font-size:0.85rem !important;
}

/* ── 小 radio 選站 chip ── */
div[data-testid="stRadio"] > div { flex-direction:row !important; flex-wrap:wrap; gap:5px; }
div[data-testid="stRadio"] > label { display:none; }
div[data-testid="stRadio"] div[data-testid="stMarkdownContainer"] { display:none; }

/* ── divider ── */
hr { border-color:#2d3748 !important; margin:12px 0 !important; }

/* ── expander ── */
div[data-testid="stExpander"] { background:#1e2432; border:1px solid #2d3748; border-radius:8px; }
div[data-testid="stExpander"] summary { color:#9ca3af !important; font-size:0.83rem !important; }

/* ── 登入頁美化（明亮溫暖・消防主題）── */
/* 只在登入頁（含 .login-hero）時，把整體背景換成明亮暖色系 */
.stApp:has(.login-hero) {
  background:radial-gradient(1100px 620px at 50% -8%, #fff1e0 0%, #fff8f0 42%, #fdf6ee 100%) !important;
}
.stApp:has(.login-hero) .block-container { padding-top:2vh !important; }

.login-hero {
  max-width:460px; margin:5vh auto 0 auto; padding:0 8px;
}
.login-logo-wrap {
  display:flex; flex-direction:column; align-items:center; margin-bottom:22px;
}
.login-mascot {
  width:172px; height:172px; object-fit:cover; border-radius:34px;
  margin-bottom:16px; filter:drop-shadow(0 14px 28px rgba(220,38,38,0.25));
}
.login-title {
  color:#3a2a20; font-size:1.34rem; font-weight:600; text-align:center; line-height:1.55;
  letter-spacing:0.02em;
}
.login-divider {
  width:48px; height:3px; background:linear-gradient(90deg,#f97316,#ef4444);
  border-radius:2px; margin:16px auto 0 auto;
}
div[data-testid="stForm"] {
  position:relative; overflow:hidden;
  background:#ffffff; border:1px solid #ffe3ce; border-radius:18px;
  padding:40px 36px 34px 36px !important;
  box-shadow:0 20px 50px rgba(230,120,60,0.16), 0 2px 8px rgba(0,0,0,0.04);
  max-width:460px; margin:0 auto;
}
div[data-testid="stForm"]::before {
  content:""; position:absolute; top:0; left:0; right:0; height:5px;
  background:linear-gradient(90deg,#fb923c,#ef4444,#fb923c);
}
/* 隱藏套件內建的「Login」標題，避免與上方自訂標題重複 */
div[data-testid="stForm"] h1,
div[data-testid="stForm"] h2,
div[data-testid="stForm"] h3 {
  display:none !important;
}
/* 帳號／密碼輸入框：統一高度與樣式（含密碼欄的顯示/隱藏眼睛圖示）*/
/* 只在最外層容器畫框，避免內層 base-input 各自出現一個方框 */
div[data-testid="stForm"] div[data-baseweb="input"],
div[data-testid="stForm"] [data-testid="stTextInputRootElement"],
div[data-testid="stForm"] div[data-testid="stTextInput"] > div {
  background:#fff9f5 !important; border:1px solid #f3dcc9 !important;
  border-radius:10px !important; height:54px !important;
  display:flex !important; align-items:center !important;
  box-sizing:border-box !important;
}
div[data-testid="stForm"] div[data-baseweb="base-input"] {
  background:transparent !important; border:none !important; border-radius:0 !important;
  height:100% !important; flex:1 1 auto !important;
  display:flex !important; align-items:center !important;
}
div[data-testid="stForm"] div[data-baseweb="input"]:focus-within,
div[data-testid="stForm"] [data-testid="stTextInputRootElement"]:focus-within {
  border-color:#f97316 !important; box-shadow:0 0 0 3px rgba(249,115,22,0.16) !important;
}
div[data-testid="stForm"] input,
div[data-testid="stForm"] input[type="text"],
div[data-testid="stForm"] input[type="password"] {
  background:#fff9f5 !important; border:none !important;
  color:#3a2a20 !important; font-size:1.02rem !important;
  padding:0 16px !important; height:100% !important; line-height:normal !important;
  -webkit-text-fill-color:#3a2a20 !important;
}
div[data-testid="stForm"] input:focus { box-shadow:none !important; }
div[data-testid="stForm"] input::placeholder { color:#c9a98d !important; opacity:1 !important; }
/* 瀏覽器自動填入時避免出現黑底 */
div[data-testid="stForm"] input:-webkit-autofill,
div[data-testid="stForm"] input:-webkit-autofill:hover,
div[data-testid="stForm"] input:-webkit-autofill:focus {
  -webkit-text-fill-color:#3a2a20 !important;
  -webkit-box-shadow:0 0 0px 1000px #fff9f5 inset !important;
  box-shadow:0 0 0px 1000px #fff9f5 inset !important;
  transition:background-color 9999s ease-in-out 0s;
}
div[data-testid="stForm"] button[title*="password"],
div[data-testid="stForm"] div[data-baseweb="input"] button {
  background:transparent !important; border:none !important; color:#b98a6f !important;
}
div[data-testid="stForm"] label p {
  color:#a8785c !important; font-size:0.86rem !important; font-weight:500 !important;
  margin-bottom:6px !important;
}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] {
  display:flex !important; align-items:center !important; gap:18px !important;
  width:100% !important; margin-top:22px !important;
}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > div {
  width:auto !important; flex:0 0 auto !important;
}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button,
div[data-testid="stForm"] button[kind="primaryFormSubmit"],
div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
  background:linear-gradient(135deg,#fb923c,#ef4444) !important;
  border:none !important; color:#fff !important; font-weight:600 !important;
  font-size:1.02rem !important;
  border-radius:10px !important; height:54px !important; width:150px !important;
  margin-top:0 !important; box-shadow:0 8px 20px rgba(239,68,68,0.28) !important;
  transition:filter 0.15s, transform 0.12s !important;
  flex:0 0 auto !important;
}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button:hover,
div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover,
div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
  filter:brightness(1.06); transform:translateY(-1px);
}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button p {
  font-size:1.02rem !important; font-weight:600 !important;
}
/* 登入按鈕旁的溫暖歡迎文字 */
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"]::after {
  content:"歡迎回來\\A 24 小時監控無線電中繼台";
  white-space:pre-line;
  color:#a8785c; font-size:0.8rem; line-height:1.6; font-weight:500;
  flex:1 1 auto;
}
.login-footnote {
  text-align:center; color:#b99a86; font-size:0.78rem; margin-top:20px;
}
</style>
""", unsafe_allow_html=True)

# ── 常數 ─────────────────────────────────────────────────────────────────────
VOLTAGE_MIN     = 12.5
VOLTAGE_MAX     = 15.0
OFFLINE_MINUTES = 90
STATION_ORDER   = [
    "無線電中繼台-瑪家","無線電中繼台-霧台","無線電中繼台-武潭",
    "無線電中繼台-佳興","無線電中繼台-新開","無線電中繼台-大漢山",
    "無線電中繼台-小琉球","無線電中繼台-北里龍","無線電中繼台-觀海樓",
    "無線電中繼台-赤牛嶺","無線電中繼台-池山","無線電中繼台-蘭嶼",
]

# ── 登入（帳密／Cookie 設定一律讀取 st.secrets，不寫死於程式碼）───────────────
if "credentials" not in st.secrets or "cookie" not in st.secrets:
    st.error("尚未設定登入密鑰，請在 .streamlit/secrets.toml（本機）或 "
             "Streamlit Cloud 的 Secrets 設定中加入 [credentials] 與 [cookie] 區塊。")
    st.stop()

credentials = {"usernames": {
    uname: dict(u) for uname, u in st.secrets["credentials"]["usernames"].items()
}}
cookie_name = st.secrets["cookie"].get("name", "power_monitor_auth")
cookie_key  = st.secrets["cookie"]["key"]
cookie_exp  = st.secrets["cookie"].get("expiry_days", 30)

auth = stauth.Authenticate(
    credentials,
    cookie_name,
    cookie_key,
    cookie_expiry_days=cookie_exp,
)

status = st.session_state.get("authentication_status")
if not status:
    st.markdown(f"""
<div class="login-hero">
  <div class="login-logo-wrap">
    <img class="login-mascot" src="data:image/jpeg;base64,{MASCOT_B64}" alt="屏東縣政府消防局吉祥物"/>
    <div class="login-title">屏東縣政府消防局</div>
    <div class="login-title">無線電中繼台 AI 通訊監控平台</div>
    <div class="login-divider"></div>
  </div>
</div>""", unsafe_allow_html=True)

auth.login(location="main")
status = st.session_state.get("authentication_status")
if status is False:
    st.markdown('<div class="login-footnote">帳號或密碼錯誤，請再試一次</div>', unsafe_allow_html=True)
    st.stop()
if not status:
    st.markdown('<div class="login-footnote">登入後將自動記住您的裝置 30 天，無需每次重新登入</div>', unsafe_allow_html=True)
    st.stop()

# ── 讀取資料 ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data():
    sa  = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        sa, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    ws = gspread.authorize(creds)\
                .open_by_key(st.secrets["google_sheet"]["sheet_id"])\
                .worksheet(st.secrets["google_sheet"]["sheet_name"])
    vals = ws.get_all_values()
    if len(vals) < 2: return pd.DataFrame()
    df = pd.DataFrame(vals[1:], columns=[c.strip() for c in vals[0]])
    tc  = next((c for c in df.columns if "時間" in c), df.columns[0])
    dc  = next((c for c in df.columns if "設備" in c), df.columns[1])
    vc  = next((c for c in df.columns if "電壓" in c), df.columns[2])
    tcs = [c for c in df.columns if "溫度" in c]
    ec  = next((c for c in df.columns if "Error" in c or "error" in c.lower()), None)
    df  = df.rename(columns={tc:"time", dc:"device", vc:"voltage"})
    for i, col in enumerate(tcs):
        names = ["temp_drive","temp_tx","temp_tcxo","temp_hpa"]
        if i < len(names): df = df.rename(columns={col: names[i]})
    if ec: df = df.rename(columns={ec:"error_info"})
    df["time"]    = pd.to_datetime(df["time"], errors="coerce")
    df["voltage"] = pd.to_numeric(df["voltage"], errors="coerce")
    for t in ["temp_drive","temp_tx","temp_tcxo","temp_hpa"]:
        if t in df.columns: df[t] = pd.to_numeric(df[t], errors="coerce")
    return df.dropna(subset=["time","device"]).sort_values("time")

def get_status(row, now):
    if row is None: return "離線","red"
    if (now-row["time"]).total_seconds()/60 > OFFLINE_MINUTES: return "離線","red"
    v = row.get("voltage")
    if pd.isna(v): return "無資料","yellow"
    if v < VOLTAGE_MIN: return "低電壓","yellow"
    if v > VOLTAGE_MAX: return "高電壓","yellow"
    if str(row.get("error_info","")).strip(): return "告警","red"
    return "正常","green"

def sname(dev): return dev.replace("無線電中繼台-","")

# ── 載入 ─────────────────────────────────────────────────────────────────────
try:
    df = load_data()
except Exception as e:
    st.error(f"讀取 Google Sheet 失敗：{e}"); st.stop()
if df.empty:
    st.warning("尚無資料"); st.stop()

now     = datetime.utcnow()
latest  = {d: df[df["device"]==d].iloc[-1] for d in df["device"].unique()}
data_latest = df["time"].max()  # 整個資料集最新一筆的時間
stations = STATION_ORDER + [d for d in df["device"].unique() if d not in STATION_ORDER]

if "sel" not in st.session_state:
    st.session_state["sel"] = stations[0]

# ── 頂部導覽 ─────────────────────────────────────────────────────────────────
n1,n2,n3,n4 = st.columns([5,2,1,1])
with n1:
    st.markdown("""
<div style="padding:4px 0;">
  <div style="color:#f9fafb;font-size:1.35rem;font-weight:700;line-height:1.3;letter-spacing:0.02em;">屏東縣政府消防局</div>
  <div style="color:#f9fafb;font-size:1.35rem;font-weight:700;line-height:1.3;letter-spacing:0.02em;">無線電中繼台 AI 通訊監控平台</div>
</div>""", unsafe_allow_html=True)
with n2:
    st.markdown(f"<p style='color:#6b7280;font-size:0.78rem;margin:0;padding:14px 0;'>"
                f"最後更新 {now.strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
with n3:
    if st.button("↺ 重新整理", use_container_width=True):
        st.cache_data.clear(); st.rerun()
with n4:
    auth.logout(button_name="登出", location="main")

st.markdown("<hr>", unsafe_allow_html=True)

# ── 站台總覽 ─────────────────────────────────────────────────────────────────
st.markdown(f"<p style='color:#e5e7eb;font-size:1.05rem;font-weight:600;margin:0 0 12px 0;letter-spacing:0.02em;'>"
            f"站台總覽&nbsp;<span style='color:#6b7280;font-size:0.9rem;font-weight:400;'>（{len(stations)} 站）</span></p>", unsafe_allow_html=True)

def card_html(dev, row, sel):
    status, color = get_status(row, now)
    v     = row["voltage"] if row is not None and not pd.isna(row.get("voltage")) else None
    v_str = f"{v:.1f} V" if v is not None else "— V"
    age   = ""
    if row is not None:
        m = int((data_latest - row["time"]).total_seconds() / 60)
        age = "最新" if m < 2 else f"{m} 分鐘前"
    is_off = (color == "red")
    cls    = "st-card" + (" offline" if is_off else "") + (" selected" if sel else "")
    volt_color = "#4ade80" if color == "green" else "#f87171" if color == "red" else "#ef4444"
    return (f'<div class="{cls}">'
            f'<div class="card-name">{sname(dev)}</div>'
            f'<div class="card-volt" style="color:{volt_color};">{v_str}</div>'
            f'<div class="card-footer">'
            f'<span class="badge {color}">{status}</span>'
            f'<span class="card-time">{age}</span>'
            f'</div></div>')

rows = [stations[i:i+6] for i in range(0, len(stations), 6)]
for row_devs in rows:
    cols = st.columns(6)
    for ci, dev in enumerate(row_devs):
        row = latest.get(dev)
        is_sel = (st.session_state["sel"] == dev)
        with cols[ci]:
            st.markdown(card_html(dev, row, is_sel), unsafe_allow_html=True)
            if st.button(sname(dev), key=f"c_{dev}", use_container_width=True):
                st.session_state["sel"] = dev
                st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ── 詳細資訊 ─────────────────────────────────────────────────────────────────
sel = st.session_state["sel"]
d1, d2 = st.columns([5,1])
with d1:
    st.markdown(f"<p style='font-size:1rem;font-weight:600;color:#e5e7eb;margin:0;'>"
                f"≋ {sname(sel)}&nbsp;&nbsp;"
                f"<span style='color:#6b7280;font-size:0.85rem;font-weight:400;'>詳細資訊</span></p>",
                unsafe_allow_html=True)
with d2:
    hours = st.selectbox("", [6,12,24,48,72], index=2,
                         format_func=lambda h: f"近 {h} 小時",
                         label_visibility="collapsed")

sub = df[df["device"]==sel].copy()
sub = sub[sub["time"] >= pd.Timestamp(now - timedelta(hours=hours))]

if sub.empty:
    st.info("此區間無資料")
else:
    TEMP_MAP = {"temp_drive":"Drive Amp","temp_tx":"TX Block","temp_tcxo":"TCXO","temp_hpa":"Final Amp"}
    TEMP_COLORS = ["#f87171","#a78bfa","#38bdf8","#4ade80"]

    tab1, tab2, tab3, tab4 = st.tabs(["電壓趨勢","溫度趨勢","異常紀錄","原始資料"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sub["time"], y=sub["voltage"], mode="lines+markers",
            line=dict(color="#4ade80", width=2), marker=dict(size=4, color="#4ade80"),
            fill="tozeroy", fillcolor="rgba(74,222,128,0.06)", showlegend=False))
        fig.add_hrect(y0=VOLTAGE_MIN, y1=VOLTAGE_MAX, fillcolor="#4ade80", opacity=0.04, line_width=0)
        fig.add_hline(y=VOLTAGE_MIN, line_dash="dot", line_color="#fbbf24", line_width=1, opacity=0.5)
        fig.add_hline(y=VOLTAGE_MAX, line_dash="dot", line_color="#fbbf24", line_width=1, opacity=0.5)
        fig.update_layout(
            height=260, margin=dict(t=8,b=8,l=0,r=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111827",
            font=dict(color="#6b7280", size=11),
            xaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False),
            yaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False, title="電壓 (V)", range=[11, 15]),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        for (col, label), color in zip(TEMP_MAP.items(), TEMP_COLORS):
            if col in sub.columns:
                fig2.add_trace(go.Scatter(
                    x=sub["time"], y=sub[col], mode="lines",
                    name=label, line=dict(color=color, width=2)))
        fig2.update_layout(
            height=240, margin=dict(t=8,b=8,l=0,r=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111827",
            font=dict(color="#6b7280", size=11),
            xaxis=dict(gridcolor="#1f2937", zeroline=False),
            yaxis=dict(gridcolor="#1f2937", zeroline=False, title="溫度 (°C)"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        # 錯誤紀錄頁
        err_sub = sub[sub.get("error_info", pd.Series(dtype=str)).astype(str).str.strip() != ""] if "error_info" in sub.columns else pd.DataFrame()
        total_err = len(err_sub)

        # 頂部統計列
        e1, e2, e3 = st.columns(3)
        with e1:
            clr = "#f87171" if total_err > 0 else "#4ade80"
            bg  = "#7f1d1d" if total_err > 0 else "#14532d"
            st.markdown(f"""
<div style="background:{bg};border-radius:8px;padding:12px 16px;text-align:center;">
  <div style="color:{clr};font-size:1.6rem;font-weight:700;">{total_err}</div>
  <div style="color:{clr};font-size:0.78rem;opacity:0.85;">異常筆數（近 {hours}h）</div>
</div>""", unsafe_allow_html=True)
        with e2:
            last_err_time = err_sub["time"].max() if total_err > 0 else None
            lt_str = last_err_time.strftime("%m/%d %H:%M") if last_err_time else "—"
            st.markdown(f"""
<div style="background:#1e2432;border:1px solid #2d3748;border-radius:8px;padding:12px 16px;text-align:center;">
  <div style="color:#e5e7eb;font-size:1.1rem;font-weight:700;">{lt_str}</div>
  <div style="color:#6b7280;font-size:0.78rem;">最後錯誤時間</div>
</div>""", unsafe_allow_html=True)
        with e3:
            ok_rows = len(sub) - total_err
            pct = f"{ok_rows/len(sub)*100:.1f}%" if len(sub) > 0 else "—"
            st.markdown(f"""
<div style="background:#1e2432;border:1px solid #2d3748;border-radius:8px;padding:12px 16px;text-align:center;">
  <div style="color:#4ade80;font-size:1.1rem;font-weight:700;">{pct}</div>
  <div style="color:#6b7280;font-size:0.78rem;">正常率</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        if total_err == 0:
            # 無錯誤 ── 清爽正常狀態
            st.markdown("""
<div style="background:#0f2318;border:1px solid #166534;border-radius:10px;
  padding:28px;text-align:center;margin-top:4px;">
  <div style="font-size:2rem;margin-bottom:8px;">✅</div>
  <div style="color:#4ade80;font-size:1rem;font-weight:600;">系統正常，無異常紀錄</div>
  <div style="color:#6b7280;font-size:0.8rem;margin-top:6px;">此時間區間內無任何異常紀錄</div>
</div>""", unsafe_allow_html=True)
        else:
            # 有錯誤 ── 時間軸列表
            st.markdown(f"<p style='color:#9ca3af;font-size:0.82rem;margin:0 0 8px;'>近 {hours} 小時共 {total_err} 筆異常，最新在上：</p>",
                        unsafe_allow_html=True)
            for _, erow in err_sub.sort_values("time", ascending=False).head(50).iterrows():
                msg   = str(erow.get("error_info","")).strip()
                ts    = erow["time"].strftime("%Y-%m-%d %H:%M:%S")
                volt  = f"{erow['voltage']:.1f}V" if not pd.isna(erow.get("voltage")) else "—"
                # 簡易嚴重度判斷
                if any(k in msg.upper() for k in ["CRIT","FAIL","DOWN","ALARM"]):
                    dot, bg2, fc = "#f87171","#3b0a0a","#fca5a5"
                elif any(k in msg.upper() for k in ["WARN","HIGH","LOW","TEMP"]):
                    dot, bg2, fc = "#fbbf24","#2d1a00","#fcd34d"
                else:
                    dot, bg2, fc = "#60a5fa","#0c1e35","#93c5fd"
                st.markdown(f"""
<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:8px;">
  <div style="display:flex;flex-direction:column;align-items:center;padding-top:4px;">
    <div style="width:10px;height:10px;border-radius:50%;background:{dot};flex-shrink:0;"></div>
    <div style="width:1px;flex:1;background:#2d3748;margin-top:4px;min-height:20px;"></div>
  </div>
  <div style="background:{bg2};border:1px solid #2d3748;border-radius:8px;
    padding:10px 14px;flex:1;margin-bottom:2px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
      <span style="color:{fc};font-size:0.82rem;font-weight:600;">{msg}</span>
      <span style="color:#4b5563;font-size:0.74rem;">{volt}</span>
    </div>
    <div style="color:#6b7280;font-size:0.75rem;">{ts}</div>
  </div>
</div>""", unsafe_allow_html=True)

    with tab4:
        show = ["time","voltage"] + [c for c in ["temp_drive","temp_tx","temp_tcxo","temp_hpa","error_info"] if c in sub.columns]
        st.dataframe(sub[show].tail(50).iloc[::-1], use_container_width=True)

    # 量測值卡片列
    lr   = sub.iloc[-1]
    mc   = st.columns(5)
    mc[0].metric("電壓",     f"{lr['voltage']:.1f} V" if not pd.isna(lr.get("voltage")) else "—")
    for i, (col, label) in enumerate(TEMP_MAP.items()):
        val = f"{lr[col]:.0f} °C" if col in lr.index and not pd.isna(lr.get(col)) else "—"
        mc[i+1].metric(label, val)

    if str(lr.get("error_info","")).strip():
        st.error(f"⚠️ Error：{lr['error_info']}")

    # ── 智慧診斷分析 ─────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("""
<div style="background:linear-gradient(135deg,#1e2d45 0%,#1e2432 100%);
  border:1px solid #3b5278;border-radius:10px;padding:14px 20px;margin-bottom:12px;
  display:flex;align-items:center;gap:12px;">
  <span style="font-size:1.4rem;">🧠</span>
  <div>
    <span style="color:#e5e7eb;font-size:1.0rem;font-weight:600;">智慧診斷分析</span>
    <span style="margin-left:10px;background:#1e3a5f;color:#93c5fd;
      font-size:0.72rem;padding:2px 10px;border-radius:4px;font-weight:600;">智慧診斷</span>
    <div style="color:#6b7280;font-size:0.78rem;margin-top:3px;">
      點擊「▶ 開始分析」，AI 將自動診斷電壓趨勢與風險等級
    </div>
  </div>
</div>""", unsafe_allow_html=True)
    ia, ib = st.columns([5,1])
    with ia:
        pass
    with ib:
        if st.button("▶ 開始分析", type="primary", key="ai_run"):
            with st.spinner("分析中..."):
                try:
                    hist = [{"t":str(r["time"])[:16],"v":round(float(r["voltage"]),2)}
                            for _,r in sub.tail(20).iterrows() if not pd.isna(r.get("voltage"))]
                    trend = "未知"
                    if len(hist)>=2:
                        rv = [h["v"] for h in hist[-6:]]
                        trend = "上升" if rv[-1]>rv[0] else "下降"
                    nh = datetime.now().hour
                    ctx = "夜間放電" if nh>=18 or nh<6 else "白天應充電"
                    vl  = hist[-1]["v"] if hist else "N/A"
                    # ── 本地智慧診斷引擎（全情境規則）──
                    lines = []
                    is_day = 6 <= nh < 18

                    # 計算變化速率（每筆平均變化量）
                    rv6 = [h["v"] for h in hist[-6:]] if len(hist) >= 2 else []
                    if len(rv6) >= 2:
                        rate = (rv6[-1] - rv6[0]) / max(len(rv6)-1, 1)
                    else:
                        rate = 0.0
                    fast_drop  = rate < -0.15   # 急速下降
                    slow_drop  = -0.15 <= rate < -0.03
                    stable_v   = -0.03 <= rate <= 0.03
                    slow_rise  = 0.03 < rate <= 0.15
                    fast_rise  = rate > 0.15

                    # 感測器卡死偵測（近10筆標準差極小）
                    rv10 = [h["v"] for h in hist[-10:]]
                    import statistics as _st
                    sensor_stuck = len(rv10) >= 5 and _st.pstdev(rv10) < 0.02

                    # 電壓區間
                    V_EMERG  = VOLTAGE_MIN - 1.5   # 緊急低壓
                    V_WARN   = VOLTAGE_MIN          # 警戒低壓
                    V_OVER   = VOLTAGE_MAX          # 高壓上限
                    V_DANGER = VOLTAGE_MAX + 0.5    # 過充危險

                    if not isinstance(vl, float):
                        lines += ["① 無法取得有效電壓數值，感測器可能離線或資料中斷。",
                                  "② 風險：中｜無法評估站台電源狀態。",
                                  "③ 建議：確認 RTU 設備與資料傳輸鏈路是否正常，若持續無資料請派員勘查。"]

                    elif sensor_stuck:
                        lines += [f"① 電壓長期固定於 {vl}V，讀值異常穩定（標準差<0.02V），疑似感測器卡死或通訊凍結。",
                                  "② 風險：中｜數值不可信，實際電壓未知。",
                                  "③ 建議：重啟遠端監控模組，若重啟後仍相同讀值則需現場檢查感測器。"]

                    elif vl < V_EMERG:
                        # 緊急低壓（< 11V）
                        if is_day:
                            lines += [f"① 【緊急】白天充電期電壓僅 {vl}V，遠低於警戒值 {V_WARN}V，太陽能系統嚴重異常——面板可能故障、遮蔽或充電控制器損壞。",
                                      "② 風險：高｜設備可能在數小時內因過低電壓自動斷電，通訊中斷。",
                                      "③ 建議：立即派員前往站台，優先檢查太陽能板連接、充電控制器輸出電壓，並確認設備負載是否異常偏高。"]
                        else:
                            lines += [f"① 【緊急】夜間電壓已降至 {vl}V，電池電量幾近耗盡，設備隨時可能斷電。",
                                      "② 風險：高｜若日出前無法維持供電，通訊中繼功能將失效。",
                                      "③ 建議：立即評估是否啟動緊急供電方案（臨時發電機），並於日出後確認太陽能充電是否恢復正常。"]

                    elif vl < V_WARN:
                        # 低壓警戒區（11V ~ 12.5V）
                        if is_day and fast_drop:
                            lines += [f"① 白天充電期電壓 {vl}V 且急速下降（每筆 {rate:.2f}V），太陽能充電量不敷負載消耗，可能為陰雨遮蔽或面板故障。",
                                      "② 風險：高｜充電無法補足放電，若持續將進入緊急低壓。",
                                      "③ 建議：確認當日天氣狀況，檢查太陽能板是否遭遮蔽，考慮減少站台非必要負載。"]
                        elif is_day and (slow_drop or stable_v):
                            lines += [f"① 白天充電期電壓 {vl}V，低於正常下限但趨勢{('穩定' if stable_v else '緩降')}，太陽能充電量略不足。",
                                      "② 風險：中｜電壓偏低，若天氣轉差可能加速惡化。",
                                      "③ 建議：監控下午充電高峰（10~14時）是否有回升，若日落前仍未回到正常範圍則安排隔日檢查。"]
                        elif is_day and (slow_rise or fast_rise):
                            lines += [f"① 白天充電期電壓 {vl}V 並持續回升（每筆 {rate:.2f}V），電池正在從低電量狀態充電回復。",
                                      "② 風險：低｜系統正在自我回復，趨勢正向。",
                                      "③ 建議：繼續觀察，預計數小時後應可回到正常電壓範圍，無需立即干預。"]
                        elif not is_day and fast_drop:
                            lines += [f"① 夜間電壓 {vl}V 且急速下降（每筆 {rate:.2f}V），放電速率異常偏高，可能有設備異常耗電。",
                                      "② 風險：高｜按此速率恐在日出前達到緊急低壓，設備斷電風險高。",
                                      "③ 建議：檢查站台是否有設備異常運作，評估是否需緊急介入，並確認日出時間作為充電回復基準。"]
                        elif not is_day and slow_drop:
                            lines += [f"① 夜間電壓 {vl}V，低壓警戒區間且緩慢下降，屬偏重放電狀態。",
                                      "② 風險：中｜若電池容量不足，日出前可能跌入緊急低壓。",
                                      "③ 建議：監控夜間最低點，確認日出後充電是否能及時回升，必要時縮減夜間設備耗電。"]
                        else:
                            lines += [f"① 電壓 {vl}V 位於低壓警戒區，{'白天' if is_day else '夜間'}趨勢穩定。",
                                      "② 風險：中｜電壓偏低但暫時穩定。",
                                      "③ 建議：持續監控，觀察是否有進一步惡化趨勢。"]

                    elif vl <= V_OVER:
                        # 正常電壓區（12.5V ~ 15V）
                        margin = vl - V_WARN
                        if is_day and fast_rise:
                            lines += [f"① 白天充電期電壓 {vl}V 快速上升（每筆 {rate:.2f}V），太陽能充電旺盛，電池正積極補電。",
                                      "② 風險：低｜充電狀態良好，需留意是否過衝至上限。",
                                      "③ 建議：確認充電控制器限壓功能正常運作，避免超過 {V_OVER}V 後持續衝高。"]
                        elif is_day and (slow_rise or stable_v):
                            lines += [f"① 白天充電期電壓 {vl}V，充電與負載平衡良好，系統運作正常。",
                                      "② 風險：低｜電壓穩定在正常範圍。",
                                      "③ 建議：維持現狀，系統無需干預。"]
                        elif is_day and slow_drop and margin < 1.0:
                            lines += [f"① 白天充電期電壓 {vl}V 緩慢下降，距低壓警戒僅 {margin:.1f}V，負載略大於充電輸入。",
                                      "② 風險：中｜若天氣轉差或下午日照不足，可能進入低壓區。",
                                      "③ 建議：注意下午天氣，確認太陽能板無遮蔽，並觀察日落前電壓是否止跌。"]
                        elif is_day and fast_drop:
                            lines += [f"① 白天充電期電壓 {vl}V 卻急速下降（每筆 {rate:.2f}V），充電系統可能突然失效或負載暴增。",
                                      "② 風險：高｜異常放電速率，需立即排查原因。",
                                      "③ 建議：立即確認太陽能板輸出、充電控制器狀態，以及是否有設備短路或異常大電流消耗。"]
                        elif not is_day and stable_v:
                            lines += [f"① 夜間電壓 {vl}V 穩定，電池電量充足，正常放電維持設備供電。",
                                      "② 風險：低｜夜間放電正常。",
                                      "③ 建議：維持現狀，預計明日日出後太陽能充電恢復正常。"]
                        elif not is_day and slow_drop:
                            lines += [f"① 夜間電壓 {vl}V 緩慢下降（每筆 {rate:.2f}V），屬正常夜間放電行為。",
                                      "② 風險：低｜放電速率正常，電量充裕可維持整夜供電。",
                                      "③ 建議：無需干預，觀察日出後充電回復情形。"]
                        elif not is_day and fast_drop and margin < 1.5:
                            lines += [f"① 夜間電壓 {vl}V 且快速下降（每筆 {rate:.2f}V），放電速率偏高，電池可能在日出前跌入低壓警戒。",
                                      "② 風險：中｜需監控夜間最低點。",
                                      "③ 建議：確認站台設備是否有異常耗電，並注意日出時間（約6時）充電恢復時機。"]
                        elif not is_day and (slow_rise or fast_rise):
                            lines += [f"① 【異常】夜間電壓 {vl}V 卻持續上升，無市電情況下夜間充電來源不明，可能為備用發電機啟動或感測器異常。",
                                      "② 風險：中｜夜間上升屬非預期現象，需確認原因。",
                                      "③ 建議：確認是否有臨時供電設備啟動，或感測器讀值是否正確。"]
                        else:
                            lines += [f"① 電壓 {vl}V 正常，{'白天充電' if is_day else '夜間放電'}期間趨勢{trend}，系統運作正常。",
                                      "② 風險：低｜無異常。",
                                      "③ 建議：維持現狀，定期確認數據回報正常。"]

                    elif vl <= V_DANGER:
                        # 高壓區（15V ~ 15.5V）
                        if is_day and fast_rise:
                            lines += [f"① 白天充電期電壓 {vl}V 且快速上升，電池接近滿充，充電控制器應即將切換至浮充模式。",
                                      "② 風險：低｜正常充飽過程，但需確認控制器正常限壓。",
                                      "③ 建議：確認充電控制器是否在 {V_OVER}V 附近正常切入限壓保護，避免持續過充。"]
                        elif is_day and stable_v:
                            lines += [f"① 白天充電期電壓 {vl}V 穩定於高壓區，可能為浮充維護狀態，電池已滿電。",
                                      "② 風險：低｜電池滿電，系統良好。",
                                      "③ 建議：確認充電控制器浮充電壓設定正確（通常 13.5~13.8V），若長期高於 {V_OVER}V 則檢查控制器設定。"]
                        else:
                            lines += [f"① 電壓 {vl}V 偏高，超過正常上限 {V_OVER}V，趨勢{trend}。",
                                      "② 風險：中｜若長期維持高壓可能損害電池壽命。",
                                      "③ 建議：確認充電控制器限壓設定，並觀察是否在短時間內自動回落至正常範圍。"]

                    else:
                        # 過充危險區（> 15.5V）
                        lines += [f"① 【警告】電壓 {vl}V 嚴重超過安全上限 {V_DANGER}V，充電控制器限壓功能可能失效，電池有過充損壞風險。",
                                  "② 風險：高｜持續過充將縮短電池壽命，嚴重時可能導致電池膨脹或損壞。",
                                  "③ 建議：立即檢查充電控制器是否正常運作，必要時暫時斷開太陽能板輸入，並安排設備檢修。"]

                    st.session_state["ai_result"] = "\n".join(lines)
                    st.session_state["ai_station"] = sel
                    st.session_state["ai_station"] = sel
                except Exception as e:
                    st.session_state["ai_result"]  = f"分析失敗：{e}"
                    st.session_state["ai_station"] = sel

    if st.session_state.get("ai_station")==sel and st.session_state.get("ai_result"):
        result = st.session_state["ai_result"]
        risk   = "中"
        for line in result.split("\n"):
            if "低" in line and "風險" in line: risk="低"
            if "高" in line and "風險" in line: risk="高"
        rc = {"低":"#4ade80","中":"#fbbf24","高":"#f87171"}.get(risk,"#9ca3af")
        rb = {"低":"#14532d","中":"#78350f","高":"#7f1d1d"}.get(risk,"#374151")
        st.markdown(f"""
<div style="background:#1e2432;border:1px solid #2d3748;border-radius:10px;padding:16px 20px;margin-top:6px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
    <span style="color:#d1d5db;font-size:0.85rem;font-weight:600;">診斷結果</span>
    <span style="background:{rb};color:{rc};font-size:0.72rem;padding:2px 10px;
      border-radius:4px;font-weight:600;">風險：{risk}</span>
    <span style="color:#4b5563;font-size:0.72rem;margin-left:auto;">
      {datetime.now().strftime('%Y-%m-%d %H:%M')} · {sname(sel)}</span>
  </div>
  <div style="color:#d1d5db;font-size:0.88rem;line-height:1.85;white-space:pre-wrap;">{result}</div>
</div>""", unsafe_allow_html=True)
