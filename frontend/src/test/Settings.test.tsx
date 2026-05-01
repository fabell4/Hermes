import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { Settings } from '@/pages/Settings'
import type { RuntimeConfig, AlertConfig } from '@/types'

// Mock the useHermes hook
vi.mock('@/hooks/useHermes', () => ({
  useHermes: vi.fn(),
}))

// Mock the API module
vi.mock('@/lib/api', () => ({
  api: {
    testAlerts: vi.fn(),
  },
}))

// Simplify framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.ComponentPropsWithRef<'div'>) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

import { useHermes } from '@/hooks/useHermes'
import { api } from '@/lib/api'

const MOCK_CONFIG: RuntimeConfig = {
  interval_minutes: 60,
  enabled_exporters: ['csv'],
  scanning_enabled: true,
}

const MOCK_ALERTS: AlertConfig = {
  enabled: true,
  failure_threshold: 3,
  cooldown_minutes: 60,
  providers: {
    webhook: { enabled: false, url: '' },
    gotify: { enabled: false, url: '', token: '', priority: 5 },
    ntfy: { enabled: false, url: '', topic: '', token: '', priority: 3, tags: [] },
    apprise: { enabled: false, url: '', urls: [] },
  },
}

function renderSettings() {
  return render(
    <MemoryRouter>
      <Settings />
    </MemoryRouter>
  )
}

function getExporterToggle(labelText: string | RegExp) {
  const label = screen.getByText(labelText)
  // The toggle button is in the same container as the label
  const container = label.closest('div.flex')
  if (!container) throw new Error(`No container found for: ${labelText}`)
  return container.querySelector('button[aria-pressed]') as HTMLElement
}

function getTestAlertButton() {
  // Text may be broken across icon + text span elements; find by partial button text
  const buttons = screen.getAllByRole('button')
  const btn = buttons.find(b => b.textContent?.includes('Send Test Notification'))
  if (!btn) throw new Error('Could not find Send Test Notification button')
  return btn
}

describe('Settings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: null,
      config: MOCK_CONFIG,
      alerts: MOCK_ALERTS,
      loading: false,
      isTesting: false,
      error: null,
      runTest: vi.fn(),
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
  })

  it('renders the Settings heading', () => {
    renderSettings()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders the Save Changes button', () => {
    renderSettings()
    expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument()
  })

  it('renders CSV exporter as enabled by default', () => {
    renderSettings()
    const csvButton = getExporterToggle('CSV Export')
    expect(csvButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('renders SQLite exporter as disabled by default', () => {
    renderSettings()
    const sqliteButton = getExporterToggle('SQLite')
    expect(sqliteButton).toHaveAttribute('aria-pressed', 'false')
  })

  it('shows loading state when config is null', () => {
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: null,
      config: null,
      alerts: null,
      loading: true,
      isTesting: false,
      error: null,
      runTest: vi.fn(),
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
    renderSettings()
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('calls updateConfig with modified config when Save Changes is clicked', async () => {
    const mockUpdateConfig = vi.fn().mockResolvedValue(undefined)
    const mockUpdateAlerts = vi.fn().mockResolvedValue(undefined)
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: null,
      config: MOCK_CONFIG,
      alerts: MOCK_ALERTS,
      loading: false,
      isTesting: false,
      error: null,
      runTest: vi.fn(),
      updateConfig: mockUpdateConfig,
      updateAlerts: mockUpdateAlerts,
      refresh: vi.fn(),
    })
    renderSettings()

    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(mockUpdateConfig).toHaveBeenCalledOnce()
      expect(mockUpdateAlerts).toHaveBeenCalledOnce()
    })
  })

  it('shows Saved status after successful save', async () => {
    const mockUpdateConfig = vi.fn().mockResolvedValue(undefined)
    const mockUpdateAlerts = vi.fn().mockResolvedValue(undefined)
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: null,
      config: MOCK_CONFIG,
      alerts: MOCK_ALERTS,
      loading: false,
      isTesting: false,
      error: null,
      runTest: vi.fn(),
      updateConfig: mockUpdateConfig,
      updateAlerts: mockUpdateAlerts,
      refresh: vi.fn(),
    })
    renderSettings()

    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /saved/i })).toBeInTheDocument()
    })
  })

  it('renders the Send Test Notification button', () => {
    renderSettings()
    expect(getTestAlertButton()).toBeInTheDocument()
  })

  it('cycles test button to sending state when clicked', async () => {
    vi.mocked(api.testAlerts).mockResolvedValue({
      status: 'success',
      results: {},
      message: 'All alerts sent successfully',
    })
    renderSettings()

    fireEvent.click(getTestAlertButton())

    await waitFor(() => {
      const buttons = screen.getAllByRole('button')
      const testBtn = buttons.find(b => b.textContent?.includes('Test Sent Successfully'))
      expect(testBtn).toBeTruthy()
    })

    expect(vi.mocked(api.testAlerts)).toHaveBeenCalledOnce()
  })

  it('shows error state when test alert fails', async () => {
    vi.mocked(api.testAlerts).mockRejectedValue(new Error('Network error'))
    renderSettings()

    fireEvent.click(getTestAlertButton())

    await waitFor(() => {
      expect(screen.getByText(/Test Failed/i)).toBeInTheDocument()
    })
  })

  it('toggles exporter when button is clicked', () => {
    renderSettings()

    // SQLite starts as disabled; clicking should toggle it
    const sqliteButton = getExporterToggle('SQLite')
    expect(sqliteButton).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(sqliteButton)
    expect(sqliteButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('renders Prometheus and Loki exporters', () => {
    renderSettings()
    expect(screen.getByText('Prometheus')).toBeInTheDocument()
    expect(screen.getByText('Loki')).toBeInTheDocument()
  })
})
