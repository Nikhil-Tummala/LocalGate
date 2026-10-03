import ChaosPanel from './components/ChaosPanel'
import ConnectionBar from './components/ConnectionBar'
import RateLimitPanel from './components/RateLimitPanel'
import MetricsGrid from './components/MetricsGrid'
import ThroughputChart from './components/ThroughputChart'
import { useTelemetry } from './hooks/useTelemetry'

export default function App() {
  const { data, connected } = useTelemetry()
  return (
    <main className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <ConnectionBar connected={connected} target={data?.target_url} />
      <MetricsGrid data={data} />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ThroughputChart series={data?.series ?? []} />
        </div>
        <div className="space-y-4">
          <ChaosPanel />
          <RateLimitPanel />
        </div>
      </div>
    </main>
  )
}
