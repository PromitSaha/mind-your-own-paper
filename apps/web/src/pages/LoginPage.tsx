import { SignInButton, SignUpButton, useAuth } from '@clerk/react'
import { Navigate, useLocation } from 'react-router'

type RedirectState = {
  from?: {
    pathname?: string
  }
}

export function LoginPage() {
  const { isLoaded, isSignedIn } = useAuth()
  const location = useLocation()
  const state = location.state as RedirectState | null
  const redirectPath = state?.from?.pathname ?? '/dashboard'

  if (!isLoaded) {
    return (
      <main className="auth-screen">
        <p className="muted">Loading authentication...</p>
      </main>
    )
  }

  if (isSignedIn) {
    return <Navigate to={redirectPath} replace />
  }

  return (
    <main className="auth-screen">
      <section className="auth-card">
        <span className="brand-mark auth-brand-mark" aria-hidden="true" />
        <p className="eyebrow">PaperMind</p>
        <h1>Sign in to continue</h1>
        <p>
          Your research workspace is protected. Sign in or create an account to
          access your dashboard, folders, chats, and shared paper files.
        </p>

        <div className="button-row">
          <SignInButton mode="modal">
            <button type="button" className="primary-button">
              Sign in
            </button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button type="button" className="text-button">
              Create account
            </button>
          </SignUpButton>
        </div>
      </section>
    </main>
  )
}
