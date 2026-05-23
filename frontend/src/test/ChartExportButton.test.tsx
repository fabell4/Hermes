import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useRef } from 'react'
import { ChartExportButton } from '@/components/ChartExportButton'
import type { RefObject } from 'react'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Renders ChartExportButton with a ref pointing to a div that has a mock SVG. */
function renderWithSvg(overrides: Partial<{ filename: string; hasSvg: boolean }> = {}) {
  const { filename = 'test-chart', hasSvg = true } = overrides

  function Wrapper() {
    const ref = useRef<HTMLDivElement>(null)
    return (
      <div>
        <div ref={ref} data-testid="chart-container">
          {hasSvg && (
            <svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
              <rect width="400" height="300" fill="#1e293b" />
              <line x1="0" y1="150" x2="400" y2="150" stroke="#22d3ee" strokeWidth="2" />
            </svg>
          )}
        </div>
        <ChartExportButton containerRef={ref as RefObject<HTMLElement | null>} filename={filename} />
      </div>
    )
  }

  return render(<Wrapper />)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ChartExportButton', () => {
  let createObjectURLSpy: ReturnType<typeof vi.fn>
  let revokeObjectURLSpy: ReturnType<typeof vi.fn>
  let clickSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => 'blob:mock-url')
    revokeObjectURLSpy = vi.fn()
    clickSpy = vi.fn()

    Object.defineProperty(globalThis, 'URL', {
      value: {
        createObjectURL: createObjectURLSpy,
        revokeObjectURL: revokeObjectURLSpy,
      },
      writable: true,
    })

    // Intercept anchor.click() to avoid jsdom navigation errors
    const origCreate = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = origCreate(tag)
      if (tag === 'a') {
        Object.defineProperty(el, 'click', { value: clickSpy, writable: true })
      }
      return el
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the Export button', () => {
    renderWithSvg()
    expect(screen.getByRole('button', { name: /export chart/i })).toBeInTheDocument()
  })

  it('dropdown is closed by default', () => {
    renderWithSvg()
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('opens dropdown when Export button is clicked', () => {
    renderWithSvg()
    fireEvent.click(screen.getByRole('button', { name: /export chart/i }))
    expect(screen.getByRole('menu')).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'PNG' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'SVG' })).toBeInTheDocument()
  })

  it('closes dropdown when Export button is clicked again', () => {
    renderWithSvg()
    const btn = screen.getByRole('button', { name: /export chart/i })
    fireEvent.click(btn)
    fireEvent.click(btn)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('closes dropdown when clicking outside', () => {
    renderWithSvg()
    fireEvent.click(screen.getByRole('button', { name: /export chart/i }))
    fireEvent.mouseDown(document.body)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('clicking SVG option creates an object URL and triggers download', () => {
    renderWithSvg({ filename: 'my-chart' })
    fireEvent.click(screen.getByRole('button', { name: /export chart/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'SVG' }))
    expect(createObjectURLSpy).toHaveBeenCalledOnce()
    expect(clickSpy).toHaveBeenCalledOnce()
    expect(revokeObjectURLSpy).toHaveBeenCalledOnce()
    // Dropdown closes after selection
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('does nothing if container has no SVG element', () => {
    renderWithSvg({ hasSvg: false })
    fireEvent.click(screen.getByRole('button', { name: /export chart/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'PNG' }))
    expect(createObjectURLSpy).not.toHaveBeenCalled()
    expect(clickSpy).not.toHaveBeenCalled()
  })

  it('shows "Export" label text', () => {
    renderWithSvg()
    expect(screen.getByText('Export')).toBeInTheDocument()
  })

  it('uses custom filename for SVG export', () => {
    renderWithSvg({ filename: 'custom-name' })
    fireEvent.click(screen.getByRole('button', { name: /export chart/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'SVG' }))
    // The anchor's download attribute should be set to custom-name.svg
    expect(clickSpy).toHaveBeenCalledOnce()
  })
})
