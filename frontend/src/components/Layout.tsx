import React, { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { LayoutDashboard, Settings, Menu, X, Zap, ArrowUpCircle } from 'lucide-react'
import { useHermes } from '@/hooks/useHermes'
import hermesLogo from '@/assets/Hermes.svg'

const GITHUB_REPO = 'fabell4/hermes'

function useUpdateCheck(currentVersion: string | undefined) {
  const [latestVersion, setLatestVersion] = useState<string | null>(null)

  useEffect(() => {
    if (!currentVersion || currentVersion === 'dev') return
    fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`, {
      headers: { Accept: 'application/vnd.github+json' },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.tag_name) setLatestVersion(data.tag_name.replace(/^v/, ''))
      })
      .catch(() => null)
  }, [currentVersion])

  const updateAvailable =
    latestVersion != null &&
    currentVersion != null &&
    currentVersion !== 'dev' &&
    latestVersion !== currentVersion

  return { latestVersion, updateAvailable }
}

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Layout({ children }: { readonly children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { health } = useHermes()
  const currentVersion = health?.version
  const { latestVersion, updateAvailable } = useUpdateCheck(currentVersion)

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
      isActive
        ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
    }`

  const sidebar = (
    <nav className="flex flex-col gap-1 p-4">
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={navLinkClass}
          onClick={() => setMobileOpen(false)}
        >
          <Icon size={18} />
          {label}
        </NavLink>
      ))}
    </nav>
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-40 h-14 border-b border-slate-800 bg-slate-950/90 backdrop-blur flex items-center px-4 gap-3">
        <button
          className="lg:hidden p-2 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
          onClick={() => setMobileOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        <div className="flex items-center gap-2">
          <img src={hermesLogo} alt="Hermes" className="h-7 w-7" />
          <span className="font-bold text-slate-100 text-lg tracking-tight">
            Hermes
          </span>
          <span className="hidden sm:inline text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
            <Zap size={10} className="inline mr-1 text-cyan-400" />
            Speed Monitor
          </span>
          {currentVersion && (
            <span className="hidden sm:inline text-xs px-2 py-0.5 rounded-full bg-slate-800/60 text-slate-500 border border-slate-700/50 font-mono">
              v{currentVersion}
            </span>
          )}
          {updateAvailable && (
            <a
              href={`https://github.com/${GITHUB_REPO}/releases/latest`}
              target="_blank"
              rel="noreferrer"
              className="hidden sm:flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/20 transition-colors"
              title={`v${latestVersion} available`}
            >
              <ArrowUpCircle size={11} />
              Update available
            </a>
          )}
        </div>
      </header>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col fixed top-14 left-0 bottom-0 w-56 border-r border-slate-800 bg-slate-950/50">
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-30 bg-slate-950/70 lg:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'tween', duration: 0.22 }}
              className="fixed top-14 left-0 bottom-0 w-56 z-40 border-r border-slate-800 bg-slate-950 lg:hidden"
            >
              {sidebar}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main content */}
      <main className="pt-14 lg:ml-56 min-h-screen">
        <div className="max-w-6xl mx-auto p-4 md:p-6">{children}</div>
      </main>
    </div>
  )
}
