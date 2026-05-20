import { useTranslation } from 'react-i18next'
import { useWorkspace } from '../../contexts/WorkspaceContext'

export function WorkspaceSelector() {
  const { t } = useTranslation()
  const { workspaces, activeWorkspace, setActiveWorkspace } = useWorkspace()

  if (workspaces.length === 0) return null

  return (
    <div className="mt-2">
      <label className="block text-xs text-gray-400">{t('workspace.selector')}</label>
      <select
        value={activeWorkspace?.id ?? ''}
        onChange={(e) => {
          const found = workspaces.find((w) => w.id === e.target.value) ?? null
          setActiveWorkspace(found)
        }}
        className="mt-1 w-full rounded border border-gray-200 px-2 py-1 text-xs text-gray-700"
      >
        <option value="">{t('workspace.all')}</option>
        {workspaces.map((ws) => (
          <option key={ws.id} value={ws.id}>
            {ws.name}
          </option>
        ))}
      </select>
    </div>
  )
}
