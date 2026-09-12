import { Activity, Database, Gauge, Timer } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Telemetry } from '../types'

function Card({ icon, label, value, sub }: { icon: ReactNode; label: string; value: string; sub: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center gap-2 text-sm text-slate-400">
        {icon} {label}
      </div>
      <div className="mt-2 text-3xl font-semibold tabular-nums">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{sub}</div>
    </div>
  )
}

export default function MetricsGrid({ data }: { data: Telemetry | null }) {
  const d = data
  const icon = 'h-4 w-4'
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card
        icon={<Activity className={icon} />}
        label="Total RPS"
        value={d ? String(d.rps) : '–'}
        sub={d ? `${d.total_requests.toLocaleString()} requests total` : 'waiting for data'}
      />
      <Card
        icon={<Database className={icon} />}
        label="Cache hit ratio"
        value={d ? `${d.cache_hit_ratio.toFixed(1)}%` : '–'}
        sub={d ? `${d.cache_hits} hits / ${d.cache_misses} misses · ${d.cache_size} cached` : 'waiting for data'}
      />
      <Card
        icon={<Gauge className={icon} />}
        label="Active bucket tokens"
        value={d ? d.tokens.toFixed(1) : '–'}
        sub={d ? `of ${d.bucket_capacity} · ${d.rate_limited} blocked (429) · ${d.chaos_injected} chaos` : 'waiting for data'}
      />
      <Card
        icon={<Timer className={icon} />}
        label="p95 latency"
        value={d ? `${d.p95_ms.toFixed(0)} ms` : '–'}
        sub={d ? `p50 ${d.p50_ms.toFixed(0)} ms` : 'waiting for data'}
      />
    </section>
  )
}
