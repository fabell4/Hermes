/**
 * Typed API client for the Hermes FastAPI backend.
 * All paths are relative — Vite proxies /api to localhost:8080 in dev.
 */

import type {
  SpeedResult,
  RuntimeConfig,
  HealthStatus,
  TriggerResponse,
  ResultsPage,
  AlertConfig,
  TestAlertResponse,
} from '@/types'

const BASE = '/api'

/** Read the API key stored by the Settings page. Returns empty object if not set. */
function apiKeyHeader(): Record<string, string> {
  const key = localStorage.getItem('hermes_api_key')
  return key ? { 'X-Api-Key': key } : {}
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...apiKeyHeader(),
      ...(options?.headers as Record<string, string> | undefined),
    },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export interface ResultsFilter {
  page?: number
  pageSize?: number
  dateFrom?: string
  dateTo?: string
  minDownload?: number
  maxDownload?: number
  minUpload?: number
  maxUpload?: number
  maxPing?: number
  server?: string
  isp?: string
}

export const api = {
  /** Paginated history — newest first. */
  getResults(page = 1, pageSize = 50): Promise<ResultsPage> {
    return request(`/results?page=${page}&page_size=${pageSize}`)
  },

  /** Paginated history with optional filters. */
  getResultsFiltered(filter: ResultsFilter = {}): Promise<ResultsPage> {
    const params = new URLSearchParams()
    params.set('page', String(filter.page ?? 1))
    params.set('page_size', String(filter.pageSize ?? 50))
    if (filter.dateFrom) params.set('date_from', filter.dateFrom)
    if (filter.dateTo) params.set('date_to', filter.dateTo)
    if (filter.minDownload !== undefined) params.set('min_download', String(filter.minDownload))
    if (filter.maxDownload !== undefined) params.set('max_download', String(filter.maxDownload))
    if (filter.minUpload !== undefined) params.set('min_upload', String(filter.minUpload))
    if (filter.maxUpload !== undefined) params.set('max_upload', String(filter.maxUpload))
    if (filter.maxPing !== undefined) params.set('max_ping', String(filter.maxPing))
    if (filter.server) params.set('server', filter.server)
    if (filter.isp) params.set('isp', filter.isp)
    return request(`/results?${params}`)
  },

  /** Fetch all distinct server names for filter dropdowns. */
  getServers(): Promise<string[]> {
    return api.getResultsFiltered({ pageSize: 500 }).then((p) =>
      [...new Set(p.results.map((r) => r.server_name))].sort((a, b) => a.localeCompare(b))
    )
  },

  /** Fetch all distinct ISP names for filter dropdowns. */
  getIsps(): Promise<string[]> {
    return api.getResultsFiltered({ pageSize: 500 }).then((p) =>
      [...new Set(p.results.map((r) => r.isp_name ?? '').filter(Boolean))].sort((a, b) =>
        a.localeCompare(b)
      )
    )
  },

  /** Single most-recent result, or null if none yet. */
  getLatestResult(): Promise<SpeedResult | null> {
    return request('/results/latest')
  },

  /** Manually trigger a speed test. */
  triggerTest(): Promise<TriggerResponse> {
    return request('/trigger', { method: 'POST' })
  },

  /** Check if a test is currently running. */
  getTestStatus(): Promise<{ is_running: boolean }> {
    return request('/trigger/status')
  },

  /** Read current runtime config. */
  getConfig(): Promise<RuntimeConfig> {
    return request('/config')
  },

  /** Persist updated runtime config. */
  updateConfig(config: Partial<RuntimeConfig>): Promise<RuntimeConfig> {
    return request('/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  },

  /** Health / scheduler status. */
  getHealth(): Promise<HealthStatus> {
    return request('/health')
  },

  /** Read current alert configuration. */
  getAlerts(): Promise<AlertConfig> {
    return request('/alerts')
  },

  /** Persist updated alert configuration. */
  updateAlerts(config: AlertConfig): Promise<AlertConfig> {
    return request('/alerts', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  },

  /** Send test alerts to all configured providers. */
  testAlerts(): Promise<TestAlertResponse> {
    return request('/alerts/test', { method: 'POST' })
  },

  /** Set or clear the annotation note on a specific result. */
  updateNote(id: number, note: string | null): Promise<SpeedResult> {
    return request(`/results/${id}/note`, {
      method: 'PUT',
      body: JSON.stringify({ note }),
    })
  },
}
