import { Link, useNavigate, useParams } from 'react-router-dom'
import { useDeleteJob, useJob, useRunJob, useUpdateJob } from '../hooks/useJobs'
import { useExecutions } from '../hooks/useExecutions'
import type { ExecutionRead } from '../types'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: 'bg-green-100 text-green-700',
    paused: 'bg-yellow-100 text-yellow-700',
    success: 'bg-green-100 text-green-700',
    failure: 'bg-red-100 text-red-700',
    running: 'bg-blue-100 text-blue-700',
  }
  const cls = styles[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

function ExecutionRow({ exc }: { exc: ExecutionRead }) {
  return (
    <tr className="border-t border-gray-100">
      <td className="py-2 pl-4 pr-4 text-xs text-gray-500">{formatDate(exc.started_at)}</td>
      <td className="py-2 pr-4">
        <StatusPill status={exc.status} />
      </td>
      <td className="py-2 pr-4 text-xs text-gray-500">
        {exc.duration_ms !== null ? `${exc.duration_ms} ms` : '—'}
      </td>
      <td className="py-2 pr-4 text-xs text-gray-500">{exc.response_status_code ?? '—'}</td>
      <td className="py-2 pr-4 text-xs text-red-600 max-w-xs truncate">{exc.error_message ?? '—'}</td>
      <td className="py-2 pr-4">
        <Link to={`/executions/${exc.id}`} className="text-xs text-blue-600 hover:underline">
          Details
        </Link>
      </td>
    </tr>
  )
}

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: job, isLoading, isError } = useJob(id!)
  const { data: executions } = useExecutions({ job_id: id!, limit: 10 })
  const runJob = useRunJob()
  const updateJob = useUpdateJob(id!)
  const deleteJob = useDeleteJob()

  if (isLoading) return <p className="text-sm text-gray-500">Loading job…</p>
  if (isError || !job) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Job not found.
      </div>
    )
  }

  const isPaused = job.status === 'paused'

  async function handleTogglePause() {
    await updateJob.mutateAsync({ status: isPaused ? 'active' : 'paused' })
  }

  async function handleDelete() {
    if (!confirm(`Delete job "${job!.name}"? This cannot be undone.`)) return
    await deleteJob.mutateAsync(job!.id)
    navigate('/jobs')
  }

  return (
    <div className="max-w-3xl">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <nav className="mb-1 text-xs text-gray-400">
            <Link to="/jobs" className="hover:underline">Jobs</Link>
            <span className="mx-1">/</span>
            <span>{job.name}</span>
          </nav>
          <h1 className="text-2xl font-bold text-gray-900">{job.name}</h1>
          {job.description && <p className="mt-1 text-sm text-gray-500">{job.description}</p>}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => runJob.mutate(job.id)}
            disabled={runJob.isPending}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {runJob.isPending ? 'Running…' : 'Run now'}
          </button>
          <button
            onClick={handleTogglePause}
            disabled={updateJob.isPending}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {isPaused ? 'Activate' : 'Pause'}
          </button>
          <Link
            to={`/jobs/${job.id}/edit`}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Edit
          </Link>
          <button
            onClick={handleDelete}
            disabled={deleteJob.isPending}
            className="rounded-md border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Info cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: 'Status', value: <span className="inline-flex"><StatusPill status={job.status} /></span> },
          { label: 'Method', value: <code className="text-xs font-mono">{job.method}</code> },
          { label: 'Schedule', value: job.schedule_type },
          { label: 'Timeout', value: `${job.timeout_seconds}s` },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-gray-500">{label}</p>
            <div className="mt-1 text-sm font-medium text-gray-900">{value}</div>
          </div>
        ))}
      </div>

      {/* URL */}
      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <p className="text-xs font-medium text-gray-500">URL</p>
        <p className="mt-1 break-all font-mono text-sm text-gray-800">{job.url}</p>
      </div>

      {/* Timing */}
      <div className="mb-6 grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Last run</p>
          <p className="mt-1 text-sm text-gray-900">{formatDate(job.last_run_at)}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Next run</p>
          <p className="mt-1 text-sm text-gray-900">{formatDate(job.next_run_at)}</p>
        </div>
      </div>

      {/* Recent executions */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent Executions</h2>
          <Link to={`/executions?job_id=${job.id}`} className="text-xs text-blue-600 hover:underline">
            View all
          </Link>
        </div>
        {!executions || executions.length === 0 ? (
          <p className="text-sm text-gray-500">No executions yet.</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  <th className="py-2 pl-4 pr-4">Started</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Duration</th>
                  <th className="py-2 pr-4">HTTP</th>
                  <th className="py-2 pr-4">Error</th>
                  <th className="py-2 pr-4"></th>
                </tr>
              </thead>
              <tbody>
                {executions.map((exc) => <ExecutionRow key={exc.id} exc={exc} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
