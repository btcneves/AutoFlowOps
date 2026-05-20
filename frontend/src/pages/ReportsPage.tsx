import { FormEvent, useMemo, useState } from 'react'
import { downloadReport } from '../api/reports'
import { useGenerateReport, useReports } from '../hooks/useReports'
import type { ReportFormat, ReportSummaryRead } from '../types'

function toDateTimeLocalValue(date: Date): string {
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

function toIso(value: string): string {
  return new Date(value).toISOString()
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function formatPeriod(report: ReportSummaryRead): string {
  return `${formatDate(report.period_start)} → ${formatDate(report.period_end)}`
}

function DownloadButtons({ report }: { report: ReportSummaryRead }) {
  const formats: { label: string; value: ReportFormat }[] = [
    { label: 'JSON', value: 'json' },
    { label: 'Markdown', value: 'markdown' },
    { label: 'CSV', value: 'csv' },
  ]

  return (
    <div className="flex justify-end gap-1">
      {formats.map((format) => (
        <button
          key={format.value}
          onClick={() => void downloadReport(report.id, format.value)}
          className="rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50"
        >
          {format.label}
        </button>
      ))}
    </div>
  )
}

export function ReportsPage() {
  const defaults = useMemo(() => {
    const end = new Date()
    const start = new Date(end)
    start.setDate(start.getDate() - 7)
    return {
      start: toDateTimeLocalValue(start),
      end: toDateTimeLocalValue(end),
    }
  }, [])

  const [name, setName] = useState('')
  const [periodStart, setPeriodStart] = useState(defaults.start)
  const [periodEnd, setPeriodEnd] = useState(defaults.end)
  const { data: reports, isLoading, isError } = useReports()
  const generate = useGenerateReport()

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    generate.mutate({
      name: name.trim() || undefined,
      period_start: toIso(periodStart),
      period_end: toIso(periodEnd),
    })
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="mt-1 text-sm text-gray-500">
          Generate operational reports for executions, failures and alerts.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="mb-6 grid gap-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm md:grid-cols-[1fr_190px_190px_auto]"
      >
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          Name
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Operational report"
            className="rounded-md border border-gray-200 px-3 py-2 text-sm font-normal text-gray-900 outline-none focus:border-blue-400"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          Start
          <input
            type="datetime-local"
            required
            value={periodStart}
            onChange={(event) => setPeriodStart(event.target.value)}
            className="rounded-md border border-gray-200 px-3 py-2 text-sm font-normal text-gray-900 outline-none focus:border-blue-400"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          End
          <input
            type="datetime-local"
            required
            value={periodEnd}
            onChange={(event) => setPeriodEnd(event.target.value)}
            className="rounded-md border border-gray-200 px-3 py-2 text-sm font-normal text-gray-900 outline-none focus:border-blue-400"
          />
        </label>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={generate.isPending}
            className="w-full rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {generate.isPending ? 'Generating…' : 'Generate Report'}
          </button>
        </div>
      </form>

      {generate.isError && (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not generate report for the selected period.
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-500">Loading reports…</p>}

      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not load reports. Make sure the API is running.
        </div>
      )}

      {!isLoading && !isError && reports && reports.length === 0 && (
        <p className="text-sm text-gray-500">No reports generated yet.</p>
      )}

      {!isLoading && !isError && reports && reports.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">Name</th>
                <th className="py-3 pr-4">Period</th>
                <th className="py-3 pr-4">Created</th>
                <th className="py-3 pr-4">Format</th>
                <th className="py-3 pr-4 text-right">Downloads</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reports.map((report) => (
                <tr key={report.id} className="border-t border-gray-100">
                  <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">
                    {report.name}
                  </td>
                  <td className="py-3 pr-4 text-xs text-gray-500">
                    {formatPeriod(report)}
                  </td>
                  <td className="py-3 pr-4 text-xs text-gray-500">
                    {formatDate(report.created_at)}
                  </td>
                  <td className="py-3 pr-4">
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                      {report.format}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-right">
                    <DownloadButtons report={report} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
