export interface HealthResponse {
  status: string
  app: string
  env: string
}

export interface VersionResponse {
  version: string
  app: string
}

export interface DailyStats {
  date: string
  success: number
  failure: number
}

export interface StatsResponse {
  total_jobs: number
  active_jobs: number
  paused_jobs: number
  total_executions: number
  executions_24h: number
  failures_24h: number
  success_rate_24h: number
  daily_stats: DailyStats[]
}

export interface WebhookRead {
  id: string
  name: string
  slug: string
  status: string
  created_at: string
  updated_at: string
  last_received_at: string | null
}

export interface AlertRead {
  id: string
  title: string
  message: string
  severity: string
  source_type: string | null
  source_id: string | null
  status: string
  created_at: string
  acknowledged_at: string | null
  resolved_at: string | null
}

export interface WebhookEventRead {
  id: string
  webhook_id: string
  headers_masked: string | null
  payload: string | null
  source_ip: string | null
  received_at: string
  status: string
  processed_at: string | null
  error_message: string | null
}

export type ReportFormat = 'json' | 'markdown' | 'csv'

export interface ReportGenerateRequest {
  name?: string
  period_start: string
  period_end: string
}

export interface ReportSummaryRead {
  id: string
  name: string
  format: string
  period_start: string
  period_end: string
  created_at: string
  created_by: string | null
}

export interface ReportRead extends ReportSummaryRead {
  content: string | null
}
