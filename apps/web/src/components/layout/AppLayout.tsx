import {
  SignOutButton,
  UserButton,
} from '@clerk/react'
import { NavLink, Outlet } from 'react-router'

import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { toggleSidebar } from '../../features/ui/uiSlice'

const navigationItems = [
  { label: 'Dashboard', to: '/dashboard' },
  { label: 'Papers', to: '/papers' },
  { label: 'Settings', to: '/settings' },
]

export function AppLayout() {
  const dispatch = useAppDispatch()
  const isSidebarOpen = useAppSelector((state) => state.ui.isSidebarOpen)

  return (
    <div className="app-shell" data-sidebar-open={isSidebarOpen}>
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark">PM</span>
          <span>PaperMind</span>
        </div>

        <nav className="nav-list">
          {navigationItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? 'nav-link nav-link--active' : 'nav-link'
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="main-region">
        <header className="topbar">
          <button
            type="button"
            className="icon-button"
            onClick={() => dispatch(toggleSidebar())}
            aria-label="Toggle sidebar"
          >
            ☰
          </button>

          <div className="auth-actions">
            <UserButton />
            <SignOutButton>
              <button type="button" className="text-button text-button--danger">
                Log out
              </button>
            </SignOutButton>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
