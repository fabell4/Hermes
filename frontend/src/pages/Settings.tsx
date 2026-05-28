import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Bell, CalendarClock, Clock, Database, Download, Eye, EyeOff, Key, Save, CheckCircle, XCircle } from 'lucide-react'
import { useHermes } from '@/hooks/useHermes'
import { api } from '@/lib/api'
import type { AlertConfig, RuntimeConfig } from '@/types'

const ALL_EXPORTERS = [
  { id: 'csv', label: 'CSV Export', desc: 'Append results to a local CSV file' },
  { id: 'sqlite', label: 'SQLite', desc: 'Persist results in a local SQLite database' },
  { id: 'prometheus', label: 'Prometheus', desc: 'Expose metrics at /metrics for scraping' },
  { id: 'loki', label: 'Loki', desc: 'Ship structured logs to a Grafana Loki endpoint' },
]



function toggleExporterInConfig(draft: RuntimeConfig, id: string): RuntimeConfig {
  const enabled = draft.enabled_exporters.includes(id)
    ? draft.enabled_exporters.filter((e) => e !== id)
    : [...draft.enabled_exporters, id]
  return { ...draft, enabled_exporters: enabled }
}

function renderExporterItem(exp: typeof ALL_EXPORTERS[number], enabled: boolean, onToggle: () => void) {
  return (
    <div
      key={exp.id}
      className="flex items-center justify-between p-3 rounded-lg bg-slate-100/50 dark:bg-slate-800/30 border border-slate-200/50 dark:border-slate-700/50"
    >
      <div>
        <div className="text-sm font-medium text-slate-800 dark:text-slate-200">
          {exp.label}
        </div>
        <div className="text-xs text-slate-500">{exp.desc}</div>
      </div>
      <button
        onClick={onToggle}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
          enabled ? 'bg-cyan-500' : 'bg-slate-300 dark:bg-slate-700'
        }`}
        aria-pressed={enabled}
      >
        <span
          className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
            enabled ? 'translate-x-5' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  )
}

function renderSaveButton(saved: boolean, onClick: () => void) {
  const className = saved
    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
    : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-500/20'
  const icon = saved ? <CheckCircle size={17} /> : <Save size={17} />
  const label = saved ? 'Saved' : 'Save Changes'
  
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all ${className}`}
    >
      {icon}
      {label}
    </button>
  )
}

function formatHour(h: number): string {
  return h === 24 ? '24:00' : String(h).padStart(2, '0') + ':00'
}


async function saveSettings(
  draft: RuntimeConfig,
  alertsDraft: AlertConfig | null,
  apiKey: string,
  updateConfig: (config: RuntimeConfig) => Promise<void>,
  updateAlerts: (alerts: AlertConfig) => Promise<void>,
  setSaved: (saved: boolean) => void
) {
  if (apiKey) {
    localStorage.setItem('hermes_api_key', apiKey)
  } else {
    localStorage.removeItem('hermes_api_key')
  }
  await updateConfig(draft)
  if (alertsDraft) await updateAlerts(alertsDraft)
  setSaved(true)
  setTimeout(() => setSaved(false), 2500)
}

function useSettingsDraft(config: RuntimeConfig | null) {
  const [draft, setDraft] = useState<RuntimeConfig | null>(null)

  // Initialize local draft once when config first loads.
  // Don't continuously sync to avoid overwriting user's unsaved changes.
  useEffect(() => {
    if (config && !draft) setDraft({ ...config })
  }, [config, draft])

  return { draft, setDraft }
}

function windowDescription(tw: { start_hour: number; end_hour: number }): string {
  if (tw.start_hour < tw.end_hour) {
    return `Tests run between ${String(tw.start_hour).padStart(2, '0')}:00 and ${formatHour(tw.end_hour)} UTC.`
  }
  return `Overnight window — tests run from ${String(tw.start_hour).padStart(2, '0')}:00 UTC, wrapping past midnight to ${String(tw.end_hour).padStart(2, '0')}:00 UTC.`
}

function renderApiKeyInput(
  apiKey: string,
  showKey: boolean,
  setApiKey: (val: string) => void,
  setShowKey: (fn: (prev: boolean) => boolean) => void
) {
  return (
    <div className="relative">
      <input
        id="api-key"
        type={showKey ? 'text' : 'password'}
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        placeholder="Enter API key\u2026"
        autoComplete="current-password"
        className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-4 py-2 pr-10 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all"
      />
      <button
        type="button"
        onClick={() => setShowKey((v) => !v)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
        aria-label={showKey ? 'Hide API key' : 'Show API key'}
      >
        {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
      </button>
    </div>
  )
}

type TestAlertState = 'idle' | 'sending' | 'success' | 'error'

export function Settings() {
  const { config, alerts, updateConfig, updateAlerts } = useHermes()
  const { draft, setDraft } = useSettingsDraft(config)
  const [alertsDraft, setAlertsDraft] = useState<AlertConfig | null>(null)
  const [saved, setSaved] = useState(false)
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('hermes_api_key') ?? '')
  const [showKey, setShowKey] = useState(false)
  const [testAlertState, setTestAlertState] = useState<TestAlertState>('idle')

  useEffect(() => {
    if (alerts && !alertsDraft) setAlertsDraft({ ...alerts })
  }, [alerts, alertsDraft])

  if (!draft) {
    return (
      <div className="text-slate-500 text-sm py-10 text-center">
        Loading configuration…
      </div>
    )
  }

  const handleSave = () => saveSettings(draft, alertsDraft, apiKey, updateConfig, updateAlerts, setSaved)

  const handleTestAlert = async () => {
    setTestAlertState('sending')
    try {
      await api.testAlerts()
      setTestAlertState('success')
    } catch {
      setTestAlertState('error')
    } finally {
      setTimeout(() => setTestAlertState('idle'), 3000)
    }
  }

  const toggleExporter = (id: string) => {
    setDraft(toggleExporterInConfig(draft, id))
  }

  const testAlertButtonClass = (() => {
    if (testAlertState === 'success') return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
    if (testAlertState === 'error') return 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
    return 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30'
  })()

  const testAlertContent = (() => {
    if (testAlertState === 'success') return <><CheckCircle size={15} /><span>Test Sent Successfully</span></>
    if (testAlertState === 'error') return <><XCircle size={15} /><span>Test Failed</span></>
    return <><Bell size={15} /><span>Send Test Notification</span></>
  })()

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-3xl space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Settings</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
          Configure the test interval and active exporters.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Interval */}
        <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-cyan-400" />
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
              Test Interval
            </h2>
          </div>
          <div>
            <label
              htmlFor="interval-minutes"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
            >
              Interval (minutes)
            </label>
            <input
              id="interval-minutes"
              type="number"
              min={5}
              max={1440}
              value={draft.interval_minutes}
              onChange={(e) =>
                setDraft((d) =>
                  d
                    ? {
                        ...d,
                        interval_minutes: Math.max(
                          5,
                          Number.parseInt(e.target.value, 10) || 60
                        ),
                      }
                    : d
                )
              }
              className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
            />
            <p className="text-xs text-slate-500 mt-1">Minimum 5 minutes.</p>
          </div>
        </div>

        {/* Exporters */}
        <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Database size={18} className="text-violet-400" />
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
              Exporters
            </h2>
          </div>
          <div className="space-y-3">
            {ALL_EXPORTERS.map((exp) =>
              renderExporterItem(
                exp,
                draft.enabled_exporters.includes(exp.id),
                () => toggleExporter(exp.id)
              )
            )}
          </div>
        </div>
      </div>



      {/* Test Window */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CalendarClock size={18} className="text-indigo-400" />
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">Test Window</h2>
          </div>
          <button
            type="button"
            onClick={() =>
              setDraft((d) =>
                d
                  ? {
                      ...d,
                      test_window: { ...d.test_window, enabled: !d.test_window.enabled },
                    }
                  : d
              )
            }
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              draft.test_window.enabled ? 'bg-indigo-500' : 'bg-slate-300 dark:bg-slate-700'
            }`}
            aria-pressed={draft.test_window.enabled}
            aria-label="Enable test window"
          >
            <span
              className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                draft.test_window.enabled ? 'translate-x-5' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Restrict automated tests to specific hours to avoid counting against data caps.
          Manual &ldquo;Run Now&rdquo; tests are always allowed.
        </p>
        {draft.test_window.enabled && (
          <div className="space-y-4 pt-1">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="tw-start" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Start hour (UTC)
                </label>
                <select
                  id="tw-start"
                  value={draft.test_window.start_hour}
                  onChange={(e) =>
                    setDraft((d) =>
                      d
                        ? {
                            ...d,
                            test_window: {
                              ...d.test_window,
                              start_hour: Number.parseInt(e.target.value, 10),
                            },
                          }
                        : d
                    )
                  }
                  className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {String(i).padStart(2, '0')}:00
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="tw-end" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  End hour (UTC)
                </label>
                <select
                  id="tw-end"
                  value={draft.test_window.end_hour}
                  onChange={(e) =>
                    setDraft((d) =>
                      d
                        ? {
                            ...d,
                            test_window: {
                              ...d.test_window,
                              end_hour: Number.parseInt(e.target.value, 10),
                            },
                          }
                        : d
                    )
                  }
                  className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  {Array.from({ length: 24 }, (_, i) => i + 1).map((h) => (
                    <option key={h} value={h}>
                      {h === 24 ? '24:00 (midnight)' : `${String(h).padStart(2, '0')}:00`}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <p className="text-xs text-slate-500">
              {windowDescription(draft.test_window)}
            </p>
          </div>
        )}
      </div>

      {/* API Key */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Key size={18} className="text-amber-400" />
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">API Key</h2>
        </div>
        <p className="text-xs text-slate-500">
          Required when the server has <code className="text-slate-600 dark:text-slate-400">API_KEY</code> configured.
          Leave blank for unauthenticated deployments.
        </p>
        {renderApiKeyInput(apiKey, showKey, setApiKey, setShowKey)}
      </div>

      {/* Data Export */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Download size={18} className="text-teal-400" />
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">Data Export</h2>
        </div>
        <p className="text-xs text-slate-500">
          Download the full results history for backup or migration. Files are generated from the
          live SQLite database.
        </p>
        <div className="flex flex-wrap gap-3">
          <a
            href="/api/export/csv"
            download
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-teal-500/10 hover:bg-teal-500/20 text-teal-400 border border-teal-500/30 transition-colors"
          >
            <Download size={15} />
            Export CSV
          </a>
          <a
            href="/api/export/json"
            download
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-teal-500/10 hover:bg-teal-500/20 text-teal-400 border border-teal-500/30 transition-colors"
          >
            <Download size={15} />
            Export JSON
          </a>
        </div>
      </div>

      {/* Alerts */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Bell size={18} className="text-rose-400" />
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">Alerts</h2>
        </div>
        <p className="text-xs text-slate-500">
          Send a test notification to verify your alert providers are configured correctly.
        </p>
        <button
          type="button"
          onClick={handleTestAlert}
          disabled={testAlertState === 'sending'}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${testAlertButtonClass}`}
        >
          {testAlertContent}
        </button>
      </div>

      {/* Save */}
      <div className="flex justify-end">
        {renderSaveButton(saved, handleSave)}
      </div>
    </motion.div>
  )
}
