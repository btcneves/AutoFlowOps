import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getMe, login as apiLogin } from '../api/auth'
import type { LoginRequest, UserRead } from '../types'

interface AuthState {
  user: UserRead | null
  isLoading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  isOperator: boolean
  login: (payload: LoginRequest) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

function roleLevel(role: string): number {
  const levels: Record<string, number> = { admin: 3, operator: 2, viewer: 1, user: 1 }
  return levels[role] ?? 0
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setIsLoading(false)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('access_token')
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (payload: LoginRequest) => {
    const token = await apiLogin(payload)
    localStorage.setItem('access_token', token.access_token)
    const me = await getMe()
    setUser(me)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    setUser(null)
  }, [])

  const level = roleLevel(user?.role ?? '')

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        isAdmin: level >= 3,
        isOperator: level >= 2,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
