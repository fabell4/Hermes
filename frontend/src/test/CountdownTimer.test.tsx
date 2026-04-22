import { render, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { CountdownTimer } from '@/components/CountdownTimer'

describe('CountdownTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders nothing when nextRun is null', () => {
    const { container } = render(<CountdownTimer nextRun={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('displays a formatted MM:SS countdown', () => {
    const nextRun = new Date(Date.now() + 5 * 60_000 + 30_000).toISOString() // 5m30s
    render(<CountdownTimer nextRun={nextRun} />)
    // The time is rendered as three adjacent text nodes: "05", ":", "30"
    const span = document.querySelector('span.font-mono')
    expect(span?.textContent).toBe('05:30')
  })

  it('shows 00:00 when nextRun is in the past', () => {
    const nextRun = new Date(Date.now() - 10_000).toISOString()
    render(<CountdownTimer nextRun={nextRun} />)
    const span = document.querySelector('span.font-mono')
    expect(span?.textContent).toBe('00:00')
  })

  it('updates every second', () => {
    const nextRun = new Date(Date.now() + 2 * 60_000).toISOString() // 2m00s
    render(<CountdownTimer nextRun={nextRun} />)
    const span = document.querySelector('span.font-mono')
    expect(span?.textContent).toBe('02:00')
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(span?.textContent).toBe('01:59')
  })
})
