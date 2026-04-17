# streamlit_app.py

"""
Hermes — Streamlit MVP UI.
Validates the full pipeline before building the production web frontend.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st
import pandas as pd

import src.config as config
import src.runtime_config as runtime_config

_tz_name = os.getenv("TZ", "UTC")
try:
    _DISPLAY_TZ = ZoneInfo(_tz_name)
except ZoneInfoNotFoundError:
    _DISPLAY_TZ = ZoneInfo("UTC")

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
    """Load and return the CSV run history, or None if unavailable/empty."""
    if not Path(config.CSV_LOG_PATH).exists():
        return None
    data = pd.read_csv(config.CSV_LOG_PATH)
    if data.empty:
        return None
    data["timestamp"] = (
        pd.to_datetime(data["timestamp"], utc=True)
        .dt.tz_convert(_DISPLAY_TZ)
        .dt.tz_localize(None)
    )
    data = data.sort_values("timestamp", ascending=False)
    return data


# --- UI ---
st.title("📡 Hermes")
st.caption(f"Speedtest Monitor — v{config.APP_VERSION}")

# Disable browser scroll-restoration and scroll to top on every full-page render.
# Fragment reruns skip module-level code, so this does not fire on widget interactions.
st.html(
    """
    <script>
      if ('scrollRestoration' in window.parent.history) {
        window.parent.history.scrollRestoration = 'manual';
      }
      var el = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
      if (el) el.scrollTo({top: 0, behavior: 'instant'});
    </script>
    """
)

st.divider()


# --- Run Test ---
def _poll_trigger_state() -> str:
    """
    Renders polling UI and returns the rerun scope needed, or "none".
    Caller is responsible for calling st.rerun() so scope="fragment" is
    invoked directly inside the @st.fragment-decorated function.
    """
    elapsed = time.time() - st.session_state.get("trigger_time", time.time())
    if elapsed > 120:
        st.error("⚠ Test timed out — check connection and try again.")
        st.session_state["trigger_fired"] = False
        return "none"
    elif runtime_config.is_running():
        st.write("🔄 Running speedtest… this takes ~30 seconds.")
        return "fragment"
    else:
        # Compare last_run_at against the moment the button was pressed.
        # set_last_run_at() is called inside run_once() before mark_done(),
        # so by the time is_running() returns False the timestamp is already
        # written — no race condition with the CSV file.
        last_run_raw = runtime_config.get_last_run_at()
        trigger_time: float = st.session_state.get("trigger_time", 0.0)
        completed = False
        if last_run_raw:
            try:
                completed = (
                    datetime.fromisoformat(last_run_raw).timestamp() > trigger_time
                )
            except (ValueError, TypeError):
                pass

        if completed:
            df_now = load_csv()
            if df_now is not None:
                latest = df_now.iloc[0]
                # Store result in session_state so it survives the full-page rerun.
                st.session_state["last_result"] = {
                    "download": latest["download_mbps"],
                    "upload": latest["upload_mbps"],
                    "ping": latest["ping_ms"],
                    "server": latest["server_name"],
                    "location": latest["server_location"],
                }
            st.session_state["trigger_fired"] = False
            return "app"
        else:
            # Trigger written but scheduler hasn't picked it up yet (within 30s poll window).
            st.info("⏳ Waiting for the scheduler to pick up the test…")
            return "fragment"


@st.fragment
def run_test_section() -> None:
    """Renders the Run a Test card and handles trigger polling."""
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Run a Test")
        st.write("Triggers a full download, upload, and ping test. Takes ~30 seconds.")
    with col2:
        run_button = st.button("▶ Run Now", width="stretch", type="primary")

    # Show last completed result if present.
    if st.session_state.get("last_result"):
        result = st.session_state["last_result"]
        st.write("✅ Test complete and logged.")
        c1, c2, c3 = st.columns(3)
        c1.metric("⬇ Download", f"{result['download']:.2f} Mbps")
        c2.metric("⬆ Upload", f"{result['upload']:.2f} Mbps")
        c3.metric("📶 Ping", f"{result['ping']:.2f} ms")
        st.caption(f"Server: {result['server']} — {result['location']}")

    if run_button:
        st.session_state["trigger_fired"] = True
        st.session_state["trigger_time"] = time.time()
        st.session_state.pop("last_result", None)
        runtime_config.trigger_run()
        # No st.rerun() here — the button press already triggered a fragment rerun.
        # Falling through to the polling block keeps us inside the fragment context,
        # which is required for st.rerun(scope="fragment") to be valid.

    # Show live running state — only when this session triggered a run.
    # Gated so page-load during a scheduled test never blocks the UI.
    if st.session_state.get("trigger_fired"):
        rerun_scope = _poll_trigger_state()
        if rerun_scope == "fragment":
            st.rerun(scope="fragment")
        elif rerun_scope == "app":
            st.rerun(scope="app")


run_test_section()

st.divider()


# --- Schedule Control ---


def _render_next_run_status(is_paused: bool, next_run_raw: str | None) -> None:
    """Renders the countdown / paused / running-now status message."""
    if runtime_config.is_running():
        st.info("🔄 Speedtest running now…")
    elif is_paused:
        st.info("⏸ No next run — scans are paused.")
    elif next_run_raw:
        try:
            next_run = datetime.fromisoformat(next_run_raw).astimezone(timezone.utc)
            remaining = (next_run - datetime.now(tz=timezone.utc)).total_seconds()
            if remaining > 0:
                mins, secs = divmod(int(remaining), 60)
                st.info(f"⏱ Next run in **{mins}m {secs:02d}s**")
            else:
                st.info("⏱ Next run imminent…")
        except (ValueError, TypeError):
            pass


@st.fragment(run_every=1)
def schedule_section() -> None:
    """Renders the schedule control and live countdown to the next run."""
    st.subheader("Schedule")

    current_interval = runtime_config.get_interval_minutes(
        default=config.SPEEDTEST_INTERVAL_MINUTES
    )
    is_paused = runtime_config.get_scheduler_paused()
    st.caption(f"Current interval: every **{current_interval} minutes**")

    # Pause / resume toggle
    col_status, col_toggle = st.columns([3, 1])
    with col_status:
        if is_paused:
            st.warning("⏸ Automated scans are **paused**.")
        else:
            st.success("▶ Automated scans are **enabled**.")
    with col_toggle:
        label = "▶ Resume" if is_paused else "⏸ Pause"
        if st.button(label, key="pause_toggle"):
            runtime_config.set_scheduler_paused(not is_paused)
            st.rerun(scope="fragment")

    # Countdown to next run
    _render_next_run_status(is_paused, runtime_config.get_next_run_at())

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
            st.toast(
                "Schedule updated — scheduler will apply the new interval within 30 seconds.",
                icon="✅",
            )


schedule_section()

st.divider()


# --- Exporter Toggles ---
@st.fragment
def exporters_section() -> None:
    """Renders the exporter toggle checkboxes and save button."""
    st.subheader("Exporters")
    st.caption("Enable or disable exporters. Changes take effect within 30 seconds.")

    current_enabled = runtime_config.get_enabled_exporters(
        default=config.ENABLED_EXPORTERS
    )

    new_enabled = []
    for name, label in KNOWN_EXPORTERS.items():
        checked = st.checkbox(
            label, value=name in current_enabled, key=f"exporter_{name}"
        )
        if checked:
            new_enabled.append(name)

    if st.button("💾 Save Exporters"):
        if sorted(new_enabled) == sorted(current_enabled):
            st.info("No changes to exporter configuration.")
        else:
            runtime_config.set_enabled_exporters(new_enabled)
            active = ", ".join(new_enabled) or "none"
            st.toast(
                f"Exporters updated — applying within 30 seconds. Active: {active}",
                icon="✅",
            )


exporters_section()

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
