import { useAuth } from '@clerk/react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

type AuthenticatedRouteProps = {
  children: ReactNode
}

export function AuthenticatedRoute({ children }: AuthenticatedRouteProps) {
  const { isLoaded, isSignedIn } = useAuth()
  const location = useLocation()

  if (!isLoaded) {
    return (
      <main className="auth-screen">
        <p className="muted">Checking authentication...</p>
      </main>
    )
  }

  if (!isSignedIn) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}
