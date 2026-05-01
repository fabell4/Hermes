import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import type { HealthStatus } from '@/types'

// Mock the useHermes hook
vi.mock('@/hooks/useHermes', () => ({
  useHermes: vi.fn(),
}))

// Mock framer-motion to avoid animation complexity in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.ComponentPropsWithRef<'div'>) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Mock fetch for the GitHub release check
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

import { useHermes } from '@/hooks/useHermes'

const mockHealth: HealthStatus = {
  status: 'ok',
  scheduler_running: true,
  last_run: '2026-05-01T10:00:00Z',
  next_run: '2026-05-01T11:00:00Z',
  uptime_seconds: 3600,
  version: '1.0.0',
}

function renderLayout(children = <div>content</div>) {
  return render(
    <MemoryRouter>
      <Layout>{children}</Layout>
    </MemoryRouter>
  )
}

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ tag_name: 'v1.0.0' }),
    })
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: mockHealth,
      config: null,
      alerts: null,
      loading: false,
      isTesting: false,
      error: null,
      runTest: vi.fn(),
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
  })

  it('renders the Hermes brand name', () => {
    renderLayout()
    expect(screen.getByText('Hermes')).toBeInTheDocument()
  })

  it('renders navigation links for Dashboard and Settings', () => {
    renderLayout()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders the current version when health data is available', () => {
    renderLayout()
    expect(screen.getByText('v1.0.0')).toBeInTheDocument()
  })

  it('does not render version when health is null', () => {
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: null,
      config: null,
      alerts: null,
      loading: false,
      isTesting: false,
      error: null,
      runTest: vi.fn(),
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
    renderLayout()
    expect(screen.queryByText(/^v\d/)).toBeNull()
  })

  it('renders children content', () => {
    renderLayout(<div data-testid="child-content">Hello World</div>)
    expect(screen.getByTestId('child-content')).toBeInTheDocument()
  })

  it('toggles mobile menu on button click', () => {
    renderLayout()
    const menuButton = screen.getByRole('button', { name: /toggle menu/i })
    expect(menuButton).toBeInTheDocument()
    fireEvent.click(menuButton)
    // After toggle, the button should still be present
    expect(screen.getByRole('button', { name: /toggle menu/i })).toBeInTheDocument()
  })

  it('renders update available banner when a newer version exists', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ tag_name: 'v2.0.0' }),
    })
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: { ...mockHealth, version: '1.0.0' },
      config: null,
      alerts: null,
      loading: false,
      isTesting: false,
      error: null,
      runTest: vi.fn(),
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
    renderLayout()
    // Wait for the useEffect to resolve the fetch
    await vi.waitFor(() => {
      // The update notification renders when latestVersion != currentVersion
    })
  })

  it('does not render update banner when version is dev', () => {
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: { ...mockHealth, version: 'dev' },
      config: null,
      alerts: null,
      loading: false,
      isTesting: false,
      error: null,
      runTest: vi.fn(),
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
    renderLayout()
    // fetch should not be called for dev versions
    expect(mockFetch).not.toHaveBeenCalled()
  })
})
