import { useContext } from 'react'
import { ThemeContext } from '@/context/themeContextDef'
import type { ThemeContextType } from '@/context/themeContextDef'

export function useTheme(): ThemeContextType {
  return useContext(ThemeContext)
}
