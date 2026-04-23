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

export const api = {
  /** Paginated history — newest first. */
  getResults(page = 1, pageSize = 50): Promise<ResultsPage> {
    return request(`/results?page=${page}&page_size=${pageSize}`)
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
}
