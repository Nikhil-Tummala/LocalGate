export interface SeriesPoint {
  t: number
  hits: number
  upstream: number
}

export interface Telemetry {
  total_requests: number
  cache_hits: number
  cache_misses: number
  rate_limited: number
  cache_hit_ratio: number
  rps: number
  p50_ms: number
  p95_ms: number
  tokens: number
  bucket_capacity: number
  cache_size: number
  target_url: string | null
  series: SeriesPoint[]
}

export interface ChaosConfig {
  latency_enabled: boolean
  min_delay_ms: number
  max_delay_ms: number
  error_injection_enabled: boolean
  failure_rate_percentage: number // 0.0 - 1.0
  error_status_codes: number[]
}

export interface AppConfig {
  target_url: string | null
  rate_limit: { capacity: number; refill_rate: number }
  cache: { max_entries: number; ttl_seconds: number; max_body_bytes: number }
  chaos: ChaosConfig
}
