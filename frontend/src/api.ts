import type { AppConfig } from './types'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const getConfig = () => call<AppConfig>('/api/config')

/** Partial update: only the fields given are changed server-side. */
export const patchConfig = (patch: Record<string, unknown>) =>
  call<AppConfig>('/api/config', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(patch),
  })

export const clearCache = () => call<{ cleared: number }>('/api/cache/clear', { method: 'POST' })
