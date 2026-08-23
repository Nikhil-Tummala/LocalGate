import { Plug, Wifi, WifiOff } from 'lucide-react'

interface Props {
  connected: boolean
  target: string | null | undefined
}

export default function ConnectionBar({ connected, target }: Props) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
      <div className="flex items-center gap-2 text-lg font-semibold">
        <Plug className="h-5 w-5 text-sky-400" /> LocalGate
      </div>
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <span className="text-slate-400">
          Target:{' '}
          <span className="font-mono text-slate-200">{target ?? 'not set (use X-Target-URL)'}</span>
        </span>
        <span
          className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 font-medium ${
            connected ? 'bg-emerald-500/15 text-emerald-400' : 'bg-amber-500/15 text-amber-400'
          }`}
        >
          {connected ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4 animate-pulse" />}
          {connected ? 'Connected' : 'Reconnecting'}
        </span>
      </div>
    </header>
  )
}
