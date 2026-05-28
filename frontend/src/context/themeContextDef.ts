/**
 * Theme context definition — no React components exported here.
 * Splitting this out satisfies react-refresh/only-export-components.
 */
import { createContext } from 'react'

export type Theme = 'dark' | 'light'

export interface ThemeContextType {
  theme: Theme
  toggleTheme: () => void
}

// Default value keeps dark mode active when used outside a provider (e.g. in tests).
export const ThemeContext = createContext<ThemeContextType>({
  theme: 'dark',
  toggleTheme: () => undefined,
})
