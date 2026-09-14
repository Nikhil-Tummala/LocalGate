import { Check, Plug, Wifi, WifiOff } from 'lucide-react'
import { useState } from 'react'
import { patchConfig } from '../api'

interface Props {
  connected: boolean
  target: string | null | undefined
}

export default function ConnectionBar({ connected, target }: Props) {
  const [draft, setDraft] = useState<string | null>(null) // null = not editing
  const [error, setError] = useState<string | null>(null)

  const save = () => {
    if (draft === null) return
    patchConfig({ target_url: draft })
      .then(() => {
        setDraft(null)
        setError(null)
      })
      .catch(() => setError('Must start with http:// or https://'))
  }

  return (
    <header className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <Plug className="h-5 w-5 text-sky-400" /> LocalGate
        </div>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <form
            className="flex items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              save()
            }}
          >
            <label htmlFor="target" className="text-slate-400">Target</label>
            <input
              id="target"
              value={draft ?? target ?? ''}
              placeholder="http://localhost:3000"
              onChange={(e) => setDraft(e.target.value)}
              className="w-64 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-slate-200 focus:border-sky-500 focus:outline-none"
            />
            {draft !== null && (
              <button type="submit" aria-label="Save target" className="rounded-md bg-sky-500/20 p-1.5 text-sky-400 hover:bg-sky-500/30">
                <Check className="h-4 w-4" />
              </button>
            )}
          </form>
          <span
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 font-medium ${
              connected ? 'bg-emerald-500/15 text-emerald-400' : 'bg-amber-500/15 text-amber-400'
            }`}
          >
            {connected ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4 animate-pulse" />}
            {connected ? 'Connected' : 'Reconnecting'}
          </span>
        </div>
      </div>
      {error && <p className="mt-2 text-right text-sm text-rose-400">{error}</p>}
    </header>
  )
}
