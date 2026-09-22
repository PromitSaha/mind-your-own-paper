export function SettingsPage() {
  return (
    <section className="page-stack">
      <div className="page-heading">
        <p className="eyebrow">Account</p>
        <h1>Settings</h1>
        <p>
          This route gives us a place for user management, account preferences,
          and future workspace settings.
        </p>
      </div>

      <article className="panel">
        <h2>User Management</h2>
        <p>
          Clerk will provide authentication identity. PaperMind can later store
          application-specific profile and workspace data in PostgreSQL.
        </p>
      </article>
    </section>
  )
}
