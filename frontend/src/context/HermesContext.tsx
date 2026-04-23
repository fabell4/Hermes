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

  // Poll test status every 2 seconds to detect scheduler-triggered tests
  // Also refresh results when test completes
  useEffect(() => {
    let wasRunning = false
    const interval = setInterval(async () => {
      try {
        const { is_running } = await api.getTestStatus()
        setIsTesting(is_running)
        
        // If test just completed, refresh data
        if (wasRunning && !is_running) {
          refresh()
        }
        wasRunning = is_running
      } catch {
        // Ignore errors
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [refresh])

  const runTest = useCallback(async () => {
    if (isTesting) return
    try {
      const response = await api.triggerTest()
      if (response.status === 'started') {
        setIsTesting(true)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to trigger test'
      console.error('Failed to trigger test:', message)
      
      // Show authentication errors to the user
      if (message.includes('401') || message.includes('403')) {
        alert('Authentication required. Please set your API key in Settings.')
      }
    }
  }, [isTesting])

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
