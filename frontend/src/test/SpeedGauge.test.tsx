import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { SpeedGauge } from '@/components/SpeedGauge'
import type { SpeedResult } from '@/types'

const MOCK_RESULT: SpeedResult = {
  id: 1,
  timestamp: '2026-04-22T12:00:00Z',
  download_mbps: 250.5,
  upload_mbps: 45.2,
  ping_ms: 12.3,
  jitter_ms: 1.4,
  isp_name: 'Test ISP',
  server_name: 'Test Server',
  server_location: 'Test City',
  server_id: 42,
}

describe('SpeedGauge', () => {
  it('renders all four metric cards', () => {
    render(<SpeedGauge isTesting={false} latest={null} />)
    expect(screen.getByText('Download')).toBeInTheDocument()
    expect(screen.getByText('Upload')).toBeInTheDocument()
    expect(screen.getByText('Ping')).toBeInTheDocument()
    expect(screen.getByText('Jitter')).toBeInTheDocument()
  })

  it('shows latest result values when not testing', () => {
    render(<SpeedGauge isTesting={false} latest={MOCK_RESULT} />)
    expect(screen.getByText('250.5')).toBeInTheDocument()
    expect(screen.getByText('45.2')).toBeInTheDocument()
    expect(screen.getByText('12.3')).toBeInTheDocument()
  })

  it('shows zeros when no result is available', () => {
    render(<SpeedGauge isTesting={false} latest={null} />)
    const zeros = screen.getAllByText('0.0')
    expect(zeros.length).toBeGreaterThanOrEqual(3)
  })

  it('renders unit labels', () => {
    render(<SpeedGauge isTesting={false} latest={MOCK_RESULT} />)
    const mbpsLabels = screen.getAllByText('Mbps')
    const msLabels = screen.getAllByText('ms')
    expect(mbpsLabels).toHaveLength(2)
    expect(msLabels).toHaveLength(2)
  })
})
