import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { Dashboard } from '@/pages/Dashboard'
import type { SpeedResult, HealthStatus } from '@/types'

// Mock the useHermes hook
vi.mock('@/hooks/useHermes', () => ({
  useHermes: vi.fn(),
}))

// Simplify framer-motion animations
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.ComponentPropsWithRef<'div'>) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Mock child components that have complex rendering
vi.mock('@/components/SpeedChart', () => ({
  SpeedChart: () => <div data-testid="speed-chart" />,
}))

vi.mock('@/components/ResultsTable', () => ({
  ResultsTable: () => <div data-testid="results-table" />,
}))

vi.mock('@/components/CountdownTimer', () => ({
  CountdownTimer: ({ nextRun }: { nextRun: string | null }) => (
    <div data-testid="countdown-timer">{nextRun ?? 'no-timer'}</div>
  ),
}))

vi.mock('@/components/SpeedGauge', () => ({
  SpeedGauge: () => <div data-testid="speed-gauge" />,
}))

import { useHermes } from '@/hooks/useHermes'

const MOCK_RESULT: SpeedResult = {
  id: 1,
  timestamp: '2026-05-01T12:00:00Z',
  download_mbps: 250.5,
  upload_mbps: 45.2,
  ping_ms: 12.3,
  jitter_ms: 1.4,
  isp_name: 'Test ISP',
  server_name: 'Test Server',
  server_location: 'Test City',
  server_id: 42,
}

const MOCK_HEALTH: HealthStatus = {
  status: 'ok',
  scheduler_running: true,
  last_run: '2026-05-01T11:00:00Z',
  next_run: '2026-05-01T12:00:00Z',
  uptime_seconds: 3600,
  version: '1.0.0',
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>
  )
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: MOCK_HEALTH,
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

  it('renders the Dashboard heading', () => {
    renderDashboard()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('renders the Run Test button when idle', () => {
    renderDashboard()
    expect(screen.getByRole('button', { name: /run test/i })).toBeInTheDocument()
  })

  it('renders the SpeedGauge component', () => {
    renderDashboard()
    expect(screen.getByTestId('speed-gauge')).toBeInTheDocument()
  })

  it('renders the CountdownTimer component', () => {
    renderDashboard()
    expect(screen.getByTestId('countdown-timer')).toBeInTheDocument()
  })

  it('does not render chart or table when no results', () => {
    renderDashboard()
    expect(screen.queryByTestId('speed-chart')).toBeNull()
    expect(screen.queryByTestId('results-table')).toBeNull()
  })

  it('renders chart and table when results are available', () => {
    vi.mocked(useHermes).mockReturnValue({
      results: [MOCK_RESULT],
      latest: MOCK_RESULT,
      health: MOCK_HEALTH,
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
    renderDashboard()
    expect(screen.getByTestId('speed-chart')).toBeInTheDocument()
    expect(screen.getByTestId('results-table')).toBeInTheDocument()
  })

  it('shows test running indicator when isTesting is true', () => {
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: MOCK_HEALTH,
      config: null,
      alerts: null,
      loading: false,
      isTesting: true,
      error: null,
      runTest: vi.fn(),
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
    renderDashboard()
    expect(screen.getByText('Test Running')).toBeInTheDocument()
    expect(screen.getByText(/Testing/i)).toBeInTheDocument()
  })

  it('disables Run Test button while testing', () => {
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: MOCK_HEALTH,
      config: null,
      alerts: null,
      loading: false,
      isTesting: true,
      error: null,
      runTest: vi.fn(),
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
    renderDashboard()
    const button = screen.getByRole('button', { name: /testing/i })
    expect(button).toBeDisabled()
  })

  it('calls runTest when Run Test button is clicked', () => {
    const mockRunTest = vi.fn()
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: MOCK_HEALTH,
      config: null,
      alerts: null,
      loading: false,
      isTesting: false,
      error: null,
      runTest: mockRunTest,
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
    renderDashboard()
    fireEvent.click(screen.getByRole('button', { name: /run test/i }))
    expect(mockRunTest).toHaveBeenCalledOnce()
  })

  it('renders error banner when error is present', () => {
    vi.mocked(useHermes).mockReturnValue({
      results: [],
      latest: null,
      health: null,
      config: null,
      alerts: null,
      loading: false,
      isTesting: false,
      error: 'Connection failed',
      runTest: vi.fn(),
      updateConfig: vi.fn(),
      updateAlerts: vi.fn(),
      refresh: vi.fn(),
    })
    renderDashboard()
    expect(screen.getByText('Connection failed')).toBeInTheDocument()
  })

  it('shows connecting message when health status is null', () => {
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
    renderDashboard()
    expect(screen.getByText(/Connecting to Hermes/i)).toBeInTheDocument()
  })

  it('shows scheduler running status with last run time', () => {
    renderDashboard()
    expect(screen.getByText(/Scheduler running/i)).toBeInTheDocument()
  })
})
