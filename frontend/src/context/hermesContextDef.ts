/**
 * Context definition only — no React components exported here.
 * Splitting this out satisfies react-refresh/only-export-components.
 */
import { createContext } from 'react'
import type { SpeedResult, RuntimeConfig, HealthStatus, AlertConfig } from '@/types'

export interface HermesContextType {
  results: SpeedResult[]
  latest: SpeedResult | null
  health: HealthStatus | null
  config: RuntimeConfig | null
  alerts: AlertConfig | null
  loading: boolean
  isTesting: boolean
  error: string | null
  runTest: () => Promise<void>
  updateConfig: (patch: Partial<RuntimeConfig>) => Promise<void>
  updateAlerts: (config: AlertConfig) => Promise<void>
  refresh: () => void
}

export const HermesContext = createContext<HermesContextType | undefined>(undefined)
