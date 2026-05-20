import { FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createWorkspace,
  deleteWorkspace,
  listWorkspaces,
} from '../api/workspaces'
import { useWorkspace } from '../contexts/WorkspaceContext'
import type { WorkspaceRead } from '../types'

export function WorkspaceSettingsPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const { setActiveWorkspace, activeWorkspace, refresh } = useWorkspace()

  const { data: workspaces, isLoading, isError } = useQuery({
    queryKey: ['workspaces'],
    queryFn: listWorkspaces,
  })

  const create = useMutation({
    mutationFn: createWorkspace,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['workspaces'] })
      void refresh()
    },
  })

  const remove = useMutation({
    mutationFn: deleteWorkspace,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['workspaces'] })
      void refresh()
    },
  })

  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [error, setError] = useState<string | null>(null)

  function handleCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!name.trim() || !slug.trim()) {
      setError(t('workspace.errorRequired'))
      return
    }
    create.mutate(
      { name: name.trim(), slug: slug.trim() },
      {
        onSuccess: () => {
          setName('')
          setSlug('')
        },
        onError: (err: Error) => setError(err.message),
      },
    )
  }

  function handleDelete(workspace: WorkspaceRead) {
    if (workspace.is_default) return
    if (activeWorkspace?.id === workspace.id) setActiveWorkspace(null)
    remove.mutate(workspace.id)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('workspace.title')}</h1>
        <p className="mt-1 text-sm text-gray-500">{t('workspace.subtitle')}</p>
      </div>

      <form
        onSubmit={handleCreate}
        className="mb-6 grid gap-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm md:grid-cols-[1fr_1fr_auto]"
      >
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          {t('workspace.labelName')}
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('workspace.placeholderName')}
            className="rounded-md border border-gray-200 px-3 py-2 text-sm font-normal text-gray-900 outline-none focus:border-blue-400"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-600">
          {t('workspace.labelSlug')}
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
            placeholder={t('workspace.placeholderSlug')}
            className="rounded-md border border-gray-200 px-3 py-2 text-sm font-normal text-gray-900 outline-none focus:border-blue-400"
          />
        </label>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={create.isPending}
            className="w-full rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {t('workspace.create')}
          </button>
        </div>
        {error && <p className="col-span-3 text-xs text-red-600">{error}</p>}
      </form>

      {isLoading && <p className="text-sm text-gray-500">{t('workspace.loading')}</p>}
      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t('workspace.error')}
        </div>
      )}

      {!isLoading && !isError && workspaces && workspaces.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">{t('workspace.colName')}</th>
                <th className="py-3 pr-4">{t('workspace.colSlug')}</th>
                <th className="py-3 pr-4">{t('workspace.colDefault')}</th>
                <th className="py-3 pr-4 text-right">{t('workspace.colActions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {workspaces.map((ws) => (
                <tr key={ws.id} className="border-t border-gray-100">
                  <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">{ws.name}</td>
                  <td className="py-3 pr-4 text-xs text-gray-500">{ws.slug}</td>
                  <td className="py-3 pr-4 text-xs text-gray-500">
                    {ws.is_default ? t('workspace.yes') : '—'}
                  </td>
                  <td className="py-3 pr-4 text-right">
                    {!ws.is_default && (
                      <button
                        onClick={() => handleDelete(ws)}
                        disabled={remove.isPending}
                        className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        {t('workspace.delete')}
                      </button>
                    )}
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
