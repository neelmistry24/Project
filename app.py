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

from config import ensure_directories, load_config
from database import ActivityDatabase
from monitor import Monitor
from reports import export_csv, recent_dataframe, summary_metrics


CATEGORY_TABS = [
    ("productive", "Productive"),
    ("non_productive", "Non-Productive"),
    ("idle", "Idle"),
]

API_BASE_URL = "http://localhost:8000"
SCREENSHOTS_PER_CATEGORY = 3

COLORS = {
    "productive": "#00e5a0",
    "non_productive": "#ff5f5f",
    "idle": "#7c6ff7",
    "gold": "#ffd166",
    "surface": "#111520",
    "surface2": "#171e2e",
    "border": "#1e293b",
    "muted": "#64748b",
    "text": "#e2e8f0",
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
    if not df.empty:
        df["captured_at"] = pd.to_datetime(df["captured_at"], errors="coerce")
        df["category"] = df["category"].replace({"work": "productive", "distraction": "non_productive"})
        df["category_display"] = df["category"].str.replace("_", "-", regex=False).str.title()
        df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0)
    return df


def load_activity_data(db: ActivityDatabase, limit: int, api_online: bool) -> tuple[pd.DataFrame, str]:
    if api_online:
        result = api_request(f"/logs?limit={limit}")
        if result and isinstance(result.get("logs"), list):
            return normalize_dataframe(pd.DataFrame(result["logs"])), "FastAPI"
    return normalize_dataframe(recent_dataframe(db, limit=limit)), "SQLite"


def inject_styles() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@400;500;600;700&display=swap');

          :root {
            --bg: #f6f8fb;
            --surface: #111520;
            --surface2: #171e2e;
            --border: #1e293b;
            --accent: #00e5a0;
            --accent2: #7c6ff7;
            --warn: #ff5f5f;
            --gold: #ffd166;
            --text: #e2e8f0;
            --muted: #64748b;
          }

          .stApp {
            background: var(--bg);
            color: var(--text);
            font-family: 'DM Sans', sans-serif;
          }

          [data-testid="stSidebar"] {
            background: var(--surface);
            border-right: 1px solid var(--border);
          }

          [data-testid="stSidebar"] * {
            color: var(--text);
          }

          [data-testid="stSidebar"] h1,
          [data-testid="stSidebar"] h2,
          [data-testid="stSidebar"] h3,
          [data-testid="stSidebar"] label,
          [data-testid="stSidebar"] p {
            color: var(--text);
          }

          [data-testid="stSidebar"] hr {
            border-color: var(--border);
          }

          .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            max-width: 1500px;
          }

          h1, h2, h3 {
            font-family: 'Space Mono', monospace;
            letter-spacing: 0;
          }

          .screensense-brand {
            display: flex;
            gap: 0.7rem;
            align-items: center;
            margin-bottom: 1rem;
          }

          .brand-mark {
            width: 34px;
            height: 34px;
            display: grid;
            place-items: center;
            border-radius: 8px;
            background: rgba(0, 229, 160, 0.12);
            border: 1px solid rgba(0, 229, 160, 0.25);
            color: var(--accent);
            font-family: 'Space Mono', monospace;
            font-weight: 700;
          }

          .brand-title {
            color: var(--accent);
            font-family: 'Space Mono', monospace;
            font-size: 1.1rem;
            font-weight: 700;
            line-height: 1;
          }

          .brand-sub {
            color: var(--muted);
            font-size: 0.72rem;
            margin-top: 0.2rem;
          }

          .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.55rem 0.8rem;
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-family: 'Space Mono', monospace;
            font-size: 0.78rem;
            margin-bottom: 1rem;
          }

          .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 8px var(--accent);
          }

          .section-label {
            font-family: 'Space Mono', monospace;
            font-size: 0.65rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 2px;
            padding: 0.45rem 0;
            margin: 0.4rem 0 0.7rem;
            border-bottom: 1px solid var(--border);
          }

          .page-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
          }

          .page-title {
            color: #111827;
            font-family: 'Space Mono', monospace;
            font-size: 1.55rem;
            font-weight: 700;
          }

          .page-subtitle {
            color: var(--muted);
            font-size: 0.85rem;
            margin-top: 0.25rem;
          }

          .time-chip {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            color: var(--muted);
            font-family: 'Space Mono', monospace;
            font-size: 0.78rem;
            padding: 0.38rem 0.85rem;
          }

          .kpi-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.15rem 1.25rem;
            min-height: 132px;
            position: relative;
            overflow: hidden;
          }

          .kpi-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: var(--accent);
          }

          .kpi-card.red::before { background: var(--warn); }
          .kpi-card.purple::before { background: var(--accent2); }
          .kpi-card.gold::before { background: var(--gold); }

          .kpi-label {
            color: var(--muted);
            font-family: 'Space Mono', monospace;
            font-size: 0.68rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
          }

          .kpi-value {
            font-size: 2.25rem;
            font-weight: 700;
            line-height: 1.05;
            margin-top: 0.35rem;
          }

          .kpi-sub {
            color: var(--muted);
            font-size: 0.75rem;
            margin-top: 0.35rem;
          }

          .panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.1rem;
            margin-top: 1rem;
          }

          .panel-title {
            color: var(--muted);
            font-family: 'Space Mono', monospace;
            font-size: 0.67rem;
            letter-spacing: 2px;
            margin-bottom: 0.9rem;
            text-transform: uppercase;
          }

          .insight {
            background: var(--surface2);
            border-left: 3px solid var(--accent);
            border-radius: 0 8px 8px 0;
            color: var(--text);
            font-size: 0.84rem;
            margin-bottom: 0.55rem;
            padding: 0.7rem 0.9rem;
          }

          .goal-box {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.9rem;
            color: var(--text);
          }

          .goal-title {
            font-weight: 700;
            font-size: 0.9rem;
          }

          .goal-meta {
            color: var(--muted);
            font-size: 0.75rem;
            margin: 0.35rem 0 0.55rem;
          }

          .progress-shell {
            background: #f6f8fb;
            height: 6px;
            border-radius: 8px;
            overflow: hidden;
          }

          .progress-fill {
            height: 100%;
            border-radius: 8px;
            background: var(--accent);
          }

          .stTabs [data-baseweb="tab-list"] {
            gap: 0.4rem;
          }

          .stTabs [data-baseweb="tab"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--muted);
            height: 38px;
            padding: 0 1rem;
          }

          .stTabs [aria-selected="true"] {
            color: var(--accent);
            border-color: rgba(0, 229, 160, 0.45);
          }

          div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
          }

          .stAlert {
            border-radius: 8px;
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


def show_image(image_path: str, caption: str) -> None:
    try:
        st.image(image_path, caption=caption, use_container_width=True)
    except TypeError:
        st.image(image_path, caption=caption, use_column_width=True)


def render_sidebar(db: ActivityDatabase, api_online: bool) -> tuple[int, bool, int]:
    st.sidebar.markdown(
        """
        <div class="screensense-brand">
          <div class="brand-mark">SS</div>
          <div>
            <div class="brand-title">ScreenSense</div>
            <div class="brand-sub">AI Activity Monitor</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    status = "MONITORING" if db.monitoring_enabled() else "IDLE"
    backend_status = "FastAPI connected" if api_online else "SQLite fallback"
    st.sidebar.markdown(
        f"""
        <div class="status-badge">
          <div class="status-dot"></div>
          <span>{status}</span>
        </div>
        <div style="color:#64748b;font-family:'Space Mono',monospace;font-size:0.7rem;margin-top:-0.55rem;margin-bottom:0.9rem">
          Data source: {backend_status}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown('<div class="section-label">Control Panel</div>', unsafe_allow_html=True)
    enabled = st.sidebar.toggle("Monitoring enabled", value=db.monitoring_enabled())
    set_monitoring_enabled(db, enabled, api_online)

    goal = st.sidebar.slider(
        "Productivity goal",
        min_value=10,
        max_value=100,
        value=int(db.get_setting("productivity_goal_pct", "70")),
        step=5,
    )
    db.set_setting("productivity_goal_pct", goal)

    limit = st.sidebar.slider("Report records", 25, 1000, 250, 25)
    auto_refresh = st.sidebar.toggle("Auto refresh", value=False)

    if safe_button("Manual Capture", key="manual_capture"):
        with st.spinner("Capturing and classifying current screen..."):
            event_id = capture_activity(api_online)
        if event_id:
            st.success(f"Captured event #{event_id}")
        else:
            st.warning("Monitoring is paused.")

    st.sidebar.markdown('<div class="section-label">Reports</div>', unsafe_allow_html=True)
    st.sidebar.caption("Run `monitor.py` in a second terminal for continuous capture.")
    st.sidebar.caption("Run `uvicorn api:app --reload` to connect the FastAPI backend.")

    return limit, auto_refresh, goal


def render_header(df: pd.DataFrame, limit: int, data_source: str) -> None:
    subtitle = "No records loaded yet."
    if not df.empty:
        earliest = df["captured_at"].min()
        latest = df["captured_at"].max()
        subtitle = f"{len(df)} records analyzed from {earliest:%d %b %H:%M} to {latest:%d %b %H:%M}"

    st.markdown(
        f"""
        <div class="page-header">
          <div>
            <div class="page-title">Dashboard</div>
            <div class="page-subtitle">{subtitle} - showing latest {limit} records - source: {data_source}</div>
          </div>
          <div class="time-chip">{pd.Timestamp.now().strftime("%H:%M:%S")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(metrics: dict[str, float], df: pd.DataFrame) -> None:
    total = int(metrics["total"])
    avg_confidence = 0.0 if df.empty else round(float(df["confidence"].mean()) * 100, 1)
    productive_pct = float(metrics["productive_pct"])
    non_productive_pct = 0.0 if total == 0 else round(metrics["non_productive"] / total * 100, 1)
    idle_pct = 0.0 if total == 0 else round(metrics["idle"] / total * 100, 1)

    cards = [
        ("Productivity Score", f"{productive_pct:.1f}%", f"{metrics['productive']} focused captures", COLORS["productive"], ""),
        ("Distraction Rate", f"{non_productive_pct:.1f}%", f"{metrics['non_productive']} distracted captures", COLORS["non_productive"], "red"),
        ("Idle Time", f"{idle_pct:.1f}%", f"{metrics['idle']} idle captures", COLORS["idle"], "purple"),
        ("AI Confidence", f"{avg_confidence:.1f}%", f"{total} total captures", COLORS["gold"], "gold"),
    ]

    cols = st.columns(4)
    for col, (label, value, sub, color, klass) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="kpi-card {klass}">
                  <div class="kpi-label">{label}</div>
                  <div class="kpi-value" style="color:{color}">{value}</div>
                  <div class="kpi-sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def plot_layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font={"color": COLORS["muted"], "family": "DM Sans"},
        margin={"l": 12, "r": 12, "t": 12, "b": 12},
        legend={"orientation": "h", "y": -0.18},
    )
    fig.update_xaxes(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"])
    fig.update_yaxes(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"])
    return fig


def render_charts(df: pd.DataFrame) -> None:
    left, middle, right = st.columns([0.9, 1.4, 1.15])

    with left:
        st.markdown('<div class="panel"><div class="panel-title">Activity Split</div>', unsafe_allow_html=True)
        split = df["category"].value_counts().reindex(["productive", "non_productive", "idle"], fill_value=0)
        labels = ["Productive", "Non-Productive", "Idle"]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=split.tolist(),
                    hole=0.68,
                    marker={"colors": [COLORS["productive"], COLORS["non_productive"], COLORS["idle"]]},
                    textinfo="percent",
                )
            ]
        )
        fig = plot_layout(fig)
        fig.update_layout(showlegend=True, height=260)
        st.plotly_chart(fig, use_container_width=True)
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
                "Productive": COLORS["productive"],
                "Non-Productive": COLORS["non_productive"],
                "Idle": COLORS["idle"],
            },
        )
        fig = plot_layout(fig)
        fig.update_layout(height=260)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel"><div class="panel-title">Top Applications</div>', unsafe_allow_html=True)
        app_counts = (
            df["active_app"]
            .replace("", "Unknown")
            .fillna("Unknown")
            .value_counts()
            .head(6)
            .reset_index()
        )
        app_counts.columns = ["application", "events"]
        fig = px.bar(
            app_counts,
            x="events",
            y="application",
            orientation="h",
            color="events",
            color_continuous_scale=[[0, COLORS["idle"]], [0.55, COLORS["gold"]], [1, COLORS["productive"]]],
        )
        fig = plot_layout(fig)
        fig.update_layout(height=260, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_insights(df: pd.DataFrame, metrics: dict[str, float], goal: int) -> None:
    if df.empty:
        insights = ["No activity has been captured yet."]
    else:
        top_category = df["category_display"].value_counts().idxmax()
        top_app = df["active_app"].replace("", "Unknown").fillna("Unknown").value_counts().idxmax()
        productivity = float(metrics["productive_pct"])
        insights = [
            f"Most common category is {top_category}.",
            f"Most used application is {top_app}.",
        ]
        if productivity < goal:
            insights.append(f"Productivity is below the {goal}% goal. Start a focused work block.")
        else:
            insights.append(f"Productivity is meeting the {goal}% goal.")

    st.markdown('<div class="panel"><div class="panel-title">AI Insights</div>', unsafe_allow_html=True)
    for insight in insights:
        st.markdown(f'<div class="insight">{insight}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_goal(metrics: dict[str, float], goal: int) -> None:
    progress = min(float(metrics["productive_pct"]) / goal, 1.0) if goal else 0.0
    st.markdown(
        f"""
        <div class="panel">
          <div class="panel-title">Goal</div>
          <div class="goal-box">
            <div class="goal-title">Daily Productive Work</div>
            <div class="goal-meta">{metrics["productive_pct"]:.1f}% / {goal}% target</div>
            <div class="progress-shell">
              <div class="progress-fill" style="width:{progress * 100:.0f}%"></div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_screenshot_gallery(df: pd.DataFrame) -> None:
    st.markdown('<div class="panel"><div class="panel-title">Screenshot Gallery</div>', unsafe_allow_html=True)
    st.caption(f"Showing latest {SCREENSHOTS_PER_CATEGORY} screenshots per category.")
    tabs = st.tabs([label for _, label in CATEGORY_TABS])

    for tab, (category, label) in zip(tabs, CATEGORY_TABS):
        with tab:
            category_df = df[
                (df["category"] == category)
                & df["screenshot_path"].notna()
                & (df["screenshot_path"].astype(str).str.strip() != "")
            ].sort_values("captured_at", ascending=False)

            if category_df.empty:
                st.info(f"No {label.lower()} screenshots captured yet.")
                continue

            cols = st.columns(SCREENSHOTS_PER_CATEGORY)
            for index, (_, row) in enumerate(category_df.head(SCREENSHOTS_PER_CATEGORY).iterrows()):
                screenshot_path = Path(str(row["screenshot_path"]))
                caption = f"{label} | {row['captured_at']} | {row.get('active_app', '')}"
                with cols[index % 3]:
                    if screenshot_path.exists():
                        show_image(str(screenshot_path), caption)
                    else:
                        st.warning(f"Missing file: {screenshot_path}")

    st.markdown("</div>", unsafe_allow_html=True)


def render_activity_table(df: pd.DataFrame) -> None:
    st.markdown('<div class="panel"><div class="panel-title">Recent Activity Log</div>', unsafe_allow_html=True)
    visible_columns = [
        "captured_at",
        "category_display",
        "tag",
        "confidence",
        "active_app",
        "window_title",
        "idle_seconds",
        "explanation",
        "screenshot_path",
    ]
    st.dataframe(df[visible_columns], use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="ScreenSense Activity Monitor",
        page_icon="SS",
        layout="wide",
    )
    inject_styles()

    config = load_config()
    ensure_directories(config)
    db = ActivityDatabase(config.database_path)
    api_online = backend_online()
    limit, auto_refresh, goal = render_sidebar(db, api_online)

    df, data_source = load_activity_data(db, limit, api_online)
    metrics = summary_metrics(df)

    render_header(df, limit, data_source)
    render_kpi_cards(metrics, df)

    if metrics["total"] and metrics["productive_pct"] < goal:
        st.warning(f"Productivity is below the {goal}% goal.")

    if df.empty:
        st.info("No records yet. Click Manual Capture or start monitor.py.")
        return

    render_charts(df)

    insight_col, goal_col = st.columns([1.7, 1])
    with insight_col:
        render_insights(df, metrics, goal)
    with goal_col:
        render_goal(metrics, goal)

    render_screenshot_gallery(df)
    render_activity_table(df)

    if safe_button("Export CSV Report", key="export_report"):
        path = export_csv(df, config.export_dir)
        st.success(f"Report saved: {path}")

    if auto_refresh:
        time.sleep(10)
        st.rerun()


if __name__ == "__main__":
    main()
