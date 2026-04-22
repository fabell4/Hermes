import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { HermesProvider } from '@/context/HermesContext'
import { Layout } from '@/components/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Settings } from '@/pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <HermesProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Layout>
      </HermesProvider>
    </BrowserRouter>
  )
}
