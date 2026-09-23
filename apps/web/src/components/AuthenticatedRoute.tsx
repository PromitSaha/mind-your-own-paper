import { useAuth } from '@clerk/react'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router'

import { fetchCurrentUser } from '../lib/api'

type AuthenticatedRouteProps = {
  children: ReactNode
}

type UserSyncState = 'idle' | 'success' | 'error'

export function AuthenticatedRoute({ children }: AuthenticatedRouteProps) {
  const { getToken, isLoaded, isSignedIn } = useAuth()
  const location = useLocation()
  const [syncState, setSyncState] = useState<UserSyncState>('idle')
  const [syncError, setSyncError] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      return
    }

    let isCancelled = false

    async function syncUser() {
      try {
        const token = await getToken()
        if (!token) {
          throw new Error('Clerk did not return a session token.')
        }

        await fetchCurrentUser(token)

        if (!isCancelled) {
          setSyncState('success')
        }
      } catch (error) {
        if (!isCancelled) {
          setSyncState('error')
          setSyncError(
            error instanceof Error
              ? error.message
              : 'Unable to sync the PaperMind user profile.',
          )
        }
      }
    }

    void syncUser()

    return () => {
      isCancelled = true
    }
  }, [getToken, isLoaded, isSignedIn])

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

  if (syncState === 'idle') {
    return (
      <main className="auth-screen">
        <p className="muted">Syncing your PaperMind profile...</p>
      </main>
    )
  }

  if (syncState === 'error') {
    return (
      <main className="auth-screen">
        <section className="auth-card">
          <p className="eyebrow">PaperMind</p>
          <h1>Profile sync failed</h1>
          <p className="error-text">
            {syncError ?? 'Unable to sync the PaperMind user profile.'}
          </p>
        </section>
      </main>
    )
  }

  return children
}
