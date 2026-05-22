import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { HermesProvider } from '@/context/HermesContext'
import { Layout } from '@/components/Layout'
import { Analysis } from '@/pages/Analysis'
import { Dashboard } from '@/pages/Dashboard'
import { Settings } from '@/pages/Settings'
import { Styleguide } from '@/pages/Styleguide'

export default function App() {
  return (
    <BrowserRouter>
      <HermesProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/styleguide" element={<Styleguide />} />
          </Routes>
        </Layout>
      </HermesProvider>
    </BrowserRouter>
  )
}
