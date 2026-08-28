import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SeriesPoint } from '../types'

export default function ThroughputChart({ series }: { series: SeriesPoint[] }) {
  // x axis shows seconds ago, so the chart reads left (60s ago) to right (now)
  const last = series.length ? series[series.length - 1].t : 0
  const points = series.map((p) => ({ ago: p.t - last, hits: p.hits, upstream: p.upstream }))
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <h2 className="mb-3 text-sm font-medium text-slate-400">Throughput, last 60 s (requests/s)</h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid stroke="#1e293b" vertical={false} />
            <XAxis dataKey="ago" tickFormatter={(v: number) => (v === 0 ? 'now' : `${v}s`)} stroke="#64748b" fontSize={12} interval={9} />
            <YAxis allowDecimals={false} stroke="#64748b" fontSize={12} />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
              labelFormatter={(v) => (Number(v) === 0 ? 'now' : `${v}s ago`)}
            />
            <Area type="monotone" dataKey="hits" name="Cache hits" stackId="1" stroke="#34d399" fill="#34d399" fillOpacity={0.35} isAnimationActive={false} />
            <Area type="monotone" dataKey="upstream" name="Upstream fetches" stackId="1" stroke="#38bdf8" fill="#38bdf8" fillOpacity={0.35} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-emerald-400" /> Cache hits</span>
        <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-sky-400" /> Upstream fetches</span>
      </div>
    </section>
  )
}
