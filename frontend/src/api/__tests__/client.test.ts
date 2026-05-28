import { describe, it, expect, vi } from 'vitest'

// vi.hoisted ensures this runs before vi.mock factories, which are hoisted above all imports
const captured = vi.hoisted(() => ({
  success: null as ((res: any) => any) | null,
  error: null as ((err: any) => Promise<never>) | null,
}))

vi.mock('axios', () => {
  const instance = {
    interceptors: {
      request: { use: vi.fn() },
      response: {
        use: vi.fn((s: any, e: any) => {
          captured.success = s
          captured.error = e
        }),
      },
    },
  }
  return { default: { create: () => instance } }
})

vi.mock('../../store/authStore', () => ({
  useAuthStore: { getState: () => ({ token: null, logout: vi.fn() }) },
}))

import '../client'

describe('axios client response interceptor', () => {
  it('unwraps {success, data, meta} envelope to data', () => {
    const raw = { success: true, data: { score: 42 }, meta: { cached: false } }
    const res = captured.success!({ data: raw })
    expect(res.data).toEqual({ score: 42 })
  })

  it('passes through a response without success key untouched', () => {
    const raw = { id: 1, username: 'alice' }
    const res = captured.success!({ data: raw })
    expect(res.data).toEqual({ id: 1, username: 'alice' })
  })

  it('passes through null body untouched', () => {
    const res = captured.success!({ data: null })
    expect(res.data).toBeNull()
  })

  it('passes through a non-object body untouched', () => {
    const res = captured.success!({ data: 'ok' })
    expect(res.data).toBe('ok')
  })

  it('rejects non-401 errors as-is', async () => {
    const err = { response: { status: 500 } }
    await expect(captured.error!(err)).rejects.toEqual(err)
  })
})
