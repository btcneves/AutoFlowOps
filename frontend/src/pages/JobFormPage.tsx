import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useJob, useCreateJob, useUpdateJob } from '../hooks/useJobs'
import type { HttpMethod, JobCreate, JobUpdate, ScheduleType } from '../types'

const HTTP_METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

interface FormState {
  name: string
  description: string
  method: HttpMethod
  url: string
  body: string
  schedule_type: ScheduleType
  schedule_expression: string
  timeout_seconds: string
  retry_count: string
  retry_delay_seconds: string
  alert_on_failure: boolean
}

const EMPTY: FormState = {
  name: '',
  description: '',
  method: 'GET',
  url: '',
  body: '',
  schedule_type: 'manual',
  schedule_expression: '',
  timeout_seconds: '30',
  retry_count: '0',
  retry_delay_seconds: '60',
  alert_on_failure: true,
}

export function JobFormPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const isEdit = id !== undefined
  const navigate = useNavigate()

  const scheduleTypes: { value: ScheduleType; label: string }[] = [
    { value: 'manual', label: t('jobForm.scheduleManual') },
    { value: 'interval', label: t('jobForm.scheduleInterval') },
    { value: 'cron', label: t('jobForm.scheduleCron') },
  ]

  const { data: existing, isLoading: loadingJob } = useJob(id ?? '')
  const createJob = useCreateJob()
  const updateJob = useUpdateJob(id ?? '')

  const [form, setForm] = useState<FormState>(EMPTY)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (existing) {
      setForm({
        name: existing.name,
        description: existing.description ?? '',
        method: existing.method ?? 'GET',
        url: existing.url ?? '',
        body: '',
        schedule_type: existing.schedule_type,
        schedule_expression: existing.schedule_expression ?? '',
        timeout_seconds: String(existing.timeout_seconds),
        retry_count: String(existing.retry_count),
        retry_delay_seconds: String(existing.retry_delay_seconds),
        alert_on_failure: existing.alert_on_failure,
      })
    }
  }, [existing])

  function set(key: keyof FormState, value: string | boolean) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!form.name.trim()) { setError(t('jobForm.errorName')); return }
    if (!form.url.trim()) { setError(t('jobForm.errorUrl')); return }
    if (form.schedule_type !== 'manual' && !form.schedule_expression.trim()) {
      setError(t('jobForm.errorSchedule')); return
    }

    try {
      if (isEdit) {
        const payload: JobUpdate = {
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          method: form.method,
          url: form.url.trim(),
          body: form.body.trim() || undefined,
          schedule_type: form.schedule_type,
          schedule_expression: form.schedule_expression.trim() || undefined,
          timeout_seconds: Number(form.timeout_seconds),
          retry_count: Number(form.retry_count),
          retry_delay_seconds: Number(form.retry_delay_seconds),
          alert_on_failure: form.alert_on_failure,
        }
        await updateJob.mutateAsync(payload)
        navigate(`/jobs/${id}`)
      } else {
        const payload: JobCreate = {
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          method: form.method,
          url: form.url.trim(),
          body: form.body.trim() || undefined,
          schedule_type: form.schedule_type,
          schedule_expression: form.schedule_expression.trim() || undefined,
          timeout_seconds: Number(form.timeout_seconds),
          retry_count: Number(form.retry_count),
          retry_delay_seconds: Number(form.retry_delay_seconds),
          alert_on_failure: form.alert_on_failure,
        }
        const job = await createJob.mutateAsync(payload)
        navigate(`/jobs/${job.id}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  if (isEdit && loadingJob) {
    return <p className="text-sm text-gray-500">{t('jobDetail.loading')}</p>
  }

  const isPending = createJob.isPending || updateJob.isPending

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        {isEdit ? t('jobForm.titleEdit') : t('jobForm.titleNew')}
      </h1>

      <form onSubmit={handleSubmit} className="space-y-5 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700">{t('jobForm.labelName')}</label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder={t('jobForm.placeholderName')}
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700">{t('jobForm.labelDescription')}</label>
          <input
            type="text"
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Method + URL */}
        <div className="flex gap-3">
          <div className="w-32 shrink-0">
            <label className="block text-sm font-medium text-gray-700">{t('jobForm.labelMethod')}</label>
            <select
              value={form.method}
              onChange={(e) => set('method', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {HTTP_METHODS.map((m) => <option key={m}>{m}</option>)}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700">{t('jobForm.labelUrl')}</label>
            <input
              type="url"
              required
              value={form.url}
              onChange={(e) => set('url', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder={t('jobForm.placeholderUrl')}
            />
          </div>
        </div>

        {/* Body */}
        {['POST', 'PUT', 'PATCH'].includes(form.method) && (
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('jobForm.labelBody')}</label>
            <textarea
              value={form.body}
              onChange={(e) => set('body', e.target.value)}
              rows={4}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-xs shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder={t('jobForm.placeholderBody')}
            />
          </div>
        )}

        {/* Schedule */}
        <div className="flex gap-3">
          <div className="w-48 shrink-0">
            <label className="block text-sm font-medium text-gray-700">{t('jobForm.labelSchedule')}</label>
            <select
              value={form.schedule_type}
              onChange={(e) => set('schedule_type', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {scheduleTypes.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
          {form.schedule_type !== 'manual' && (
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700">
                {form.schedule_type === 'interval' ? t('jobForm.labelInterval') : t('jobForm.labelCron')}
              </label>
              <input
                type="text"
                value={form.schedule_expression}
                onChange={(e) => set('schedule_expression', e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder={form.schedule_type === 'interval' ? t('jobForm.placeholderInterval') : t('jobForm.placeholderCron')}
              />
            </div>
          )}
        </div>

        {/* Timeout + Retry */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('jobForm.labelTimeout')}</label>
            <input
              type="number"
              min={1}
              max={300}
              value={form.timeout_seconds}
              onChange={(e) => set('timeout_seconds', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('jobForm.labelRetries')}</label>
            <input
              type="number"
              min={0}
              max={10}
              value={form.retry_count}
              onChange={(e) => set('retry_count', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('jobForm.labelRetryDelay')}</label>
            <input
              type="number"
              min={1}
              value={form.retry_delay_seconds}
              onChange={(e) => set('retry_delay_seconds', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Alert on failure */}
        <div className="flex items-center gap-2">
          <input
            id="alert_on_failure"
            type="checkbox"
            checked={form.alert_on_failure}
            onChange={(e) => set('alert_on_failure', e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600"
          />
          <label htmlFor="alert_on_failure" className="text-sm text-gray-700">
            {t('jobForm.labelAlert')}
          </label>
        </div>

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => navigate(isEdit ? `/jobs/${id}` : '/jobs')}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {t('jobForm.cancel')}
          </button>
          <button
            type="submit"
            disabled={isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {isPending ? t('jobForm.saving') : isEdit ? t('jobForm.saveChanges') : t('jobForm.createJob')}
          </button>
        </div>
      </form>
    </div>
  )
}
