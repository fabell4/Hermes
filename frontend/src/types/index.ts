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
}

export interface RuntimeConfig {
  interval_minutes: number
  enabled_exporters: string[]
  scanning_enabled: boolean
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
