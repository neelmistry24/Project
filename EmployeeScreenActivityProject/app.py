from __future__ import annotations

import json
from pathlib import Path
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from cloud_storage import get_screenshot_url
from config import ensure_directories, load_config
from database import ActivityDatabase
from monitor import Monitor
from reports import export_csv, recent_dataframe, summary_metrics


API_BASE_URL = "http://localhost:8000"
SCREENSHOTS_PER_CATEGORY = 3

CATEGORY_ORDER = ["productive", "non_productive", "idle"]
CATEGORY_LABELS = {
    "productive": "Productive",
    "non_productive": "Non-Productive",
    "idle": "Idle",
}
CATEGORY_COLORS = {
    "productive": "#22c55e",
    "non_productive": "#ff3b3b",
    "idle": "#6d5dfc",
}


def api_request(path: str, method: str = "GET") -> dict[str, object] | None:
    request = Request(f"{API_BASE_URL}{path}", method=method)
    try:
        with urlopen(request, timeout=2) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def backend_online() -> bool:
    health = api_request("/health")
    return bool(health and health.get("status") == "ok")


def set_monitoring_enabled(db: ActivityDatabase, enabled: bool, api_online: bool) -> None:
    if api_online:
        result = api_request(f"/settings/monitoring?enabled={str(enabled).lower()}", method="POST")
        if result is not None:
            return
    db.set_setting("monitoring_enabled", enabled)


def capture_activity(api_online: bool) -> int | None:
    if api_online:
        result = api_request("/capture", method="POST")
        if result and result.get("status") == "captured":
            return int(result["event_id"])
        return None
    return Monitor().capture_once()


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required_columns = [
        "id",
        "captured_at",
        "category",
        "tag",
        "confidence",
        "active_app",
        "window_title",
        "browser_tab",
        "idle_seconds",
        "ocr_text",
        "screenshot_path",
        "explanation",
    ]
    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    if df.empty:
        return df

    df["captured_at"] = pd.to_datetime(df["captured_at"], errors="coerce")
    df["category"] = df["category"].replace({"work": "productive", "distraction": "non_productive"})
    df["category"] = df["category"].fillna("idle")
    df["category_display"] = df["category"].map(CATEGORY_LABELS).fillna(df["category"].astype(str))
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0)
    df["idle_seconds"] = pd.to_numeric(df["idle_seconds"], errors="coerce").fillna(0).astype(int)
    df["active_app"] = df["active_app"].fillna("Unknown").replace("", "Unknown")
    df["tag"] = df["tag"].fillna("general").replace("", "general")
    df["window_title"] = df["window_title"].fillna("").astype(str)
    df["screenshot_path"] = df["screenshot_path"].fillna("").astype(str)
    return df.sort_values("captured_at", ascending=False)


def load_activity_data(db: ActivityDatabase, limit: int, api_online: bool) -> tuple[pd.DataFrame, str]:
    if api_online:
        result = api_request(f"/logs?limit={limit}")
        if result and isinstance(result.get("logs"), list):
            return normalize_dataframe(pd.DataFrame(result["logs"])), "FastAPI"
    return normalize_dataframe(recent_dataframe(db, limit=limit)), "SQLite Database"


def screenshot_source(path_text: str) -> str | None:
    path_text = str(path_text or "").strip()
    if not path_text:
        return None
    if path_text.startswith("http"):
        return path_text
    if path_text.startswith("employee_screenshots/"):
        return get_screenshot_url(path_text)
    local_path = Path(path_text)
    if local_path.exists():
        return str(local_path)
    return None


def inject_styles() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

          :root {
            --nav: #061b34;
            --nav2: #031225;
            --text: #111827;
            --muted: #64748b;
            --border: #e2e8f0;
            --green: #22c55e;
            --red: #ff3b3b;
            --purple: #6d5dfc;
            --blue: #1683f7;
          }

          .stApp {
            background: #f8fafc;
            font-family: 'Inter', sans-serif;
            color: var(--text);
          }

          .block-container {
            max-width: 1620px;
            padding: 2.75rem 1.8rem 2rem;
          }

          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--nav) 0%, var(--nav2) 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
          }

          [data-testid="stSidebar"] * {
            color: #f8fafc;
          }

          [data-testid="stSidebar"] .stButton > button {
            width: 100%;
            justify-content: flex-start;
            border: 0;
            border-radius: 10px;
            padding: 0.75rem 0.9rem;
            color: #f8fafc;
            background: transparent;
            font-weight: 700;
          }

          [data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(16, 185, 129, 0.18);
            color: #ffffff;
          }

          [data-testid="stSidebar"] label,
          [data-testid="stSidebar"] p,
          [data-testid="stSidebar"] span {
            color: #dbeafe;
          }

          .brand {
            display: flex;
            gap: 0.75rem;
            align-items: center;
            margin-bottom: 1.1rem;
          }

          .brand-icon {
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: linear-gradient(135deg, #06b981, #0ea5e9);
            display: grid;
            place-items: center;
            color: white;
            font-weight: 900;
          }

          .brand-title {
            color: #00f0a0;
            font-size: 1.08rem;
            font-weight: 800;
          }

          .brand-sub {
            color: #94a3b8;
            font-size: 0.78rem;
            margin-top: 0.1rem;
          }

          .sidebar-label {
            color: #94a3b8;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-size: 0.75rem;
            margin: 1.35rem 0 0.65rem;
          }

          .source-card {
            margin-top: 2rem;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 0.9rem;
            background: rgba(255,255,255,0.04);
            color: #cbd5e1;
            font-size: 0.8rem;
          }

          .topbar {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 1.25rem;
          }

          .title {
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--text);
            margin-bottom: 0.25rem;
          }

          .subtitle {
            color: #475569;
            font-size: 0.95rem;
          }

          .status-row {
            display: flex;
            gap: 0.9rem;
            align-items: center;
            color: var(--text);
            font-weight: 600;
            font-size: 0.88rem;
          }

          .status-pill {
            background: #e7f8ee;
            color: #047857;
            border-radius: 999px;
            padding: 0.55rem 1rem;
          }

          .metric-card {
            min-height: 156px;
            border-radius: 14px;
            border: 1px solid var(--border);
            background: white;
            padding: 1.25rem;
            box-shadow: 0 10px 30px rgba(15,23,42,0.04);
          }

          .metric-card.green { background: linear-gradient(135deg, #f1fff7, #ffffff); border-color: #bbf7d0; }
          .metric-card.red { background: linear-gradient(135deg, #fff5f5, #ffffff); border-color: #fecaca; }
          .metric-card.purple { background: linear-gradient(135deg, #f7f5ff, #ffffff); border-color: #ddd6fe; }
          .metric-card.blue { background: linear-gradient(135deg, #f0f7ff, #ffffff); border-color: #bfdbfe; }

          .metric-head {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            color: #0f172a;
            font-weight: 800;
            font-size: 0.82rem;
            text-transform: uppercase;
          }

          .metric-icon {
            width: 34px;
            height: 34px;
            border-radius: 9px;
            display: grid;
            place-items: center;
            font-weight: 900;
          }

          .metric-value {
            font-size: 2.45rem;
            font-weight: 800;
            margin: 0.65rem 0 0.1rem;
          }

          .metric-sub {
            color: #334155;
            font-size: 0.92rem;
          }

          .mini-bar {
            height: 4px;
            border-radius: 999px;
            background: #e5e7eb;
            overflow: hidden;
            margin-top: 1rem;
          }

          .mini-fill {
            height: 100%;
            border-radius: 999px;
          }

          .panel {
            background: white;
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.05rem 1.2rem;
            box-shadow: 0 10px 30px rgba(15,23,42,0.035);
          }

          .panel-title {
            color: #0f172a;
            font-size: 0.88rem;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 0.85rem;
          }

          .shot-card {
            border: 1px solid var(--border);
            border-radius: 11px;
            padding: 0.45rem;
            background: white;
          }

          [data-testid="stImage"] img {
            border-radius: 9px;
            aspect-ratio: 16 / 9;
            object-fit: cover;
          }

          .shot-meta {
            padding: 0.45rem 0.35rem 0.1rem;
            color: #1e293b;
            font-size: 0.8rem;
          }

          .badge {
            display: inline-block;
            border-radius: 6px;
            padding: 0.2rem 0.45rem;
            font-weight: 700;
            font-size: 0.76rem;
            margin-bottom: 0.35rem;
          }

          .badge.productive { background: #dcfce7; color: #16a34a; }
          .badge.non_productive { background: #fee2e2; color: #ef4444; }
          .badge.idle { background: #ede9fe; color: #6d5dfc; }

          .stTabs [data-baseweb="tab-list"] {
            gap: 0.55rem;
          }

          .stTabs [data-baseweb="tab"] {
            border: 1px solid var(--border);
            background: #f8fafc;
            border-radius: 8px;
            height: 34px;
            padding: 0 1.1rem;
          }

          .stTabs [aria-selected="true"] {
            background: #16a34a;
            color: white;
          }

          div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
          }

          .stDownloadButton button,
          .stButton button {
            border-radius: 9px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_button(label: str, *, key: str | None = None) -> bool:
    try:
        return st.button(label, key=key, use_container_width=True)
    except TypeError:
        return st.button(label, key=key)


def sidebar_button(label: str, *, key: str | None = None) -> bool:
    try:
        return st.sidebar.button(label, key=key, use_container_width=True)
    except TypeError:
        return st.sidebar.button(label, key=key)


def show_image(image_path: str, caption: str | None = None) -> None:
    try:
        st.image(image_path, caption=caption, use_container_width=True)
    except TypeError:
        st.image(image_path, caption=caption, use_column_width=True)


def screenshot_container():
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


def nav_button(label: str, view: str) -> None:
    if sidebar_button(label, key=f"nav_{view}"):
        st.session_state.view = view


def render_sidebar(db: ActivityDatabase, api_online: bool) -> tuple[int, bool, int]:
    if "view" not in st.session_state:
        st.session_state.view = "dashboard"

    st.sidebar.markdown(
        """
        <div class="brand">
          <div class="brand-icon">EA</div>
          <div>
            <div class="brand-title">Employee Activity</div>
            <div class="brand-sub">AI Activity Monitor</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav_button("Dashboard", "dashboard")
    nav_button("Activity Logs", "logs")
    nav_button("Screenshots", "screenshots")
    nav_button("Reports", "reports")

    st.sidebar.markdown('<div class="sidebar-label">Control Panel</div>', unsafe_allow_html=True)
    enabled = st.sidebar.toggle("Monitoring", value=db.monitoring_enabled())
    set_monitoring_enabled(db, enabled, api_online)

    goal = st.sidebar.slider(
        "Productivity Goal",
        min_value=10,
        max_value=100,
        value=int(db.get_setting("productivity_goal_pct", "70")),
        step=5,
    )
    db.set_setting("productivity_goal_pct", goal)

    limit = st.sidebar.slider("Report Records", 25, 1000, 250, 25)
    auto_refresh = st.sidebar.toggle("Auto Refresh", value=False)

    if sidebar_button("Capture Now", key="capture_now"):
        with st.spinner("Capturing and classifying current screen..."):
            event_id = capture_activity(api_online)
        if event_id:
            st.success(f"Captured event #{event_id}")
        else:
            st.warning("Monitoring is paused.")

    source_text = "FastAPI + SQLite/Supabase" if api_online else "SQLite Database"
    st.sidebar.markdown(
        f"""
        <div class="source-card">
          <div style="font-weight:800;margin-bottom:0.35rem">Data Source</div>
          <div>{source_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return limit, auto_refresh, goal


def render_header(db: ActivityDatabase, api_online: bool) -> None:
    status = "Monitoring Active" if db.monitoring_enabled() else "Monitoring Paused"
    now = pd.Timestamp.now()
    st.markdown(
        f"""
        <div class="topbar">
          <div>
            <div class="title">Activity Dashboard</div>
            <div class="subtitle">Welcome back! Here's what's happening with your productivity today.</div>
          </div>
          <div class="status-row">
            <div class="status-pill">{status}</div>
            <div>{now.strftime("%d %b %Y")}</div>
            <div>{now.strftime("%I:%M:%S %p")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, sub: str, color: str, klass: str, bar_pct: float, icon: str) -> None:
    bar_pct = max(0, min(float(bar_pct), 100))
    st.markdown(
        f"""
        <div class="metric-card {klass}">
          <div class="metric-head">
            <div class="metric-icon" style="background:{color}18;color:{color}">{icon}</div>
            <div>{label}</div>
          </div>
          <div class="metric-value" style="color:{color}">{value}</div>
          <div class="metric-sub">{sub}</div>
          <div class="mini-bar"><div class="mini-fill" style="width:{bar_pct}%;background:{color}"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(metrics: dict[str, float], df: pd.DataFrame) -> None:
    total = int(metrics["total"])
    productive_pct = float(metrics["productive_pct"])
    non_productive_pct = round(metrics["non_productive"] / total * 100, 1) if total else 0.0
    idle_pct = round(metrics["idle"] / total * 100, 1) if total else 0.0

    cols = st.columns(4)
    with cols[0]:
        sub = "Below 70% goal" if productive_pct < 70 else "Goal achieved"
        render_metric_card("Productivity Score", f"{productive_pct:.1f}%", sub, "#16a34a", "green", productive_pct, "▲")
    with cols[1]:
        render_metric_card("Non-Productive", f"{non_productive_pct:.1f}%", f"{metrics['non_productive']} distracted captures", "#ff3b3b", "red", non_productive_pct, "▼")
    with cols[2]:
        render_metric_card("Idle Time", f"{idle_pct:.1f}%", f"{metrics['idle']} idle captures", "#6d5dfc", "purple", idle_pct, "⏳")
    with cols[3]:
        render_metric_card("Total Captures", str(total), "Today", "#1683f7", "blue", min(total * 10, 100), "📁")


def light_layout(fig: go.Figure, height: int = 285) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Inter", "color": "#243455", "size": 12},
        margin={"l": 18, "r": 18, "t": 8, "b": 18},
        legend={"orientation": "h", "y": -0.18, "x": 0.18},
    )
    fig.update_xaxes(gridcolor="#e5e7eb", zerolinecolor="#e5e7eb")
    fig.update_yaxes(gridcolor="#e5e7eb", zerolinecolor="#e5e7eb")
    return fig


def render_charts(df: pd.DataFrame) -> None:
    left, middle, right = st.columns([1.05, 1.45, 1.35])

    counts = df["category"].value_counts().reindex(CATEGORY_ORDER, fill_value=0)
    total = max(int(counts.sum()), 1)

    with left:
        st.markdown('<div class="panel"><div class="panel-title">Activity Split</div>', unsafe_allow_html=True)
        fig = go.Figure(
            go.Pie(
                labels=[CATEGORY_LABELS[item] for item in CATEGORY_ORDER],
                values=counts.tolist(),
                hole=0.58,
                marker={"colors": [CATEGORY_COLORS[item] for item in CATEGORY_ORDER]},
                textinfo="none",
            )
        )
        fig = light_layout(fig, height=255)
        fig.update_layout(showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        for category in CATEGORY_ORDER:
            pct = counts[category] / total * 100
            st.caption(f"{CATEGORY_LABELS[category]}: {pct:.0f}%")
        st.markdown("</div>", unsafe_allow_html=True)

    with middle:
        st.markdown('<div class="panel"><div class="panel-title">Activity Timeline</div>', unsafe_allow_html=True)
        timeline = (
            df.dropna(subset=["captured_at"])
            .sort_values("captured_at")
            .groupby([pd.Grouper(key="captured_at", freq="10min"), "category_display"])
            .size()
            .reset_index(name="events")
        )
        fig = px.bar(
            timeline,
            x="captured_at",
            y="events",
            color="category_display",
            color_discrete_map={
                "Productive": CATEGORY_COLORS["productive"],
                "Non-Productive": CATEGORY_COLORS["non_productive"],
                "Idle": CATEGORY_COLORS["idle"],
            },
        )
        fig = light_layout(fig, height=285)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel"><div class="panel-title">Top Applications</div>', unsafe_allow_html=True)
        app_counts = df["active_app"].value_counts().head(5).sort_values().reset_index()
        app_counts.columns = ["application", "events"]
        fig = px.bar(
            app_counts,
            x="events",
            y="application",
            orientation="h",
            text="events",
            color="events",
            color_continuous_scale=["#1683f7", "#22c55e"],
        )
        fig = light_layout(fig, height=285)
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def screenshot_rows(df: pd.DataFrame, category: str | None = None, limit: int = 5) -> pd.DataFrame:
    rows = df[df["screenshot_path"].astype(str).str.strip() != ""]
    if category:
        rows = rows[rows["category"] == category]
    return rows.sort_values("captured_at", ascending=False).head(limit)


def render_screenshot_card(row: pd.Series) -> None:
    category = str(row["category"])
    image_src = screenshot_source(str(row["screenshot_path"]))
    label = CATEGORY_LABELS.get(category, category.title())
    time_text = row["captured_at"].strftime("%I:%M:%S %p") if pd.notna(row["captured_at"]) else ""
    app = str(row.get("active_app") or "Unknown")
    tag = str(row.get("tag") or "general")

    with screenshot_container():
        if image_src:
            show_image(image_src)
        else:
            st.info("Screenshot unavailable")
        st.markdown(
            f"""
            <div class="shot-meta">
              <span class="badge {category}">{label}</span>
              <span style="float:right;color:#334155;font-size:0.76rem">{time_text}</span>
              <div>{app}</div>
              <div style="color:#475569;font-size:0.75rem;margin-top:0.25rem">{tag}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_recent_screenshots(df: pd.DataFrame) -> None:
    st.markdown('<div class="panel"><div class="panel-title">Recent Screenshots</div>', unsafe_allow_html=True)
    tabs = st.tabs(
        [
            f"All ({len(screenshot_rows(df, None, 1000))})",
            f"Productive ({len(screenshot_rows(df, 'productive', 1000))})",
            f"Non-Productive ({len(screenshot_rows(df, 'non_productive', 1000))})",
            f"Idle ({len(screenshot_rows(df, 'idle', 1000))})",
        ]
    )
    tab_specs = [(None, 5), ("productive", SCREENSHOTS_PER_CATEGORY), ("non_productive", SCREENSHOTS_PER_CATEGORY), ("idle", SCREENSHOTS_PER_CATEGORY)]
    for tab, (category, limit) in zip(tabs, tab_specs):
        with tab:
            rows = screenshot_rows(df, category, limit)
            if rows.empty:
                st.info("No screenshots available for this view.")
                continue
            cols = st.columns(len(rows))
            for col, (_, row) in zip(cols, rows.iterrows()):
                with col:
                    render_screenshot_card(row)
    st.markdown("</div>", unsafe_allow_html=True)


def render_activity_log(df: pd.DataFrame, limit: int = 10) -> None:
    st.markdown('<div class="panel"><div class="panel-title">Recent Activity Log</div>', unsafe_allow_html=True)
    table = df.head(limit).copy()
    table["Captured At"] = table["captured_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    table["Category"] = table["category_display"]
    table["Tag"] = table["tag"]
    table["Confidence"] = (table["confidence"] * 100).round(0).astype(int).astype(str) + "%"
    table["Active App"] = table["active_app"]
    table["Window Title"] = table["window_title"]
    table["Idle (sec)"] = table["idle_seconds"]
    visible = ["Captured At", "Category", "Tag", "Confidence", "Active App", "Window Title", "Idle (sec)"]
    st.dataframe(table[visible], use_container_width=True, hide_index=True)
    st.caption(f"Showing latest {min(limit, len(table))} records")
    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard(db: ActivityDatabase, df: pd.DataFrame, metrics: dict[str, float], api_online: bool) -> None:
    render_header(db, api_online)
    render_kpis(metrics, df)
    st.write("")
    if df.empty:
        st.info("No activity records yet. Use Capture Now or run monitor.py.")
        return
    render_charts(df)
    st.write("")
    render_recent_screenshots(df)
    st.write("")
    render_activity_log(df, limit=10)


def render_logs_page(df: pd.DataFrame) -> None:
    st.markdown('<div class="title">Activity Logs</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("No records available.")
        return
    render_activity_log(df, limit=min(len(df), 250))


def render_screenshots_page(df: pd.DataFrame) -> None:
    st.markdown('<div class="title">Screenshots</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("No screenshots available.")
        return
    render_recent_screenshots(df)


def render_reports_page(df: pd.DataFrame, config) -> None:
    st.markdown('<div class="title">Reports</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("No records available for report.")
        return
    render_charts(df)
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button("Export CSV", data=csv_data, file_name="activity_report.csv", mime="text/csv")
    if safe_button("Save CSV Report", key="save_csv"):
        path = export_csv(df, config.export_dir)
        st.success(f"Report saved to {path}")


def main() -> None:
    st.set_page_config(page_title="ScreenSense Dashboard", page_icon="SS", layout="wide")
    inject_styles()

    config = load_config()
    ensure_directories(config)
    db = ActivityDatabase(config.database_path)
    api_online = backend_online()
    limit, auto_refresh, goal = render_sidebar(db, api_online)

    df, _source = load_activity_data(db, limit, api_online)
    metrics = summary_metrics(df)

    view = st.session_state.get("view", "dashboard")
    if view == "dashboard":
        render_dashboard(db, df, metrics, api_online)
    elif view == "logs":
        render_logs_page(df)
    elif view == "screenshots":
        render_screenshots_page(df)
    elif view == "reports":
        render_reports_page(df, config)

    if auto_refresh:
        time.sleep(10)
        st.rerun()


if __name__ == "__main__":
    main()
