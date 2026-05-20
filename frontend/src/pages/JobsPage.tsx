import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { LiveIndicator } from '../components/ui/LiveIndicator'
import { useDeleteJob, useJobs, useRunJob } from '../hooks/useJobs'
import { useWebSocket } from '../hooks/useWebSocket'
import type { JobRead } from '../types'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: 'bg-green-100 text-green-700',
    paused: 'bg-yellow-100 text-yellow-700',
  }
  const cls = styles[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

function JobRow({ job }: { job: JobRead }) {
  const runJob = useRunJob()
  const deleteJob = useDeleteJob()
  const [confirmDelete, setConfirmDelete] = useState(false)

  function handleDelete() {
    if (confirmDelete) {
      deleteJob.mutate(job.id)
    } else {
      setConfirmDelete(true)
    }
  }

  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pl-4 pr-4">
        <Link to={`/jobs/${job.id}`} className="text-sm font-medium text-blue-600 hover:underline">
          {job.name}
        </Link>
        {job.description && (
          <p className="mt-0.5 text-xs text-gray-400 truncate max-w-xs">{job.description}</p>
        )}
      </td>
      <td className="py-3 pr-4">
        <StatusPill status={job.status} />
      </td>
      <td className="py-3 pr-4 text-xs text-gray-600">
        <span className="font-mono">{job.method}</span>
        {job.url && (
          <span className="ml-1 text-gray-400 truncate block max-w-[200px]">{job.url}</span>
        )}
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">
        {job.schedule_type === 'manual'
          ? 'Manual'
          : job.schedule_type === 'interval'
          ? `Every ${job.schedule_expression}s`
          : job.schedule_expression}
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(job.last_run_at)}</td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(job.next_run_at)}</td>
      <td className="py-3 pr-4 text-right space-x-1">
        <button
          onClick={() => runJob.mutate(job.id)}
          disabled={runJob.isPending}
          className="rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 disabled:opacity-50"
        >
          Run
        </button>
        <Link
          to={`/jobs/${job.id}/edit`}
          className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-100"
        >
          Edit
        </Link>
        <button
          onClick={handleDelete}
          disabled={deleteJob.isPending}
          className={`rounded px-2 py-1 text-xs disabled:opacity-50 ${
            confirmDelete
              ? 'bg-red-100 text-red-700 hover:bg-red-200'
              : 'text-red-500 hover:bg-red-50'
          }`}
        >
          {confirmDelete ? 'Confirm?' : 'Delete'}
        </button>
      </td>
    </tr>
  )
}

export function JobsPage() {
  const queryClient = useQueryClient()
  const { lastEvent, status: wsStatus } = useWebSocket()

  useEffect(() => {
    if (lastEvent?.type === 'execution.completed') {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
    }
  }, [lastEvent, queryClient])

  const { data: jobs, isLoading, isError } = useJobs()

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
          <p className="mt-1 text-sm text-gray-500">
            Scheduled HTTP jobs and manual triggers.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <LiveIndicator status={wsStatus} />
          <Link
            to="/jobs/new"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            New Job
          </Link>
        </div>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading jobs…</p>}

      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not load jobs. Make sure the API is running.
        </div>
      )}

      {!isLoading && !isError && jobs && jobs.length === 0 && (
        <div className="rounded-lg border border-dashed border-gray-300 p-10 text-center">
          <p className="text-sm text-gray-500">No jobs yet.</p>
          <Link to="/jobs/new" className="mt-2 inline-block text-sm text-blue-600 hover:underline">
            Create your first job →
          </Link>
        </div>
      )}

      {!isLoading && !isError && jobs && jobs.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pl-4 pr-4">Name</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Endpoint</th>
                <th className="py-3 pr-4">Schedule</th>
                <th className="py-3 pr-4">Last Run</th>
                <th className="py-3 pr-4">Next Run</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <JobRow key={job.id} job={job} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
