import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Bell,
  Send,
  Save,
  CheckCircle,
} from 'lucide-react'
import { useHermes } from '@/hooks/useHermes'
import type { AlertConfig } from '@/types'
import { api } from '@/lib/api'

type TestAlertStatus = 'idle' | 'sending' | 'success' | 'error'

function getTestButtonClassName(status: TestAlertStatus): string {
  if (status === 'sending') {
    return 'bg-slate-100 dark:bg-slate-700 text-slate-400 cursor-not-allowed'
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
        <span className="text-red-400">⚠</span>
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

async function sendTestAlerts(
  setTestStatus: (status: TestAlertStatus) => void,
  setTestMessage: (message: string) => void
): Promise<void> {
  setTestStatus('sending')
  setTestMessage('')
  try {
    const response = await api.testAlerts()
    if (response.status === 'success' || response.status === 'partial') {
      setTestStatus('success')
    } else {
      setTestStatus('error')
    }
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

function ProviderToggle({
  enabled,
  onToggle,
}: Readonly<{ enabled: boolean; onToggle: () => void }>) {
  return (
    <button
      type="button"
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
  )
}

const inputCls =
  'w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500'

export function Alerts() {
  const { alerts, updateAlerts } = useHermes()
  const [draft, setDraft] = useState<AlertConfig | null>(null)
  const [saved, setSaved] = useState(false)
  const [testStatus, setTestStatus] = useState<TestAlertStatus>('idle')
  const [testMessage, setTestMessage] = useState('')

  useEffect(() => {
    if (alerts && !draft) setDraft({ ...alerts })
  }, [alerts, draft])

  if (!draft) {
    return (
      <div className="text-slate-500 text-sm py-10 text-center">
        Loading alert configuration…
      </div>
    )
  }

  const handleSave = async () => {
    await updateAlerts(draft)
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const handleTestAlerts = () => sendTestAlerts(setTestStatus, setTestMessage)

  const patchProvider = <K extends keyof AlertConfig['providers']>(
    key: K,
    patch: Partial<AlertConfig['providers'][K]>
  ) => {
    setDraft((d) =>
      d
        ? {
            ...d,
            providers: {
              ...d.providers,
              [key]: { ...d.providers[key], ...patch },
            },
          }
        : d
    )
  }

  const saveButtonClass = saved
    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
    : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-500/20'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-3xl space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Alert Settings</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
          Configure notifications when speed tests fail. Providers can also be set via environment variables (restart required).
        </p>
      </div>

      {/* Alerts master toggle */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell size={18} className="text-orange-400" />
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">Alerts Enabled</h2>
          </div>
          <button
            type="button"
            onClick={() => setDraft((d) => (d ? { ...d, enabled: !d.enabled } : d))}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              draft.enabled ? 'bg-orange-500' : 'bg-slate-300 dark:bg-slate-700'
            }`}
            aria-pressed={draft.enabled}
          >
            <span
              className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                draft.enabled ? 'translate-x-5' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Get notified when speed tests fail consecutively. Toggle off to silence all alerts without losing your configuration.
        </p>
      </div>

      {/* Thresholds */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">Thresholds</h2>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="failure-threshold"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
            >
              Failure Threshold
            </label>
            <input
              id="failure-threshold"
              type="number"
              min={1}
              max={100}
              value={draft.failure_threshold}
              onChange={(e) =>
                setDraft((d) =>
                  d
                    ? {
                        ...d,
                        failure_threshold: Math.max(1, Number.parseInt(e.target.value, 10) || 3),
                      }
                    : d
                )
              }
              className={inputCls}
            />
            <p className="text-xs text-slate-500 mt-1">Alert after N consecutive failures</p>
          </div>
          <div>
            <label
              htmlFor="cooldown-minutes"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
            >
              Cooldown Period (minutes)
            </label>
            <input
              id="cooldown-minutes"
              type="number"
              min={0}
              max={1440}
              value={draft.cooldown_minutes}
              onChange={(e) =>
                setDraft((d) =>
                  d
                    ? {
                        ...d,
                        cooldown_minutes: Math.max(0, Number.parseInt(e.target.value, 10) || 60),
                      }
                    : d
                )
              }
              className={inputCls}
            />
            <p className="text-xs text-slate-500 mt-1">Time between repeated alerts</p>
          </div>
        </div>
      </div>

      {/* Providers */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">Notification Providers</h2>

        {/* Webhook */}
        <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">Webhook</h3>
            <ProviderToggle
              enabled={draft.providers.webhook.enabled}
              onToggle={() => patchProvider('webhook', { enabled: !draft.providers.webhook.enabled })}
            />
          </div>
          {draft.providers.webhook.enabled && (
            <input
              type="url"
              placeholder="https://webhook.example.com/alerts"
              value={draft.providers.webhook.url}
              onChange={(e) => patchProvider('webhook', { url: e.target.value })}
              className={inputCls}
            />
          )}
        </div>

        {/* Gotify */}
        <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">Gotify</h3>
            <ProviderToggle
              enabled={draft.providers.gotify.enabled}
              onToggle={() => patchProvider('gotify', { enabled: !draft.providers.gotify.enabled })}
            />
          </div>
          {draft.providers.gotify.enabled && (
            <div className="space-y-2">
              <input
                type="url"
                placeholder="https://gotify.example.com"
                value={draft.providers.gotify.url}
                onChange={(e) => patchProvider('gotify', { url: e.target.value })}
                className={inputCls}
              />
              <input
                type="password"
                placeholder="App token"
                value={draft.providers.gotify.token}
                onChange={(e) => patchProvider('gotify', { token: e.target.value })}
                className={inputCls}
              />
            </div>
          )}
        </div>

        {/* ntfy */}
        <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">ntfy</h3>
            <ProviderToggle
              enabled={draft.providers.ntfy.enabled}
              onToggle={() => patchProvider('ntfy', { enabled: !draft.providers.ntfy.enabled })}
            />
          </div>
          {draft.providers.ntfy.enabled && (
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Topic name"
                value={draft.providers.ntfy.topic}
                onChange={(e) => patchProvider('ntfy', { topic: e.target.value })}
                className={inputCls}
              />
              <input
                type="password"
                placeholder="Access token (optional)"
                value={draft.providers.ntfy.token}
                onChange={(e) => patchProvider('ntfy', { token: e.target.value })}
                className={inputCls}
              />
              <input
                type="url"
                placeholder="https://ntfy.sh (optional)"
                value={draft.providers.ntfy.url}
                onChange={(e) => patchProvider('ntfy', { url: e.target.value })}
                className={inputCls}
              />
            </div>
          )}
        </div>

        {/* Apprise */}
        <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Apprise</span>
              <p className="text-xs text-slate-500 mt-0.5">100+ services (Discord, Telegram, Slack, etc.)</p>
            </div>
            <ProviderToggle
              enabled={draft.providers.apprise.enabled}
              onToggle={() => patchProvider('apprise', { enabled: !draft.providers.apprise.enabled })}
            />
          </div>
          {draft.providers.apprise.enabled && (
            <div className="space-y-2">
              <input
                type="url"
                placeholder="https://apprise.example.com/notify/myconfig"
                value={draft.providers.apprise.url}
                onChange={(e) => patchProvider('apprise', { url: e.target.value })}
                className={inputCls}
              />
              <p className="text-xs text-slate-500">
                Full URL with config ID (e.g., https://apprise.example.com/notify/myconfig) or base URL for stateless mode with service URLs below.
              </p>
              <textarea
                placeholder={
                  'Optional: Service URLs for stateless mode (one per line)\nntfy://ntfy.example.com/topic\ngotify://gotify.example.com/token'
                }
                value={(draft.providers.apprise.urls ?? []).join('\n')}
                onChange={(e) =>
                  patchProvider('apprise', {
                    urls: e.target.value
                      .split('\n')
                      .map((s) => s.trim())
                      .filter((s) => s.length > 0),
                  })
                }
                rows={3}
                className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono"
              />
              <p className="text-xs text-slate-500">
                See{' '}
                <a
                  href="https://github.com/caronc/apprise-api"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cyan-400 hover:underline"
                >
                  Apprise API docs
                </a>
                {' '}for URL format examples.
              </p>
            </div>
          )}
        </div>

        {/* Test Alert Button */}
        <div className="pt-4 border-t border-slate-200/50 dark:border-slate-700/50">
          <button
            onClick={handleTestAlerts}
            disabled={testStatus === 'sending'}
            className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${getTestButtonClassName(testStatus)}`}
          >
            {renderTestButtonContent(testStatus)}
          </button>
          {testMessage && (
            <p
              className={`text-xs mt-2 ${
                testStatus === 'success' ? 'text-emerald-400' : 'text-red-400'
              }`}
            >
              {testMessage}
            </p>
          )}
        </div>
      </div>

      {/* Save */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all ${saveButtonClass}`}
        >
          {saved ? <CheckCircle size={17} /> : <Save size={17} />}
          {saved ? 'Saved' : 'Save Changes'}
        </button>
      </div>
    </motion.div>
  )
}
