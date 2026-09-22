export function MissingClerkConfig() {
  return (
    <main className="missing-config">
      <h1>Clerk is not configured</h1>
      <p>
        Add <code>VITE_CLERK_PUBLISHABLE_KEY</code> to{' '}
        <code>apps/web/.env.local</code>, then restart the Vite dev server.
      </p>
    </main>
  )
}
