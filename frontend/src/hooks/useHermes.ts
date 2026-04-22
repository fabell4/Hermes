import { useContext } from 'react'
import {
  HermesContext,
  type HermesContextType,
} from '@/context/hermesContextDef'

export function useHermes(): HermesContextType {
  const ctx = useContext(HermesContext)
  if (!ctx) throw new Error('useHermes must be used within HermesProvider')
  return ctx
}
