import { FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useCreateEscalationPolicy,
  useDeleteEscalationPolicy,
  useDeleteEscalationStep,
  useEscalationPolicies,
  useUpdateEscalationPolicy,
} from '../hooks/useEscalation'
import { useNotificationChannels } from '../hooks/useNotifications'
import type { EscalationPolicyRead, EscalationStepPayload } from '../types'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

function PolicyForm({
  editing,
  onDone,
}: {
  editing: EscalationPolicyRead | null
  onDone: () => void
}) {
  const { t } = useTranslation()
  const create = useCreateEscalationPolicy()
  const update = useUpdateEscalationPolicy()
  const { data: channels } = useNotificationChannels()
  const [name, setName] = useState(editing?.name ?? '')
  const [isActive, setIsActive] = useState(editing?.is_active ?? true)
  const [steps, setSteps] = useState<EscalationStepPayload[]>(
    editing
      ? editing.steps.map((s) => ({
          channel_id: s.channel_id,
          step_order: s.step_order,
          delay_minutes: s.delay_minutes,
        }))
      : [{ channel_id: '', step_order: 0, delay_minutes: 0 }]
  )
  const [error, setError] = useState<string | null>(null)
  const isPending = create.isPending || update.isPending

  function addStep() {
    setSteps([
      ...steps,
      { channel_id: '', step_order: steps.length, delay_minutes: 10 },
    ])
  }

  function removeStep(index: number) {
    setSteps(steps.filter((_, i) => i !== index).map((s, i) => ({ ...s, step_order: i })))
  }

  function updateStep(index: number, field: keyof EscalationStepPayload, value: string | number) {
    setSteps(steps.map((s, i) => (i === index ? { ...s, [field]: value } : s)))
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!name.trim()) {
      setError(t('escalation.errorName'))
      return
    }
    const payload = { name: name.trim(), is_active: isActive, steps }
    const mutation = editing
      ? update.mutateAsync({ id: editing.id, payload })
      : create.mutateAsync(payload)
    void mutation.then(onDone).catch((err: Error) => setError(err.message))
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">
          {editing ? t('escalation.formTitleEdit') : t('escalation.formTitleNew')}
        </h2>
        {editing && (
          <button
            type="button"
            onClick={onDone}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {t('escalation.cancel')}
          </button>
        )}
      </div>
      <div className="mb-4 flex items-center gap-4">
        <label className="flex-1 text-xs font-medium text-gray-600">
          {t('escalation.labelName')}
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="flex items-center gap-2 pt-5 text-xs font-medium text-gray-600">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          {t('escalation.labelActive')}
        </label>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-gray-600">{t('escalation.labelSteps')}</p>
        {steps.map((step, index) => (
          <div key={index} className="flex items-center gap-2 rounded border border-gray-100 p-2">
            <span className="w-6 text-center text-xs text-gray-400">{index + 1}</span>
            <label className="flex-1 text-xs text-gray-600">
              {t('escalation.labelChannel')}
              <select
                value={step.channel_id}
                onChange={(e) => updateStep(index, 'channel_id', e.target.value)}
                className="mt-0.5 w-full rounded border border-gray-300 px-2 py-1 text-sm"
              >
                <option value="">{t('escalation.selectChannel')}</option>
                {channels?.map((ch) => (
                  <option key={ch.id} value={ch.id}>{ch.name}</option>
                ))}
              </select>
            </label>
            <label className="w-28 text-xs text-gray-600">
              {t('escalation.labelDelay')}
              <input
                type="number"
                min={0}
                value={step.delay_minutes}
                onChange={(e) => updateStep(index, 'delay_minutes', Number(e.target.value))}
                className="mt-0.5 w-full rounded border border-gray-300 px-2 py-1 text-sm"
              />
            </label>
            {steps.length > 1 && (
              <button
                type="button"
                onClick={() => removeStep(index)}
                className="mt-3 text-xs text-red-500 hover:text-red-700"
              >
                {t('escalation.remove')}
              </button>
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={addStep}
          className="text-xs text-blue-600 hover:underline"
        >
          {t('escalation.addStep')}
        </button>
      </div>

      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
      <button
        disabled={isPending}
        className="mt-4 rounded bg-gray-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
      >
        {editing ? t('escalation.savePolicy') : t('escalation.createPolicy')}
      </button>
    </form>
  )
}

function PolicyRow({
  policy,
  onEdit,
}: {
  policy: EscalationPolicyRead
  onEdit: (p: EscalationPolicyRead) => void
}) {
  const { t } = useTranslation()
  const remove = useDeleteEscalationPolicy()
  const deleteStep = useDeleteEscalationStep()
  const { data: channels } = useNotificationChannels()

  function channelName(id: string): string {
    return channels?.find((c) => c.id === id)?.name ?? id.slice(0, 8)
  }

  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">{policy.name}</td>
      <td className="py-3 pr-4">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            policy.is_active
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          {policy.is_active ? t('escalation.active') : t('escalation.inactive')}
        </span>
      </td>
      <td className="py-3 pr-4 text-xs text-gray-600">
        {policy.steps.length === 0 ? (
          '—'
        ) : (
          <ol className="list-inside list-decimal space-y-0.5">
            {policy.steps
              .slice()
              .sort((a, b) => a.step_order - b.step_order)
              .map((step) => (
                <li key={step.id} className="flex items-center gap-1">
                  <span>
                    {channelName(step.channel_id)}
                    {step.delay_minutes > 0
                      ? ` ${t('escalation.delayMin', { delay: step.delay_minutes })}`
                      : ` ${t('escalation.immediate')}`}
                  </span>
                  <button
                    onClick={() =>
                      deleteStep.mutate({ policyId: policy.id, stepId: step.id })
                    }
                    className="text-red-400 hover:text-red-600"
                    title={t('escalation.removeStep')}
                  >
                    ×
                  </button>
                </li>
              ))}
          </ol>
        )}
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(policy.created_at)}</td>
      <td className="py-3 pr-4 text-right space-x-1">
        <button
          onClick={() => onEdit(policy)}
          className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
        >
          {t('escalation.edit')}
        </button>
        <button
          onClick={() => remove.mutate(policy.id)}
          disabled={remove.isPending}
          className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
        >
          {t('escalation.delete')}
        </button>
      </td>
    </tr>
  )
}

export function EscalationPoliciesPage() {
  const { t } = useTranslation()
  const { data: policies, isLoading, isError } = useEscalationPolicies()
  const [editing, setEditing] = useState<EscalationPolicyRead | null>(null)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('escalation.title')}</h1>
        <p className="mt-1 text-sm text-gray-500">{t('escalation.subtitle')}</p>
      </div>

      <PolicyForm editing={editing} onDone={() => setEditing(null)} />

      {isLoading && <p className="text-sm text-gray-500">{t('escalation.loading')}</p>}
      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t('escalation.error')}
        </div>
      )}
      {!isLoading && !isError && policies && policies.length === 0 && (
        <p className="text-sm text-gray-500">{t('escalation.empty')}</p>
      )}
      {!isLoading && !isError && policies && policies.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">{t('escalation.colName')}</th>
                <th className="py-3 pr-4">{t('escalation.colStatus')}</th>
                <th className="py-3 pr-4">{t('escalation.colSteps')}</th>
                <th className="py-3 pr-4">{t('escalation.colCreated')}</th>
                <th className="py-3 pr-4 text-right">{t('escalation.colActions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {policies.map((policy) => (
                <PolicyRow key={policy.id} policy={policy} onEdit={setEditing} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
