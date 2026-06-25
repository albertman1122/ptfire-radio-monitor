# -*- coding: utf-8 -*-
import streamlit as st
import streamlit_authenticator as stauth
import gspread
import pandas as pd
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import json
from google import genai

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

# ── 登入 ─────────────────────────────────────────────────────────────────────
try:
    creds_cfg = st.secrets.get("credentials", {})
    usernames = creds_cfg.get("usernames", {})
    credentials = {
        "usernames": {
            u: {"name": i["name"], "password": i["password"]}
            for u, i in usernames.items()
        }
    } if usernames else {
        "usernames": {
            "admin": {
                "name": "Admin",
                "password": "$2b$12$Ubd5IT1hnQHyDsKgdnEnZePuy7dgu/zFzZA.4i70LdP7HHRGDtfVq"
            }
        }
    }
    cookie_name = st.secrets.get("cookie", {}).get("name", "power_monitor_auth")
    cookie_key  = st.secrets.get("cookie", {}).get("key", "ptfire2026monitor")
    cookie_exp  = st.secrets.get("cookie", {}).get("expiry_days", 7)
except Exception:
    credentials = {
        "usernames": {
            "admin": {
                "name": "Admin",
                "password": "$2b$12$Ubd5IT1hnQHyDsKgdnEnZePuy7dgu/zFzZA.4i70LdP7HHRGDtfVq"
            }
        }
    }
    cookie_name = "power_monitor_auth"
    cookie_key  = "ptfire2026monitor"
    cookie_exp  = 7

auth = stauth.Authenticate(
    credentials,
    cookie_name,
    cookie_key,
    cookie_expiry_days=cookie_exp,
)
auth.login(location="main")
status = st.session_state.get("authentication_status")
if status is False:
    st.error("帳號或密碼錯誤"); st.stop()
if not status:
    st.info("請輸入帳號密碼"); st.stop()

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

now     = datetime.now()
latest  = {d: df[df["device"]==d].iloc[-1] for d in df["device"].unique()}
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
        m = int((now-row["time"]).total_seconds()/60)
        age = f"{m} 分鐘前"
    is_off = (color == "red")
    cls    = "st-card" + (" offline" if is_off else "") + (" selected" if sel else "")
    return (f'<div class="{cls}">'
            f'<div class="card-name">{sname(dev)}</div>'
            f'<div class="card-volt" style="color:{"#facc15" if color=="green" else "#f87171" if color=="red" else "#fb923c"};">{v_str}</div>'
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
            yaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False, title="電壓 (V)"),
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
      font-size:0.72rem;padding:2px 10px;border-radius:4px;font-weight:600;">Gemini AI</span>
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
            api_key = st.secrets.get("gemini_api_key","")
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
                    prompt = (f"分析無線電中繼台電源（太陽能，無市電）。現{ctx}。"
                              f"站:{sname(sel)}，電壓:{vl}V，正常:{VOLTAGE_MIN}~{VOLTAGE_MAX}V，趨勢:{trend}。"
                              f"近20筆:{json.dumps(hist,ensure_ascii=False)}。"
                              f"繁中3-5句：①原因 ②風險(低/中/高) ③建議。直接回答。")
                    client = genai.Client(api_key=api_key)
                    resp   = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
                    st.session_state["ai_result"]  = resp.text.strip()
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
