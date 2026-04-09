# streamlit_app.py

"""
Hermes — Streamlit MVP UI.
Validates the full pipeline before building the production web frontend.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

import src.config as config
import src.runtime_config as runtime_config

# Friendly labels for the known exporters.
# Keep in sync with EXPORTER_REGISTRY in main.py.
KNOWN_EXPORTERS: dict[str, str] = {
    "csv": "CSV — log results to file",
    "prometheus": "Prometheus — expose /metrics endpoint",
    "loki": "Loki — ship structured logs",
}

# --- Page config ---
st.set_page_config(
    page_title="Hermes",
    page_icon="📡",
    layout="centered",
)


# --- Helpers ---
def load_csv() -> pd.DataFrame | None:
    if not Path(config.CSV_LOG_PATH).exists():
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
    run_button = st.button("▶ Run Now", width="stretch", type="primary")

if run_button:
    runtime_config.trigger_run()
    st.success(
        "Test triggered — the scheduler will run it within seconds. Refresh this page to see the result."
    )

st.divider()

# --- Schedule Control ---
st.subheader("Schedule")

current_interval = runtime_config.get_interval_minutes(
    default=config.SPEEDTEST_INTERVAL_MINUTES
)
st.caption(f"Current interval: every **{current_interval} minutes**")

new_interval = st.number_input(
    "New interval (minutes)",
    min_value=1,
    max_value=1440,
    value=current_interval,
    step=5,
)

if st.button("💾 Save Schedule"):
    if new_interval == current_interval:
        st.info("Interval is already set to that value.")
    else:
        runtime_config.set_interval_minutes(new_interval)
        st.success(
            "Schedule updated — scheduler will apply the new interval within 30 seconds."
        )
        st.rerun()

st.divider()

# --- Exporter Toggles ---
st.subheader("Exporters")
st.caption("Enable or disable exporters. Changes take effect within 30 seconds.")

current_enabled = runtime_config.get_enabled_exporters(default=config.ENABLED_EXPORTERS)

new_enabled = []
for name, label in KNOWN_EXPORTERS.items():
    checked = st.checkbox(label, value=name in current_enabled, key=f"exporter_{name}")
    if checked:
        new_enabled.append(name)

if st.button("💾 Save Exporters"):
    if sorted(new_enabled) == sorted(current_enabled):
        st.info("No changes to exporter configuration.")
    else:
        runtime_config.set_enabled_exporters(new_enabled)
        st.success(
            f"Exporters updated — scheduler will apply within 30 seconds. Active: {', '.join(new_enabled) or 'none'}"
        )
        st.rerun()

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
        width="stretch",
    )

    with st.expander("Raw data"):
        st.dataframe(df, width="stretch", hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download CSV",
        data=csv_bytes,
        file_name="speedtest_results.csv",
        mime="text/csv",
    )
