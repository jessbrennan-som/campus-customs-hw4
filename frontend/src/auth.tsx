import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { accounts, type User } from './api'

// Who is logged in. The browser keeps the login cookie; this just asks the backend "who am I?" once
// when the site opens and remembers the answer.

type Auth = {
  user: User | null
  ready: boolean // false until the first "who am I?" answer arrives
  setUser: (u: User | null) => void
  logOut: () => Promise<void>
}

const AuthContext = createContext<Auth | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    accounts
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setReady(true))
  }, [])

  const logOut = useCallback(async () => {
    await accounts.logout().catch(() => undefined)
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, ready, setUser, logOut }), [user, ready, logOut])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth must be used inside <AuthProvider>')
  return auth
}
