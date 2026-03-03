# streamlit_app.py

"""
Hermes — Streamlit MVP UI.
Validates the full pipeline before building the production web frontend.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from src import config
from src import runtime_config
from src.services.speedtest_runner import SpeedtestRunner
from src.result_dispatcher import ResultDispatcher, DispatchError
from src.exporters.csv_exporter import CSVExporter
from main import run_once, build_scheduler, update_schedule

# --- Page config ---
st.set_page_config(
    page_title="Hermes",
    page_icon="📡",
    layout="centered",
)


# --- Cached resources ---
@st.cache_resource
def get_service() -> SpeedtestRunner:
    return SpeedtestRunner()


@st.cache_resource
def get_dispatcher() -> ResultDispatcher:
    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("csv", CSVExporter(path=config.CSV_LOG_PATH))
    return dispatcher


@st.cache_resource
def get_scheduler():
    return build_scheduler(get_service(), get_dispatcher())


# --- Helpers ---
def load_csv() -> pd.DataFrame | None:
    if not config.CSV_LOG_PATH.exists():
        return None
    df = pd.read_csv(config.CSV_LOG_PATH)
    if df.empty:
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp", ascending=False)
    return df


# --- UI ---
st.title("📡 Hermes")
st.caption("Speedtest Monitor — MVP")

st.divider()

# --- Run Test ---
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("Run a Test")
    st.write("Triggers a full download, upload, and ping test. Takes ~30 seconds.")
with col2:
    run_button = st.button("▶ Run Now", use_container_width=True, type="primary")

if run_button:
    with st.spinner("Running speedtest... this takes about 30 seconds."):
        try:
            result = get_service().run()
            try:
                get_dispatcher().dispatch(result)
                st.success("Test complete and logged.")
            except DispatchError as e:
                st.warning(f"Test ran but some exporters failed: {e.failures}")

            m1, m2, m3 = st.columns(3)
            m1.metric("⬇ Download", f"{result.download_mbps} Mbps")
            m2.metric("⬆ Upload", f"{result.upload_mbps} Mbps")
            m3.metric("📶 Ping", f"{result.ping_ms} ms")
            st.caption(f"Server: {result.server_name} — {result.server_location}")

        except RuntimeError as e:
            st.error(f"Speedtest failed: {e}")

st.divider()

# --- Schedule Control ---
st.subheader("Schedule")

current_interval = runtime_config.get_interval_minutes(default=config.SPEEDTEST_INTERVAL_MINUTES)
st.caption(f"Current interval: every **{current_interval} minutes**")

new_interval = st.number_input(
    "New interval (minutes)",
    min_value=1,
    max_value=1440,   # 24 hours max
    value=current_interval,
    step=5,
)

if st.button("💾 Save Schedule"):
    if new_interval == current_interval:
        st.info("Interval is already set to that value.")
    else:
        try:
            update_schedule(get_scheduler(), new_interval)
            st.success(f"Schedule updated — next run in {new_interval} minutes.")
            st.rerun()  # Refresh so the caption reflects the new value
        except Exception as e:
            st.error(f"Failed to update schedule: {e}")

st.divider()

# --- History ---
st.subheader("Run History")

df = load_csv()

if df is None:
    st.info("No runs logged yet. Hit 'Run Now' to start.")
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Runs", len(df))
    m2.metric("Avg Download", f"{df['download_mbps'].mean():.1f} Mbps")
    m3.metric("Avg Upload", f"{df['upload_mbps'].mean():.1f} Mbps")
    m4.metric("Avg Ping", f"{df['ping_ms'].mean():.1f} ms")

    st.line_chart(
        df.set_index("timestamp")[["download_mbps", "upload_mbps"]],
        use_container_width=True,
    )

    with st.expander("Raw data"):
        st.dataframe(df, use_container_width=True, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download CSV",
        data=csv_bytes,
        file_name="speedtest_results.csv",
        mime="text/csv",
    )