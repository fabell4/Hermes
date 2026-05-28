/**
 * Core domain types for Hermes — mirrors src/models/speed_result.py
 */

export interface SpeedResult {
  id: number
  timestamp: string        // ISO 8601
  download_mbps: number
  upload_mbps: number
  ping_ms: number
  jitter_ms: number | null
  isp_name: string | null
  server_name: string
  server_location: string
  server_id: number | null
  note?: string | null
}

export interface RuntimeConfig {
  interval_minutes: number
  enabled_exporters: string[]
  scanning_enabled: boolean
  test_window: TestWindow
}

export interface TestWindow {
  enabled: boolean
  start_hour: number  // 0–23 UTC, inclusive
  end_hour: number    // 1–24 UTC, exclusive (24 = midnight)
}

export interface HealthStatus {
  status: 'ok' | 'degraded'
  scheduler_running: boolean
  last_run: string | null
  next_run: string | null
  uptime_seconds: number
  version: string
}

export interface TriggerResponse {
  status: 'started' | 'already_running'
}

export interface ResultsPage {
  results: SpeedResult[]
  total: number
  page: number
  page_size: number
}

export interface WebhookProviderConfig {
  enabled: boolean
  url: string
}

export interface GotifyProviderConfig {
  enabled: boolean
  url: string
  token: string
  priority: number
}

export interface NtfyProviderConfig {
  enabled: boolean
  url: string
  topic: string
  token: string
  priority: number
  tags: string[]
}

export interface AppriseProviderConfig {
  enabled: boolean
  url: string
  urls: string[]  // Service URLs for stateless mode (e.g., ['ntfy://...', 'gotify://...'])
}

export interface AlertProvidersConfig {
  webhook: WebhookProviderConfig
  gotify: GotifyProviderConfig
  ntfy: NtfyProviderConfig
  apprise: AppriseProviderConfig
}

export interface AlertConfig {
  enabled: boolean
  failure_threshold: number
  cooldown_minutes: number
  providers: AlertProvidersConfig
}

export interface TestAlertResponse {
  status: 'success' | 'failed' | 'partial' | 'no_providers'
  results: Record<string, boolean>
  message: string
}

// ---------------------------------------------------------------------------
// Analysis types
// ---------------------------------------------------------------------------

export interface AnomalyFlag {
  metric: string
  value: number
  baseline_mean: number
  baseline_stdev: number
  z_score: number
}

export interface AnnotatedResult {
  id: number
  timestamp: string
  download_mbps: number
  upload_mbps: number
  ping_ms: number
  jitter_ms: number | null
  isp_name: string | null
  server_name: string
  server_location: string
  is_anomaly: boolean
  anomaly_flags: AnomalyFlag[]
}

export interface HourlyStats {
  hour: number
  sample_count: number
  avg_download_mbps: number
  avg_upload_mbps: number
  avg_ping_ms: number
  min_download_mbps: number
  max_download_mbps: number
}

export interface MonthlyStats {
  month: string
  sample_count: number
  avg_download_mbps: number
  avg_upload_mbps: number
  avg_ping_ms: number
}

export interface TrendReport {
  monthly_stats: MonthlyStats[]
  download_slope: number | null
  upload_slope: number | null
  ping_slope: number | null
  degradation_detected: boolean
  months_available: number
}
