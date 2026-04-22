import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '@/lib/api'

describe('api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('getResults calls the correct URL', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: [], total: 0, page: 1, page_size: 50 }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await api.getResults(1, 50)
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/results?page=1&page_size=50',
      expect.objectContaining({ headers: { 'Content-Type': 'application/json' } })
    )
  })

  it('getHealth calls /api/health', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          status: 'ok',
          scheduler_running: true,
          last_run: null,
          next_run: null,
          uptime_seconds: 42,
          version: '0.3.0',
        }),
    })
    vi.stubGlobal('fetch', mockFetch)

    const result = await api.getHealth()
    expect(mockFetch).toHaveBeenCalledWith('/api/health', expect.any(Object))
    expect(result.version).toBe('0.3.0')
  })

  it('triggerTest uses POST', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'started' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await api.triggerTest()
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/trigger',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('throws on non-OK response', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      text: () => Promise.resolve('Service unavailable'),
    })
    vi.stubGlobal('fetch', mockFetch)

    await expect(api.getHealth()).rejects.toThrow('API error 503')
  })
})
