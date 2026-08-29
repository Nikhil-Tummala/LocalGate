import { Flame, Timer, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { clearCache, getConfig, patchConfig } from '../api'
import type { AppConfig } from '../types'

function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${on ? 'bg-sky-500' : 'bg-slate-700'}`}
    >
      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${on ? 'left-5.5' : 'left-0.5'}`} />
    </button>
  )
}

export default function ChaosPanel() {
  const [cfg, setCfg] = useState<AppConfig | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [flushed, setFlushed] = useState<number | null>(null)
  const debounce = useRef<number | undefined>(undefined)

  useEffect(() => {
    getConfig().then(setCfg).catch((e: Error) => setError(e.message))
  }, [])

  if (!cfg) {
    return <section className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-400">{error ?? 'Loading controls…'}</section>
  }
  const chaos = cfg.chaos

  // Update the UI immediately; send to the backend after the slider settles.
  const setChaos = (patch: Partial<AppConfig['chaos']>) => {
    setCfg({ ...cfg, chaos: { ...chaos, ...patch } })
    window.clearTimeout(debounce.current)
    debounce.current = window.setTimeout(() => {
      patchConfig({ chaos: patch })
        .then((fresh) => {
          setCfg(fresh)
          setError(null)
        })
        .catch((e: Error) => setError(e.message))
    }, 150)
  }

  // Keep min <= max, otherwise the backend rejects the update.
  const setMin = (v: number) => setChaos({ min_delay_ms: v, max_delay_ms: Math.max(v, chaos.max_delay_ms) })
  const setMax = (v: number) => setChaos({ max_delay_ms: v, min_delay_ms: Math.min(v, chaos.min_delay_ms) })

  const flush = () =>
    clearCache()
      .then((r) => setFlushed(r.cleared))
      .catch((e: Error) => setError(e.message))

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <h2 className="mb-4 flex items-center gap-2 text-sm font-medium text-slate-400">
        <Flame className="h-4 w-4" /> Chaos controls
      </h2>

      <div className="space-y-6">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium">Error injection</span>
            <Toggle on={chaos.error_injection_enabled} onChange={(v) => setChaos({ error_injection_enabled: v })} label="Error injection" />
          </div>
          <label className="flex items-center gap-3 text-sm text-slate-400">
            Failure probability
            <input
              type="range" min={0} max={100} step={1}
              value={Math.round(chaos.failure_rate_percentage * 100)}
              onChange={(e) => setChaos({ failure_rate_percentage: Number(e.target.value) / 100 })}
              className="flex-1 accent-sky-500"
            />
            <span className="w-12 text-right font-mono text-slate-200">{Math.round(chaos.failure_rate_percentage * 100)}%</span>
          </label>
          <div className="mt-1 text-xs text-slate-500">Returns {chaos.error_status_codes.join(' / ')} without calling upstream</div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-sm font-medium"><Timer className="h-4 w-4" /> Latency injection</span>
            <Toggle on={chaos.latency_enabled} onChange={(v) => setChaos({ latency_enabled: v })} label="Latency injection" />
          </div>
          {([['Min delay', chaos.min_delay_ms, setMin], ['Max delay', chaos.max_delay_ms, setMax]] as const).map(([label, value, set]) => (
            <label key={label} className="mb-1 flex items-center gap-3 text-sm text-slate-400">
              <span className="w-20">{label}</span>
              <input type="range" min={0} max={5000} step={50} value={value} onChange={(e) => set(Number(e.target.value))} className="flex-1 accent-sky-500" />
              <span className="w-16 text-right font-mono text-slate-200">{value} ms</span>
            </label>
          ))}
        </div>

        <div className="flex items-center justify-between border-t border-slate-800 pt-4">
          <span className="text-sm text-slate-400">{flushed === null ? 'Cache' : `Flushed ${flushed} entries`}</span>
          <button onClick={flush} className="flex items-center gap-2 rounded-lg bg-rose-500/15 px-3 py-1.5 text-sm font-medium text-rose-400 hover:bg-rose-500/25">
            <Trash2 className="h-4 w-4" /> Flush cache
          </button>
        </div>
        {error && <p className="text-sm text-rose-400">{error}</p>}
      </div>
    </section>
  )
}
