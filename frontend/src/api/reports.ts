import { apiFetch } from './client'
import type {
  ReportFormat,
  ReportGenerateRequest,
  ReportRead,
  ReportSummaryRead,
} from '../types'

const baseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export function getReports(): Promise<ReportSummaryRead[]> {
  return apiFetch<ReportSummaryRead[]>('/api/reports')
}

export function generateReport(payload: ReportGenerateRequest): Promise<ReportRead> {
  return apiFetch<ReportRead>('/api/reports/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function downloadReport(
  reportId: string,
  format: ReportFormat
): Promise<void> {
  const response = await fetch(
    `${baseUrl}/api/reports/${reportId}/download?format=${format}`
  )
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`)
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const extension = format === 'markdown' ? 'md' : format
  const link = document.createElement('a')
  link.href = url
  link.download = `autoflowops-report-${reportId}.${extension}`
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
