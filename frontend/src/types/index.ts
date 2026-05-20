export interface HealthResponse {
  status: string
  app: string
  env: string
  database: 'ok' | 'error'
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

export type NotificationChannelType =
  | 'discord_webhook'
  | 'slack_webhook'
  | 'telegram_message'
  | 'smtp_email'
  | 'custom_webhook'
export type NotificationChannelStatus = 'active' | 'paused'

export interface NotificationChannelRead {
  id: string
  name: string
  type: NotificationChannelType
  status: NotificationChannelStatus
  config_masked: Record<string, unknown>
  created_at: string
  updated_at: string
  last_tested_at: string | null
}

export interface NotificationChannelPayload {
  name: string
  type: NotificationChannelType
  status?: NotificationChannelStatus
  config: Record<string, unknown>
}

export interface NotificationChannelUpdatePayload {
  name?: string
  type?: NotificationChannelType
  status?: NotificationChannelStatus
  config?: Record<string, unknown>
}

export interface NotificationDeliveryRead {
  id: string
  alert_id: string | null
  channel_id: string | null
  channel_name: string
  channel_type: NotificationChannelType
  status: string
  error_message: string | null
  sent_at: string | null
  created_at: string
}

export interface NotificationTestResult {
  channel: NotificationChannelRead
  delivery: NotificationDeliveryRead
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

// Jobs
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
export type ScheduleType = 'manual' | 'interval' | 'cron'
export type JobStatus = 'active' | 'paused'

export interface JobRead {
  id: string
  name: string
  description: string | null
  type: string
  status: JobStatus
  schedule_type: ScheduleType
  schedule_expression: string | null
  method: HttpMethod | null
  url: string | null
  headers_masked: Record<string, string> | null
  timeout_seconds: number
  retry_count: number
  retry_delay_seconds: number
  alert_on_failure: boolean
  created_at: string
  updated_at: string
  last_run_at: string | null
  next_run_at: string | null
}

export interface JobCreate {
  name: string
  description?: string
  type?: 'http'
  method: HttpMethod
  url: string
  headers?: Record<string, string>
  body?: string
  schedule_type: ScheduleType
  schedule_expression?: string
  timeout_seconds?: number
  retry_count?: number
  retry_delay_seconds?: number
  alert_on_failure?: boolean
}

export interface JobUpdate {
  name?: string
  description?: string
  method?: HttpMethod
  url?: string
  headers?: Record<string, string>
  body?: string
  schedule_type?: ScheduleType
  schedule_expression?: string
  timeout_seconds?: number
  retry_count?: number
  retry_delay_seconds?: number
  alert_on_failure?: boolean
  status?: JobStatus
}

// Executions
export interface ExecutionRead {
  id: string
  job_id: string
  trigger_type: string
  status: string
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  request_method: string | null
  request_url: string | null
  request_headers_masked: string | null
  request_body_masked: string | null
  response_status_code: number | null
  response_body_preview: string | null
  error_message: string | null
  retry_attempt: number
  created_at: string
}

// Notification templates
export interface NotificationTemplateRead {
  id: string
  name: string
  severity_filter: string | null
  title_template: string
  body_template: string
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface NotificationTemplatePayload {
  name: string
  severity_filter?: string | null
  title_template?: string
  body_template?: string
  is_default?: boolean
}

// Escalation policies
export interface EscalationStepRead {
  id: string
  policy_id: string
  step_order: number
  channel_id: string
  delay_minutes: number
}

export interface EscalationStepPayload {
  channel_id: string
  step_order: number
  delay_minutes: number
}

export interface EscalationPolicyRead {
  id: string
  name: string
  is_active: boolean
  steps: EscalationStepRead[]
  created_at: string
  updated_at: string
}

export interface EscalationPolicyPayload {
  name: string
  is_active?: boolean
  steps?: EscalationStepPayload[]
}

// Auth
export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export type UserRole = 'admin' | 'operator' | 'viewer'

export interface UserRead {
  id: string
  email: string
  name: string
  role: UserRole | string
  is_active: boolean
  created_at: string
  updated_at: string
  last_login_at: string | null
}

export interface UserCreatePayload {
  email: string
  name: string
  password: string
  role: UserRole
}

export interface UserUpdatePayload {
  name?: string
  role?: UserRole
  is_active?: boolean
}

// Audit logs
export interface AuditLogRead {
  id: string
  user_id: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  status: string
  ip_address: string | null
  user_agent: string | null
  metadata_: Record<string, unknown> | null
  created_at: string
}
