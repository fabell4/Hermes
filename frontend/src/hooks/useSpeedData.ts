import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import type { SpeedResult, HealthStatus } from '@/types'

const POLL_INTERVAL_MS = 10_000

export function useSpeedData() {
  const [results, setResults] = useState<SpeedResult[]>([])
  const [latest, setLatest] = useState<SpeedResult | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    try {
      const [page, latestResult, healthStatus] = await Promise.all([
        api.getResults(1, 100),
        api.getLatestResult(),
        api.getHealth(),
      ])
      setResults(page.results)
      setLatest(latestResult)
      setHealth(healthStatus)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load + polling
  useEffect(() => {
    fetchAll()
    const id = setInterval(fetchAll, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [fetchAll])

  return { results, latest, health, loading, error, refresh: fetchAll }
}
