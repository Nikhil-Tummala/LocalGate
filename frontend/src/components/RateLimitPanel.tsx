import { Gauge } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getConfig, patchConfig } from '../api'

/** Capacity and refill rate, applied together. Applying resets every bucket to full (server side). */
export default function RateLimitPanel() {
  const [capacity, setCapacity] = useState('')
  const [refill, setRefill] = useState('')
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    getConfig()
      .then((c) => {
        setCapacity(String(c.rate_limit.capacity))
        setRefill(String(c.rate_limit.refill_rate))
      })
      .catch(() => setNote({ ok: false, text: 'Could not load rate limits' }))
  }, [])

  const apply = () => {
    const cap = Number(capacity)
    const rate = Number(refill)
    if (!Number.isInteger(cap) || cap < 1 || !(rate > 0)) {
      setNote({ ok: false, text: 'Capacity must be a whole number ≥ 1 and refill rate > 0' })
      return
    }
    patchConfig({ rate_limit: { capacity: cap, refill_rate: rate } })
      .then(() => setNote({ ok: true, text: 'Applied. Buckets reset to full.' }))
      .catch(() => setNote({ ok: false, text: 'Backend rejected the update' }))
  }

  const input = 'w-24 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-slate-200 focus:border-sky-500 focus:outline-none'
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <h2 className="mb-4 flex items-center gap-2 text-sm font-medium text-slate-400">
        <Gauge className="h-4 w-4" /> Rate limit (per path)
      </h2>
      <div className="flex flex-wrap items-end gap-4 text-sm text-slate-400">
        <label className="flex flex-col gap-1">
          Capacity (tokens)
          <input inputMode="numeric" value={capacity} onChange={(e) => setCapacity(e.target.value)} className={input} />
        </label>
        <label className="flex flex-col gap-1">
          Refill (tokens/s)
          <input inputMode="decimal" value={refill} onChange={(e) => setRefill(e.target.value)} className={input} />
        </label>
        <button onClick={apply} className="rounded-lg bg-sky-500/20 px-3 py-1.5 font-medium text-sky-400 hover:bg-sky-500/30">
          Apply
        </button>
      </div>
      {note && <p className={`mt-3 text-sm ${note.ok ? 'text-emerald-400' : 'text-rose-400'}`}>{note.text}</p>}
    </section>
  )
}
