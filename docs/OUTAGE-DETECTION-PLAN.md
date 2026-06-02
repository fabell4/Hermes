---
layout: default
title: "Outage Detection Implementation Plan"
---
**Status:** Not started  
**Target:** v1.4  
**Estimated Total Effort:** 10–14 hours  

---

## Overview

Three-tier passive outage detection wired into the existing scheduler loop. A new `OutageDetector`
service performs TCP socket probes before each speedtest to distinguish complete connectivity loss
from degraded performance. When an outage is confirmed the speedtest is skipped, an `OutageEvent`
is persisted to SQLite and CSV, and existing alert providers are notified via new `AlertManager`
methods. Optional RIPE Stat BGP enrichment and Cloudflare Radar annotation enrichment provide ISP
context in alert messages.

**Detection tiers:**

| Tier | Condition | Action |
|------|-----------|--------|
| 1 | TCP probe majority-vote fails N consecutive rounds | Skip speedtest; fire `CONNECTIVITY_LOST` alert |
| 2 | Probe passes; speedtest SLA/anomaly flags degraded results | Enrich alert with ASN/BGP context (opt-in) |
| 3 | Probe passes; speedtest raises socket exception | Fire `DNS_FAILURE` or `SPEEDTEST_SERVER_UNREACHABLE` alert |

**Design decisions (confirmed):**

- Outage declared after N consecutive probe-failure rounds (`OUTAGE_PROBE_FAILURE_THRESHOLD`, default
  2), not immediately — mirrors the `AlertManager.failure_threshold` model
- RIPE Stat BGP enrichment is opt-in (`OUTAGE_ISP_CHECK_ENABLED=true`, default `false`)
- Cloudflare Radar annotation enrichment is optional behind `CLOUDFLARE_API_TOKEN`
- Outage suppression (`SharedState.outage_in_progress`) is internal state, separate from the
  user-controlled scan-pause toggle
- BGP enrichment is informational only — does not gate whether an alert fires
- `OutageEvent` records are stored in both SQLite and CSV alongside `SpeedResult`
- ASN is fetched once at startup via RIPE Stat `network-info` and cached in `SharedState`
- BGP and CF check results are cached for 15 minutes to avoid API hammering

**External APIs evaluated:**

| API | Decision | Reason |
|-----|----------|--------|
| `ipapi.co` | Rejected | Free tier explicitly "not for production use" |
| `ip-api.com` | Rejected | HTTP-only on free tier (OWASP A02 cleartext transmission) |
| Downdetector | Rejected | Commercial API only; no public access |
| RIPE Stat `network-info` | **Selected** | Free, no key required, HTTPS, returns ASN from public IP |
| RIPE Stat `bgpupdate-activity` | **Selected (opt-in)** | Free, no key required, HTTPS, BGP instability proxy |
| Cloudflare Radar annotations | **Selected (optional)** | Free with API key; curated outage events |

---

## New Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OUTAGE_PROBE_HOSTS` | csv list | `1.1.1.1:53,8.8.8.8:53,9.9.9.9:53` | TCP probe endpoints |
| `OUTAGE_PROBE_TIMEOUT` | int | `3` | Seconds per probe attempt |
| `OUTAGE_PROBE_FAILURE_THRESHOLD` | int | `2` | Consecutive failure rounds to declare DOWN |
| `OUTAGE_PROBE_QUORUM` | int | `2` | Number of probes that must fail per round to count as a failure |
| `OUTAGE_ISP_CHECK_ENABLED` | bool | `false` | Enable RIPE Stat BGP enrichment |
| `CLOUDFLARE_API_TOKEN` | str/None | None | Enables Cloudflare Radar annotation enrichment |

---

## Phase 1 — Data Layer

### Step 1.1: `OutageEventType` Constants

**Status:** Not started  
**Estimated Effort:** 0.5 hours  
**Priority:** High — required by all other steps  

**Changes Required:**

1. Add `OutageEventType(StrEnum)` enum after `ProviderType` with values: `CONNECTIVITY_LOST`,
   `CONNECTIVITY_RESTORED`, `SPEEDTEST_SERVER_UNREACHABLE`, `DNS_FAILURE`
2. Add probe default constants: `DEFAULT_PROBE_HOSTS`, `DEFAULT_PROBE_TIMEOUT`,
   `DEFAULT_PROBE_FAILURE_THRESHOLD`, `DEFAULT_PROBE_QUORUM`

**Files to modify:**

- `src/constants.py` — add enum after `ProviderType`

**Test coverage:**

- [ ] `OutageEventType` members accessible as strings (StrEnum behaviour)
- [ ] All four values present and unique

---

### Step 1.2: `OutageEvent` Model

**Status:** Not started  
**Estimated Effort:** 0.5 hours  
**Priority:** High  

**Changes Required:**

1. Create `src/models/outage_event.py` with `OutageEvent` dataclass
2. Fields: `event_type: OutageEventType`, `timestamp: datetime`, `duration_seconds: float | None`,
   `isp_name: str | None`, `asn: str | None`, `bgp_unstable: bool | None`,
   `cloudflare_outage_desc: str | None`, `probe_results: str`

**Files to modify:**

- `src/models/outage_event.py` (new file)

**Test coverage:**

- [ ] `OutageEvent` instantiation with required fields only
- [ ] `OutageEvent` instantiation with all optional fields populated

---

### Step 1.3: Config — New Env Vars

**Status:** Not started  
**Estimated Effort:** 0.5 hours  
**Priority:** High  

**Changes Required:**

1. Add the six new env vars to `src/config.py` after the alerting section using existing
   `_get_int()`, `_get_bool()`, `_get_str()`, and `_get_csv_list()` helpers

**Files to modify:**

- `src/config.py` — add six new attributes after alerting section

**Test coverage:**

- [ ] Default values applied when env vars absent
- [ ] `OUTAGE_PROBE_FAILURE_THRESHOLD` respects int coercion
- [ ] `OUTAGE_PROBE_QUORUM` defaults to 2
- [ ] `OUTAGE_ISP_CHECK_ENABLED` defaults to `False`
- [ ] `CLOUDFLARE_API_TOKEN` returns `None` when unset

---

### Step 1.4: `SharedState` — Outage State Fields

**Status:** Not started  
**Estimated Effort:** 0.5 hours  
**Priority:** High  

**Changes Required:**

1. Add module-level globals after existing globals: `_outage_in_progress: bool = False`,
   `_outage_start_time: datetime | None = None`
2. Add thread-safe getter/setter functions: `set_outage_in_progress()`,
   `get_outage_in_progress()`, `set_outage_start_time()`, `get_outage_start_time()`

**Files to modify:**

- `src/shared_state.py` — add globals and accessor functions

**Test coverage:**

- [ ] `get_outage_in_progress()` returns `False` by default
- [ ] `set_outage_in_progress(True)` / `get_outage_in_progress()` round-trip
- [ ] `get_outage_start_time()` returns `None` by default
- [ ] Thread-safety: concurrent reads and writes do not corrupt state

---

## Phase 2 — Detection Service

### Step 2.1: `OutageDetector` Service

**Status:** Not started  
**Estimated Effort:** 3–4 hours  
**Priority:** High  

**Changes Required:**

1. Create `src/services/outage_detector.py` with `OutageDetector` class
2. `check_connectivity() → ConnectivityStatus`: performs TCP `socket.create_connection()` probes
   against `OUTAGE_PROBE_HOSTS`; applies majority-vote quorum; increments or resets
   `_consecutive_probe_failures`; returns `UP` or `DOWN`. Declares `DOWN` only after
   `OUTAGE_PROBE_FAILURE_THRESHOLD` consecutive failure rounds
3. `get_public_ip() → str | None`: HTTPS `GET https://stat.ripe.net/data/network-info/data.json?resource={local_ip}`;
   called once at startup; result cached in `SharedState`
4. `get_isp_asn(ip: str) → str | None`: parses ASN from RIPE Stat `network-info` response
5. `check_bgp_stability(asn: str) → bool`: `GET https://stat.ripe.net/data/bgpupdate-activity/data.json?resource=AS{asn}`;
   result cached 15 minutes; returns `True` if BGP update activity is anomalously high
6. `check_cloudflare_outage(asn: str) → str | None`: `GET https://api.cloudflare.com/client/v4/radar/annotations/outages?asns={asn}`
   with `Authorization: Bearer {CLOUDFLARE_API_TOKEN}`; returns annotation description or `None`;
   only called when token is set; result cached 15 minutes
7. Internal state: `_consecutive_probe_failures: int`, `_bgp_cache: dict[str, tuple[bool, datetime]]`,
   `_cf_cache: dict[str, tuple[str | None, datetime]]`

**Files to modify:**

- `src/services/outage_detector.py` (new file)

**Test coverage:**

- [ ] `check_connectivity()` returns `DOWN` when quorum of probes fail
- [ ] `check_connectivity()` returns `UP` when fewer than quorum fail
- [ ] Consecutive failure counter increments; resets on first `UP` round
- [ ] `DOWN` not declared until `OUTAGE_PROBE_FAILURE_THRESHOLD` consecutive failure rounds
- [ ] Single `UP` round restores `UP` state
- [ ] `get_isp_asn()` result cached; `get_public_ip()` only called once
- [ ] BGP cache honours 15-minute TTL; fresh call made after expiry
- [ ] CF Radar not called when `CLOUDFLARE_API_TOKEN` is unset
- [ ] CF Radar result cached 15 minutes
- [ ] All HTTP calls use HTTPS; plain HTTP URLs rejected

---

### Step 2.2: `AlertManager` — Outage Methods

**Status:** Not started  
**Estimated Effort:** 1.5 hours  
**Priority:** High  

**Changes Required:**

1. Modify `record_failure()` at line 100 in `src/services/alert_manager.py`: add early return
   (no-op) when `SharedState.get_outage_in_progress() is True`
2. Add `record_outage_start(isp_name: str | None, bgp_context: str | None) -> None` after
   `reset()` at line 301: sets `SharedState.outage_in_progress = True`, resets
   `_consecutive_failures`, sends outage-start alert via existing `_send_alert_async()`
3. Add `record_outage_recovered(duration_s: float) -> None`: sets
   `SharedState.outage_in_progress = False`, sends recovery alert with duration in message

**Files to modify:**

- `src/services/alert_manager.py` — modify `record_failure()` at line 100; add two methods after `reset()` at line 301

**Test coverage:**

- [ ] `record_failure()` is a no-op when `outage_in_progress = True`
- [ ] `record_failure()` operates normally when `outage_in_progress = False`
- [ ] `record_outage_start()` sets `SharedState.outage_in_progress = True`
- [ ] `record_outage_start()` resets `_consecutive_failures` to zero
- [ ] `record_outage_start()` dispatches alert with ISP name and BGP context in message
- [ ] `record_outage_recovered()` sets `SharedState.outage_in_progress = False`
- [ ] `record_outage_recovered()` dispatches alert with duration in message
- [ ] Cooldown still applies to outage-start alert

---

## Phase 3 — Integration

### Step 3.1: Wire `OutageDetector` into `run_once()`

**Status:** Not started  
**Estimated Effort:** 2 hours  
**Priority:** High  

**Changes Required:**

1. Add `outage_detector: OutageDetector | None = None` parameter to `run_once()` at line 159
2. At the top of `run_once()` body, call `outage_detector.check_connectivity()` when detector is
   not `None`
3. If `ConnectivityStatus.DOWN`: dispatch `OutageEvent(CONNECTIVITY_LOST, ...)`, call
   `alert_manager.record_outage_start()`, return early (skip speedtest)
4. If state transitions from DOWN to UP: dispatch `OutageEvent(CONNECTIVITY_RESTORED, duration=...)`,
   call `alert_manager.record_outage_recovered()`
5. In the `except RuntimeError` block (line 211): inspect exception `__cause__` — `socket.gaierror`
   maps to `OutageEventType.DNS_FAILURE`; `socket.timeout` / `ConnectionError` maps to
   `OutageEventType.SPEEDTEST_SERVER_UNREACHABLE`; then fall through to existing
   `alert_manager.record_failure(str(e))`
6. Construct `OutageDetector` in `_poll_once()` at line 264 (or in `main()` at line 417) and
   pass through; confirm via `_validate_environment()` at line 404 that required config is present

**Files to modify:**

- `src/main.py` — modify `run_once()` at line 159; update `_poll_once()` at line 264 and `main()` at line 417

**Test coverage:**

- [ ] `run_once()` returns early without calling speedtest runner when detector returns `DOWN`
- [ ] `run_once()` dispatches `CONNECTIVITY_LOST` event on DOWN
- [ ] `run_once()` dispatches `CONNECTIVITY_RESTORED` event with correct duration when transitioning UP
- [ ] `socket.gaierror` in speedtest produces `DNS_FAILURE` event type
- [ ] `socket.timeout` in speedtest produces `SPEEDTEST_SERVER_UNREACHABLE` event type
- [ ] `outage_detector=None` (default) preserves existing behaviour unchanged

---

## Phase 4 — Persistence

### Step 4.1: SQLite `outage_events` Table

**Status:** Not started  
**Estimated Effort:** 1 hour  
**Priority:** Medium  

**Changes Required:**

1. Add `_CREATE_OUTAGE_TABLE` DDL constant to `src/exporters/sqlite_exporter.py` after the
   existing `_CREATE_INDEX` constant at line 47:

```sql
CREATE TABLE IF NOT EXISTS outage_events (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type              TEXT    NOT NULL,
    timestamp               TEXT    NOT NULL,
    duration_seconds        REAL,
    isp_name                TEXT,
    asn                     TEXT,
    bgp_unstable            INTEGER,
    cloudflare_outage_desc  TEXT,
    probe_results           TEXT    NOT NULL
)
```

1. Append migration tuple to `_MIGRATIONS` list at line 105:
   `("add_outage_events_table", _CREATE_OUTAGE_TABLE)`
2. Add `export_outage_event(event: OutageEvent) -> None` method after `export()` at line 153

**Files to modify:**

- `src/exporters/sqlite_exporter.py` — add DDL constant after line 47;
append to `_MIGRATIONS` at line 105; add method after line 153

**Test coverage:**

- [ ] Migration applied idempotently (running `_init_db()` twice does not raise)
- [ ] `outage_events` table created on first `_init_db()`
- [ ] `export_outage_event()` inserts all column values correctly
- [ ] `duration_seconds` stored as `NULL` when field is `None`
- [ ] `bgp_unstable` stored as `0`/`1` integer

---

### Step 4.2: CSV `outage_events` Export

**Status:** Not started  
**Estimated Effort:** 0.5 hours  
**Priority:** Low  

**Changes Required:**

1. Add `OUTAGE_FIELDNAMES` list to `src/exporters/csv_exporter.py` after `FIELDNAMES` at line 13
2. Add `export_outage_event(event: OutageEvent) -> None` method after `export()` at line 71;
   writes to a separate `outage_events.csv` file using the same rotation and prune logic as the
   main results CSV

**Files to modify:**

- `src/exporters/csv_exporter.py` — add `OUTAGE_FIELDNAMES` after line 13; add method after line 71

**Test coverage:**

- [ ] `outage_events.csv` created when it does not yet exist
- [ ] `export_outage_event()` appends a row with correct field names and values
- [ ] File rotation triggers at same size threshold as `results.csv`

---

## Phase 5 — API

### Step 5.1: Outage API Routes

**Status:** Not started  
**Estimated Effort:** 1.5 hours  
**Priority:** Medium  

**Changes Required:**

1. Create `src/api/routes/outages.py` with `router = APIRouter(tags=["outages"])`
2. `GET /outages`: paginated list of `OutageEvent` records from SQLite; mirrors the `ResultsPage`
   pattern in `src/api/routes/results.py` with `page` and `page_size` (max 500) query params
3. `GET /outage-status`: returns `{ "outage_in_progress": bool, "outage_start_time": str | null }`
   from `SharedState`
4. Register router in `src/api/main.py` at line 156 (after `analysis.router`):
   `app.include_router(outages.router, prefix="/api")`

**Files to modify:**

- `src/api/routes/outages.py` (new file)
- `src/api/main.py` — add `include_router` call at line 156

**Test coverage:**

- [ ] `GET /api/outages` returns empty list when no events recorded
- [ ] `GET /api/outages` pagination: `page=1&page_size=10` returns correct slice and correct `total`
- [ ] `GET /api/outages` rejects `page_size` > 500
- [ ] `GET /api/outage-status` returns `outage_in_progress: false` by default
- [ ] `GET /api/outage-status` reflects `SharedState` after `record_outage_start()` called

---

## Open / Deferred Questions

- **Recovery threshold:** Current preference is that one successful probe round restores the UP
  state. Alternative: require M consecutive successes before clearing DOWN to reduce flap noise.
  Deferred until real-world testing.
- **DNS failure sub-type handling:** Tier 3 `DNS_FAILURE` events currently fall through to the
  existing `record_failure()` alert path. A fully separate alert flow (skip `record_failure()`,
  use outage-style message) is deferred.
- **BGP enrichment latency:** RIPE Stat `bgpupdate-activity` data can lag real-time BGP events by
  several minutes. Acceptable given enrichment is informational only.
- **CF Radar editorial lag:** Cloudflare Radar annotations are curated and may lag 15–60 minutes,
  or not appear at all for minor outages. To be documented in `.env.example`.
