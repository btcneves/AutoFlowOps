import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { listWorkspaces } from '../api/workspaces'
import type { WorkspaceRead } from '../types'

const STORAGE_KEY = 'active_workspace_id'

interface WorkspaceState {
  workspaces: WorkspaceRead[]
  activeWorkspace: WorkspaceRead | null
  setActiveWorkspace: (workspace: WorkspaceRead | null) => void
  refresh: () => Promise<void>
}

const WorkspaceContext = createContext<WorkspaceState | null>(null)

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [workspaces, setWorkspaces] = useState<WorkspaceRead[]>([])
  const [activeWorkspace, setActiveWorkspaceState] = useState<WorkspaceRead | null>(null)

  const refresh = useCallback(async () => {
    try {
      const list = await listWorkspaces()
      setWorkspaces(list)
      const savedId = localStorage.getItem(STORAGE_KEY)
      if (savedId) {
        const found = list.find((w) => w.id === savedId) ?? null
        setActiveWorkspaceState(found)
      }
    } catch {
      // Not authenticated yet — ignore
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const setActiveWorkspace = useCallback((workspace: WorkspaceRead | null) => {
    setActiveWorkspaceState(workspace)
    if (workspace) {
      localStorage.setItem(STORAGE_KEY, workspace.id)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  return (
    <WorkspaceContext.Provider value={{ workspaces, activeWorkspace, setActiveWorkspace, refresh }}>
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useWorkspace(): WorkspaceState {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) throw new Error('useWorkspace must be used inside WorkspaceProvider')
  return ctx
}
