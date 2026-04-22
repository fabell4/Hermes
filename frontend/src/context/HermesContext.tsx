import {
  useState,
  useCallback,
  useEffect,
  useMemo,
  ReactNode,
} from 'react'
import { api } from '@/lib/api'
import { useSpeedData } from '@/hooks/useSpeedData'
import { HermesContext } from '@/context/hermesContextDef'
import type { RuntimeConfig } from '@/types'

interface HermesProviderProps {
  readonly children: ReactNode
}

export function HermesProvider({ children }: HermesProviderProps) {
  const { results, latest, health, loading, error, refresh } = useSpeedData()
  const [config, setConfig] = useState<RuntimeConfig | null>(null)
  const [isTesting, setIsTesting] = useState(false)

  // Load config once on mount
  useEffect(() => {
    api.getConfig().then(setConfig).catch(() => null)
  }, [])

  const runTest = useCallback(async () => {
    if (isTesting) return
    setIsTesting(true)
    try {
      await api.triggerTest()
      // Poll until a new result appears (up to 30 s)
      let attempts = 0
      const latestTs = latest?.timestamp ?? null
      const poll = setInterval(async () => {
        attempts++
        const newLatest = await api.getLatestResult()
        const hasNewResult = newLatest != null && newLatest.timestamp !== latestTs
        if (hasNewResult || attempts >= 30) {
          clearInterval(poll)
          setIsTesting(false)
          refresh()
        }
      }, 1000)
    } catch {
      setIsTesting(false)
    }
  }, [isTesting, latest, refresh])

  const updateConfig = useCallback(
    async (patch: Partial<RuntimeConfig>) => {
      const updated = await api.updateConfig(patch)
      setConfig(updated)
    },
    []
  )

  const contextValue = useMemo(
    () => ({
      results,
      latest,
      health,
      config,
      loading,
      isTesting,
      error,
      runTest,
      updateConfig,
      refresh,
    }),
    [results, latest, health, config, loading, isTesting, error, runTest, updateConfig, refresh]
  )

  return (
    <HermesContext.Provider value={contextValue}>
      {children}
    </HermesContext.Provider>
  )
}
