import { useAuth } from '@clerk/react'
import { useState } from 'react'

import { type CurrentUserResponse, fetchCurrentUser } from '../lib/api'

type AuthCheckState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; user: CurrentUserResponse }
  | { status: 'error'; message: string }

export function DashboardPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth()
  const [authCheck, setAuthCheck] = useState<AuthCheckState>({ status: 'idle' })

  async function handleCheckBackendAuth() {
    if (!isSignedIn) {
      setAuthCheck({
        status: 'error',
        message: 'Sign in with Clerk before checking backend auth.',
      })
      return
    }

    setAuthCheck({ status: 'loading' })

    try {
      const token = await getToken()
      if (!token) {
        throw new Error('Clerk did not return a session token.')
      }

      const user = await fetchCurrentUser(token)
      setAuthCheck({ status: 'success', user })
    } catch (error) {
      setAuthCheck({
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown auth error',
      })
    }
  }

  return (
    <section className="page-stack">
      <div className="page-heading">
        <p className="eyebrow">Workspace</p>
        <h1>Research dashboard</h1>
        <p>
          Start with authentication, then grow into projects, papers, citations,
          and source-grounded research chat.
        </p>
      </div>

      <div className="panel-grid">
        <article className="panel">
          <h2>Backend Auth</h2>
          <p>
            Use this check after signing in to verify that Clerk and FastAPI can
            agree on the current user.
          </p>
          <button
            type="button"
            className="primary-button"
            onClick={handleCheckBackendAuth}
            disabled={!isLoaded || authCheck.status === 'loading'}
          >
            {authCheck.status === 'loading'
              ? 'Checking...'
              : 'Check backend auth'}
          </button>

          {authCheck.status === 'success' ? (
            <pre className="result-box">
              {JSON.stringify(authCheck.user, null, 2)}
            </pre>
          ) : null}

          {authCheck.status === 'error' ? (
            <p className="error-text">{authCheck.message}</p>
          ) : null}
        </article>

        <article className="panel">
          <h2>Next Product Slice</h2>
          <p>
            Once auth is proven end to end, the next backend layer can add a
            local user record, projects, and ownership checks.
          </p>
        </article>
      </div>
    </section>
  )
}
