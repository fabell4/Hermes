import { useState, useCallback } from 'react'

const STORAGE_KEY = 'hermes_dashboard'

export type MetricId = 'Download' | 'Upload' | 'Ping' | 'Jitter'
export type SectionId = 'chart' | 'resultLog'

export interface DashboardConfig {
  metricOrder: MetricId[]
  hiddenMetrics: MetricId[]
  hiddenSections: SectionId[]
}

export const ALL_METRICS: MetricId[] = ['Download', 'Upload', 'Ping', 'Jitter']

export const DEFAULT_DASHBOARD_CONFIG: DashboardConfig = {
  metricOrder: [...ALL_METRICS],
  hiddenMetrics: [],
  hiddenSections: [],
}

function isMetricId(v: unknown): v is MetricId {
  return ALL_METRICS.includes(v as MetricId)
}

function isSectionId(v: unknown): v is SectionId {
  return v === 'chart' || v === 'resultLog'
}

function loadConfig(): DashboardConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_DASHBOARD_CONFIG
    const parsed = JSON.parse(raw) as Partial<DashboardConfig>

    const storedOrder = Array.isArray(parsed.metricOrder)
      ? (parsed.metricOrder as unknown[]).filter(isMetricId)
      : null

    // Ensure every metric appears in the order; append any missing ones at end
    const fullOrder: MetricId[] = storedOrder
      ? [...storedOrder, ...ALL_METRICS.filter((m) => !storedOrder.includes(m))]
      : [...ALL_METRICS]

    return {
      metricOrder: fullOrder,
      hiddenMetrics: Array.isArray(parsed.hiddenMetrics)
        ? (parsed.hiddenMetrics as unknown[]).filter(isMetricId)
        : [],
      hiddenSections: Array.isArray(parsed.hiddenSections)
        ? (parsed.hiddenSections as unknown[]).filter(isSectionId)
        : [],
    }
  } catch {
    return DEFAULT_DASHBOARD_CONFIG
  }
}

function persist(config: DashboardConfig): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
}

export function useDashboardConfig() {
  const [config, setConfig] = useState<DashboardConfig>(loadConfig)

  const setMetricOrder = useCallback((order: MetricId[]) => {
    setConfig((prev) => {
      const next = { ...prev, metricOrder: order }
      persist(next)
      return next
    })
  }, [])

  const toggleMetric = useCallback((id: MetricId) => {
    setConfig((prev) => {
      const next = {
        ...prev,
        hiddenMetrics: prev.hiddenMetrics.includes(id)
          ? prev.hiddenMetrics.filter((m) => m !== id)
          : [...prev.hiddenMetrics, id],
      }
      persist(next)
      return next
    })
  }, [])

  const toggleSection = useCallback((id: SectionId) => {
    setConfig((prev) => {
      const next = {
        ...prev,
        hiddenSections: prev.hiddenSections.includes(id)
          ? prev.hiddenSections.filter((s) => s !== id)
          : [...prev.hiddenSections, id],
      }
      persist(next)
      return next
    })
  }, [])

  const reset = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setConfig(DEFAULT_DASHBOARD_CONFIG)
  }, [])

  return { config, setMetricOrder, toggleMetric, toggleSection, reset }
}
