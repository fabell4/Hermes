import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Clock, Database, Eye, EyeOff, Key, Save, CheckCircle, Bell, Send } from 'lucide-react'
import { useHermes } from '@/hooks/useHermes'
import type { RuntimeConfig, AlertConfig } from '@/types'
import { api } from '@/lib/api'

const ALL_EXPORTERS = [
  { id: 'csv', label: 'CSV Export', desc: 'Append results to a local CSV file' },
  { id: 'sqlite', label: 'SQLite', desc: 'Persist results in a local SQLite database' },
  { id: 'prometheus', label: 'Prometheus', desc: 'Expose metrics at /metrics for scraping' },
  { id: 'loki', label: 'Loki', desc: 'Ship structured logs to a Grafana Loki endpoint' },
]

type TestAlertStatus = 'idle' | 'sending' | 'success' | 'error'

function getTestButtonClassName(status: TestAlertStatus): string {
  if (status === 'sending') {
    return 'bg-slate-700 text-slate-400 cursor-not-allowed'
  }
  if (status === 'success') {
    return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
  }
  if (status === 'error') {
    return 'bg-red-500/20 text-red-400 border border-red-500/30'
  }
  return 'bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
}

function renderTestButtonContent(status: TestAlertStatus) {
  if (status === 'sending') {
    return (
      <>
        <div className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
        Sending...
      </>
    )
  }
  if (status === 'success') {
    return (
      <>
        <CheckCircle size={16} />
        Test Sent Successfully
      </>
    )
  }
  if (status === 'error') {
    return (
      <>
        <span className="text-red-400">\u26a0</span>
        {' '}
        Test Failed
      </>
    )
  }
  return (
    <>
      <Send size={16} />
      Send Test Notification
    </>
  )
}

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
      className="flex items-center justify-between p-3 rounded-lg bg-slate-800/30 border border-slate-700/50"
    >
      <div>
        <div className="text-sm font-medium text-slate-200">
          {exp.label}
        </div>
        <div className="text-xs text-slate-500">{exp.desc}</div>
      </div>
      <button
        onClick={onToggle}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
          enabled ? 'bg-cyan-500' : 'bg-slate-700'
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

async function saveSettings(
  draft: RuntimeConfig,
  alertsDraft: AlertConfig,
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
  await Promise.all([updateConfig(draft), updateAlerts(alertsDraft)])
  setSaved(true)
  setTimeout(() => setSaved(false), 2500)
}

export function Settings() {
  const { config, alerts, updateConfig, updateAlerts } = useHermes()
  const [draft, setDraft] = useState<RuntimeConfig | null>(null)
  const [alertsDraft, setAlertsDraft] = useState<AlertConfig | null>(null)
  const [saved, setSaved] = useState(false)
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('hermes_api_key') ?? '')
  const [showKey, setShowKey] = useState(false)
  const [testStatus, setTestStatus] = useState<TestAlertStatus>('idle')
  const [testMessage, setTestMessage] = useState('')

  // Initialize local drafts once when config/alerts first load
  // Don't continuously sync to avoid overwriting user's unsaved changes
  useEffect(() => {
    if (config && !draft) {
      setDraft({ ...config })
    }
  }, [config, draft])

  useEffect(() => {
    if (alerts && !alertsDraft) {
      setAlertsDraft({ ...alerts })
    }
  }, [alerts, alertsDraft])

  if (!draft || !alertsDraft) {
    return (
      <div className="text-slate-500 text-sm py-10 text-center">
        Loading configuration…
      </div>
    )
  }

  const handleSave = () => saveSettings(draft, alertsDraft, apiKey, updateConfig, updateAlerts, setSaved)

  const handleTestAlerts = async () => {
    setTestStatus('sending')
    setTestMessage('')
    try {
      const response = await api.testAlerts()
      setTestStatus('success')
      setTestMessage(response.message)
      setTimeout(() => {
        setTestStatus('idle')
        setTestMessage('')
      }, 5000)
    } catch (error) {
      setTestStatus('error')
      setTestMessage(error instanceof Error ? error.message : 'Failed to send test alerts')
      setTimeout(() => {
        setTestStatus('idle')
        setTestMessage('')
      }, 5000)
    }
  }

  const toggleExporter = (id: string) => {
    setDraft(toggleExporterInConfig(draft, id))
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-3xl space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Settings</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Configure the test interval and active exporters.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Interval */}
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-cyan-400" />
            <h2 className="text-base font-semibold text-slate-200">
              Test Interval
            </h2>
          </div>
          <div>
            <label
              htmlFor="interval-minutes"
              className="block text-sm font-medium text-slate-300 mb-2"
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
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
            />
            <p className="text-xs text-slate-500 mt-1">Minimum 5 minutes.</p>
          </div>
        </div>

        {/* Exporters */}
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Database size={18} className="text-violet-400" />
            <h2 className="text-base font-semibold text-slate-200">
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

      {/* Alerts */}
      {alertsDraft && (
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell size={18} className="text-orange-400" />
              <h2 className="text-base font-semibold text-slate-200">Alerts</h2>
            </div>
            <button
              onClick={() =>
                setAlertsDraft((d) => (d ? { ...d, enabled: !d.enabled } : d))
              }
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                alertsDraft.enabled ? 'bg-orange-500' : 'bg-slate-700'
              }`}
              aria-pressed={alertsDraft.enabled}
            >
              <span
                className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                  alertsDraft.enabled ? 'translate-x-5' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          
          <p className="text-xs text-slate-500">
            Get notified when speed tests fail consecutively. Configure providers below or via environment variables (restart required).
          </p>

          {alertsDraft.enabled && (
            <div className="space-y-4 pt-2">
              {/* Threshold and Cooldown */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="failure-threshold" className="block text-sm font-medium text-slate-300 mb-2">
                    Failure Threshold
                  </label>
                  <input
                    id="failure-threshold"
                    type="number"
                    min={1}
                    max={100}
                    value={alertsDraft.failure_threshold}
                    onChange={(e) =>
                      setAlertsDraft((d) =>
                        d
                          ? {
                              ...d,
                              failure_threshold: Math.max(
                                1,
                                Number.parseInt(e.target.value, 10) || 3
                              ),
                            }
                          : d
                      )
                    }
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Alert after N failures
                  </p>
                </div>
                <div>
                  <label htmlFor="cooldown-minutes" className="block text-sm font-medium text-slate-300 mb-2">
                    Cooldown Period (minutes)
                  </label>
                  <input
                    id="cooldown-minutes"
                    type="number"
                    min={0}
                    max={1440}
                    value={alertsDraft.cooldown_minutes}
                    onChange={(e) =>
                      setAlertsDraft((d) =>
                        d
                          ? {
                              ...d,
                              cooldown_minutes: Math.max(
                                0,
                                Number.parseInt(e.target.value, 10) || 60
                              ),
                            }
                          : d
                      )
                    }
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Time between alerts
                  </p>
                </div>
              </div>

              {/* Webhook Provider */}
              <div className="border-t border-slate-700 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-slate-300">Webhook</h3>
                  <button
                    onClick={() =>
                      setAlertsDraft((d) =>
                        d
                          ? {
                              ...d,
                              providers: {
                                ...d.providers,
                                webhook: {
                                  ...d.providers.webhook,
                                  enabled: !d.providers.webhook.enabled,
                                },
                              },
                            }
                          : d
                      )
                    }
                    className={`relative inline-flex h-4 w-8 items-center rounded-full transition-colors ${
                      alertsDraft.providers.webhook.enabled ? 'bg-cyan-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white transition-transform ${
                        alertsDraft.providers.webhook.enabled ? 'translate-x-4.5' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                {alertsDraft.providers.webhook.enabled && (
                  <input
                    type="url"
                    placeholder="https://webhook.example.com/alerts"
                    value={alertsDraft.providers.webhook.url}
                    onChange={(e) =>
                      setAlertsDraft((d) =>
                        d
                          ? {
                              ...d,
                              providers: {
                                ...d.providers,
                                webhook: { ...d.providers.webhook, url: e.target.value },
                              },
                            }
                          : d
                      )
                    }
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                  />
                )}
              </div>

              {/* Gotify Provider */}
              <div className="border-t border-slate-700 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-slate-300">Gotify</h3>
                  <button
                    onClick={() =>
                      setAlertsDraft((d) =>
                        d
                          ? {
                              ...d,
                              providers: {
                                ...d.providers,
                                gotify: {
                                  ...d.providers.gotify,
                                  enabled: !d.providers.gotify.enabled,
                                },
                              },
                            }
                          : d
                      )
                    }
                    className={`relative inline-flex h-4 w-8 items-center rounded-full transition-colors ${
                      alertsDraft.providers.gotify.enabled ? 'bg-cyan-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white transition-transform ${
                        alertsDraft.providers.gotify.enabled ? 'translate-x-4.5' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                {alertsDraft.providers.gotify.enabled && (
                  <div className="space-y-2">
                    <input
                      type="url"
                      placeholder="https://gotify.example.com"
                      value={alertsDraft.providers.gotify.url}
                      onChange={(e) =>
                        setAlertsDraft((d) =>
                          d
                            ? {
                                ...d,
                                providers: {
                                  ...d.providers,
                                  gotify: { ...d.providers.gotify, url: e.target.value },
                                },
                              }
                            : d
                        )
                      }
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                    />
                    <input
                      type="password"
                      placeholder="App token"
                      value={alertsDraft.providers.gotify.token}
                      onChange={(e) =>
                        setAlertsDraft((d) =>
                          d
                            ? {
                                ...d,
                                providers: {
                                  ...d.providers,
                                  gotify: { ...d.providers.gotify, token: e.target.value },
                                },
                              }
                            : d
                        )
                      }
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                    />
                  </div>
                )}
              </div>

              {/* ntfy Provider */}
              <div className="border-t border-slate-700 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-slate-300">ntfy</h3>
                  <button
                    onClick={() =>
                      setAlertsDraft((d) =>
                        d
                          ? {
                              ...d,
                              providers: {
                                ...d.providers,
                                ntfy: {
                                  ...d.providers.ntfy,
                                  enabled: !d.providers.ntfy.enabled,
                                },
                              },
                            }
                          : d
                      )
                    }
                    className={`relative inline-flex h-4 w-8 items-center rounded-full transition-colors ${
                      alertsDraft.providers.ntfy.enabled ? 'bg-cyan-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white transition-transform ${
                        alertsDraft.providers.ntfy.enabled ? 'translate-x-4.5' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                {alertsDraft.providers.ntfy.enabled && (
                  <div className="space-y-2">
                    <input
                      type="text"
                      placeholder="Topic name"
                      value={alertsDraft.providers.ntfy.topic}
                      onChange={(e) =>
                        setAlertsDraft((d) =>
                          d
                            ? {
                                ...d,
                                providers: {
                                  ...d.providers,
                                  ntfy: { ...d.providers.ntfy, topic: e.target.value },
                                },
                              }
                            : d
                        )
                      }
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                    />
                    <input
                      type="password"
                      placeholder="Access token (optional)"
                      value={alertsDraft.providers.ntfy.token}
                      onChange={(e) =>
                        setAlertsDraft((d) =>
                          d
                            ? {
                                ...d,
                                providers: {
                                  ...d.providers,
                                  ntfy: { ...d.providers.ntfy, token: e.target.value },
                                },
                              }
                            : d
                        )
                      }
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                    />
                    <input
                      type="url"
                      placeholder="https://ntfy.sh (optional)"
                      value={alertsDraft.providers.ntfy.url}
                      onChange={(e) =>
                        setAlertsDraft((d) =>
                          d
                            ? {
                                ...d,
                                providers: {
                                  ...d.providers,
                                  ntfy: { ...d.providers.ntfy, url: e.target.value },
                                },
                              }
                            : d
                        )
                      }
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                    />
                  </div>
                )}
              </div>

              {/* Apprise Provider */}
              <div className="border-t border-slate-800 pt-3">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="text-sm font-medium text-slate-300">Apprise</span>
                    <p className="text-xs text-slate-500 mt-0.5">
                      100+ services (Discord, Telegram, Slack, etc.)
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setAlertsDraft((d) =>
                        d
                          ? {
                              ...d,
                              providers: {
                                ...d.providers,
                                apprise: {
                                  ...d.providers.apprise,
                                  enabled: !d.providers.apprise.enabled,
                                },
                              },
                            }
                          : d
                      )
                    }
                    className={`relative inline-flex h-4 w-8 items-center rounded-full transition-colors ${
                      alertsDraft.providers.apprise.enabled ? 'bg-cyan-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white transition-transform ${
                        alertsDraft.providers.apprise.enabled ? 'translate-x-4.5' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                {alertsDraft.providers.apprise.enabled && (
                  <div className="space-y-2">
                    <input
                      type="url"
                      placeholder="http://apprise:8000" // NOSONAR: example for local Docker service
                      value={alertsDraft.providers.apprise.url}
                      onChange={(e) =>
                        setAlertsDraft((d) =>
                          d
                            ? {
                                ...d,
                                providers: {
                                  ...d.providers,
                                  apprise: { ...d.providers.apprise, url: e.target.value },
                                },
                              }
                            : d
                        )
                      }
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                    />
                    <p className="text-xs text-slate-500">
                      URL to Apprise API service. See{' '}
                      <a
                        href="https://github.com/caronc/apprise-api"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-400 hover:underline"
                      >
                        Apprise API
                      </a>{' '}
                      for setup instructions
                    </p>
                  </div>
                )}
              </div>

              {/* Test Alert Button */}
              <div className="pt-4 border-t border-slate-700/50">
                <button
                  onClick={handleTestAlerts}
                  disabled={testStatus === 'sending'}
                  className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${getTestButtonClassName(testStatus)}`}
                >
                  {renderTestButtonContent(testStatus)}
                </button>
                {testMessage && (
                  <p className={`text-xs mt-2 ${
                    testStatus === 'success' ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    {testMessage}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* API Key */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Key size={18} className="text-amber-400" />
          <h2 className="text-base font-semibold text-slate-200">API Key</h2>
        </div>
        <p className="text-xs text-slate-500">
          Required when the server has <code className="text-slate-400">API_KEY</code> configured.
          Leave blank for unauthenticated deployments.
        </p>
        <div className="relative">
          <input
            id="api-key"
            type={showKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Enter API key…"
            autoComplete="current-password"
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 pr-10 text-slate-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all"
          />
          <button
            type="button"
            onClick={() => setShowKey((v) => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
            aria-label={showKey ? 'Hide API key' : 'Show API key'}
          >
            {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
      </div>

      {/* Save */}
      <div className="flex justify-end">
        {renderSaveButton(saved, handleSave)}
      </div>
    </motion.div>
  )
}
