import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { HermesProvider } from '@/context/HermesContext'
import { ThemeProvider } from '@/context/ThemeContext'
import { Layout } from '@/components/Layout'
import { Analysis } from '@/pages/Analysis'
import { Dashboard } from '@/pages/Dashboard'
import { Alerts } from '@/pages/Alerts'
import { Reports } from '@/pages/Reports'
import { Settings } from '@/pages/Settings'
import { Styleguide } from '@/pages/Styleguide'

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <HermesProvider>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/styleguide" element={<Styleguide />} />
            </Routes>
          </Layout>
        </HermesProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
