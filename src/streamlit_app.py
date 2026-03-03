# streamlit_app.py

"""
Streamlit MVP — validates the full speedtest pipeline with a minimal UI.
Replace this with the full web frontend once core logic is confirmed.
"""

import streamlit as st  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
from pathlib import Path
from src.services.speedtest_runner import SpeedtestRunner
from src.result_dispatcher import ResultDispatcher, DispatchError
from src.exporters.csv_exporter import CSVExporter

# --- Page config ---
st.set_page_config(
    page_title="Speedtest",
    page_icon="📡",
    layout="centered",
)

# --- Cached resources ---
# These are instantiated once per session, not on every rerender
@st.cache_resource
def get_service() -> SpeedtestRunner:
    return SpeedtestRunner()

@st.cache_resource
def get_dispatcher() -> ResultDispatcher:
    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("csv", CSVExporter(path="logs/results.csv"))
    return dispatcher


# --- Helpers ---
def load_csv() -> pd.DataFrame | None:
    """Load the CSV log into a DataFrame. Returns None if file doesn't exist or is empty."""
    path = Path("logs/results.csv")
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty:
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp", ascending=False)
    return df


# --- UI ---
st.title("📡 Speedtest Monitor")
st.caption("MVP — testing core pipeline before full web frontend")

st.divider()

# Run button
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("Run a Test")
    st.write("Triggers a full download, upload, and ping test. Takes ~30 seconds.")
with col2:
    run_button = st.button("▶ Run Now", use_container_width=True, type="primary")

if run_button:
    with st.spinner("Running speedtest... this takes about 30 seconds."):
        try:
            service = get_service()
            dispatcher = get_dispatcher()
            result = service.run()

            try:
                dispatcher.dispatch(result)
                st.success("Test complete and logged.")
            except DispatchError as e:
                st.warning(f"Test ran but some exporters failed: {e.failures}")

            # Show this run's result immediately
            st.subheader("Latest Result")
            m1, m2, m3 = st.columns(3)
            m1.metric("⬇ Download", f"{result.download_mbps} Mbps")
            m2.metric("⬆ Upload", f"{result.upload_mbps} Mbps")
            m3.metric("📶 Ping", f"{result.ping_ms} ms")
            st.caption(f"Server: {result.server_name} — {result.server_location}")

        except RuntimeError as e:
            st.error(f"Speedtest failed: {e}")

st.divider()

# Historical results
st.subheader("Run History")

df = load_csv()

if df is None:
    st.info("No runs logged yet. Hit 'Run Now' to start.")
else:
    # Summary metrics across all runs
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Runs", len(df))
    m2.metric("Avg Download", f"{df['download_mbps'].mean():.1f} Mbps")
    m3.metric("Avg Upload", f"{df['upload_mbps'].mean():.1f} Mbps")
    m4.metric("Avg Ping", f"{df['ping_ms'].mean():.1f} ms")

    st.divider()

    # Charts
    st.line_chart(
        df.set_index("timestamp")[["download_mbps", "upload_mbps"]],
        use_container_width=True,
    )

    # Raw table
    with st.expander("Raw data"):
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

    # Download button
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download CSV",
        data=csv_bytes,
        file_name="speedtest_results.csv",
        mime="text/csv",
    )