import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ResultsTable } from '@/components/ResultsTable'
import type { SpeedResult } from '@/types'

vi.mock('@/lib/api', () => ({
  api: { updateNote: vi.fn() },
}))

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.ComponentPropsWithRef<'div'>) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

const makeResult = (overrides: Partial<SpeedResult> & { id: number }): SpeedResult => ({
  timestamp: '2026-05-01T12:00:00Z',
  download_mbps: 100,
  upload_mbps: 50,
  ping_ms: 10,
  jitter_ms: 1,
  isp_name: 'Test ISP',
  server_name: 'Server A',
  server_location: 'City A',
  server_id: 1,
  note: null,
  ...overrides,
})

const DATA: SpeedResult[] = [
  makeResult({ id: 1, timestamp: '2026-05-01T10:00:00Z', download_mbps: 200, server_name: 'Server A' }),
  makeResult({ id: 2, timestamp: '2026-05-10T10:00:00Z', download_mbps: 80, server_name: 'Server B' }),
  makeResult({ id: 3, timestamp: '2026-05-20T10:00:00Z', download_mbps: 50, server_name: 'Server A' }),
]

function renderTable(data = DATA) {
  return render(<ResultsTable data={data} />)
}

function openTable() {
  fireEvent.click(screen.getByText('Result Log'))
}

function openFilters() {
  fireEvent.click(screen.getByRole('button', { name: /toggle filters/i }))
}

describe('ResultsTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the result log header', () => {
    renderTable()
    expect(screen.getByText('Result Log')).toBeInTheDocument()
  })

  it('shows entry count in header', () => {
    renderTable()
    expect(screen.getByText('3 entries')).toBeInTheDocument()
  })

  it('table rows hidden by default (collapsed)', () => {
    renderTable()
    expect(screen.queryByText('Server A')).not.toBeInTheDocument()
  })

  it('reveals rows after clicking header', () => {
    renderTable()
    openTable()
    expect(screen.getAllByText('Server A')).toHaveLength(2)
    expect(screen.getByText('Server B')).toBeInTheDocument()
  })

  it('renders filters button', () => {
    renderTable()
    expect(screen.getByRole('button', { name: /toggle filters/i })).toBeInTheDocument()
  })

  it('shows filter bar when filters button is clicked', () => {
    renderTable()
    openFilters()
    expect(screen.getByLabelText('From')).toBeInTheDocument()
    expect(screen.getByLabelText('To')).toBeInTheDocument()
    expect(screen.getByLabelText('Min Download (Mbps)')).toBeInTheDocument()
    expect(screen.getByLabelText('Server')).toBeInTheDocument()
  })

  it('populates server dropdown from unique servers', () => {
    renderTable()
    openFilters()
    const select = screen.getByLabelText('Server') as HTMLSelectElement
    const options = Array.from(select.options).map((o) => o.value)
    expect(options).toContain('Server A')
    expect(options).toContain('Server B')
    // No duplicates
    expect(options.filter((v) => v === 'Server A')).toHaveLength(1)
  })

  it('filters by server', () => {
    renderTable()
    openTable()
    openFilters()
    fireEvent.change(screen.getByLabelText('Server'), { target: { value: 'Server B' } })
    // Only 1 data row should be visible (1 header + 1 data = 2 rows total)
    expect(screen.getAllByRole('row')).toHaveLength(2)
    // Server A cells should not be present in the table body
    expect(screen.queryAllByRole('cell', { name: /Server A/ })).toHaveLength(0)
  })

  it('shows "1 of 3 entries" badge when server filter is active', () => {
    renderTable()
    openFilters()
    fireEvent.change(screen.getByLabelText('Server'), { target: { value: 'Server B' } })
    expect(screen.getByText('1 of 3 entries')).toBeInTheDocument()
  })

  it('filters by min download', () => {
    renderTable()
    openTable()
    openFilters()
    fireEvent.change(screen.getByLabelText('Min Download (Mbps)'), { target: { value: '100' } })
    // Only result with download_mbps=200 should show
    const rows = screen.getAllByRole('row')
    // 1 header row + 1 data row
    expect(rows).toHaveLength(2)
  })

  it('shows empty-state row when no results match filters', () => {
    renderTable()
    openTable()
    openFilters()
    fireEvent.change(screen.getByLabelText('Min Download (Mbps)'), { target: { value: '999' } })
    expect(screen.getByText('No results match the current filters.')).toBeInTheDocument()
  })

  it('filters by date from', () => {
    renderTable()
    openTable()
    openFilters()
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-05-10' } })
    // Results on 2026-05-10 and 2026-05-20 should show (ids 2 and 3)
    expect(screen.getByText('2 of 3 entries')).toBeInTheDocument()
  })

  it('filters by date to', () => {
    renderTable()
    openTable()
    openFilters()
    fireEvent.change(screen.getByLabelText('To'), { target: { value: '2026-05-01' } })
    // Only result on 2026-05-01 (id 1) should show
    expect(screen.getByText('1 of 3 entries')).toBeInTheDocument()
  })

  it('shows filter count badge on Filters button when filters are active', () => {
    renderTable()
    openFilters()
    fireEvent.change(screen.getByLabelText('Server'), { target: { value: 'Server A' } })
    fireEvent.change(screen.getByLabelText('Min Download (Mbps)'), { target: { value: '100' } })
    // The badge showing count=2 should appear inside the filters button
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('clears all filters when "Clear filters" is clicked', () => {
    renderTable()
    openFilters()
    fireEvent.change(screen.getByLabelText('Server'), { target: { value: 'Server B' } })
    expect(screen.getByText('1 of 3 entries')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Clear filters'))
    expect(screen.getByText('3 entries')).toBeInTheDocument()
  })
})
