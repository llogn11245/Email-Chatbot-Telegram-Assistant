import { useCallback, useEffect, useRef, useState } from 'react'
import { PROVIDERS, translations } from './i18n.js'

function Chip({ ok, label }) {
  return (
    <span className={`chip ${ok ? 'chip-ok' : 'chip-todo'}`}>
      {ok ? '✓' : '○'} {label}
    </span>
  )
}

function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <small className="field-hint">{hint}</small>}
    </label>
  )
}

function AccountRow({ account, tr, onSetDefault, onRemove, onRename }) {
  const [label, setLabel] = useState(account.label || '')
  useEffect(() => setLabel(account.label || ''), [account.label])
  return (
    <div className="account-row">
      <div className="account-main">
        <input
          className="account-label"
          value={label}
          placeholder={tr('label_placeholder')}
          onChange={(e) => setLabel(e.target.value)}
          onBlur={() => {
            if (label.trim() !== (account.label || '')) onRename(account.id, label.trim())
          }}
        />
        <span className="account-email">{account.email}</span>
      </div>
      <div className="account-actions">
        {account.is_default ? (
          <span className="badge-default">{tr('account_default')}</span>
        ) : (
          <button type="button" className="ghost" onClick={() => onSetDefault(account.id)}>
            {tr('set_default')}
          </button>
        )}
        <button type="button" className="ghost danger" onClick={() => onRemove(account.id)}>
          {tr('remove')}
        </button>
      </div>
    </div>
  )
}

function num(value, fallback) {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function LogsPanel({ tr }) {
  const [lines, setLines] = useState(null)
  const [level, setLevel] = useState('')
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: '300' })
      if (level) params.set('level', level)
      const res = await fetch('/api/logs?' + params.toString())
      const data = await res.json()
      setLines(data.lines || [])
    } catch (e) {
      setLines([String(e)])
    } finally {
      setLoading(false)
    }
  }, [level])

  return (
    <section>
      <h2>{tr('logs_title')}</h2>
      <p className="hint">{tr('logs_hint')}</p>
      <div className="logs-controls">
        <select value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="">{tr('logs_all')}</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>
        <button type="button" onClick={load} disabled={loading}>
          {loading ? '...' : tr('logs_refresh')}
        </button>
      </div>
      {lines &&
        (lines.length ? (
          <pre className="logs">{lines.join('\n')}</pre>
        ) : (
          <p className="hint">{tr('logs_empty')}</p>
        ))}
    </section>
  )
}

export default function App() {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'vi')
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState(null)
  const [bot, setBot] = useState({ token: '' })
  const [llm, setLlm] = useState({
    provider: 'openai',
    model: '',
    api_key: '',
    temperature: '0.2',
    timeout: '30',
    max_tokens: '1000',
    max_retries: '2',
  })
  const [gcp, setGcp] = useState({ client_id: '', client_secret: '', json: '' })
  const [busy, setBusy] = useState(false)
  const [awaitingAccount, setAwaitingAccount] = useState(false)
  const accountCountRef = useRef(0)

  const tr = useCallback((key) => translations[lang][key] || key, [lang])

  const loadStatus = useCallback(async () => {
    const res = await fetch('/api/status')
    const data = await res.json()
    setStatus(data)
    if (!localStorage.getItem('lang') && data.ui_language) {
      setLang(data.ui_language)
    }
    setLlm((prev) => ({
      ...prev,
      provider: data.llm.provider || prev.provider || 'openai',
      model: data.llm.model || prev.model,
      temperature: data.llm.temperature || prev.temperature,
      timeout: data.llm.timeout || prev.timeout,
      max_tokens: data.llm.max_tokens || prev.max_tokens,
      max_retries: data.llm.max_retries || prev.max_retries,
    }))
  }, [])

  useEffect(() => {
    loadStatus().catch((e) => setMessage({ kind: 'error', text: String(e) }))
  }, [loadStatus])

  useEffect(() => {
    if (!awaitingAccount) return undefined
    let tries = 0
    const id = setInterval(async () => {
      tries += 1
      try {
        const res = await fetch('/api/status')
        const data = await res.json()
        setStatus(data)
        if ((data.gmail.accounts || []).length > accountCountRef.current) {
          setAwaitingAccount(false)
          setMessage({ kind: 'ok', text: tr('account_added') })
        }
      } catch (e) {
        /* ignore */
      }
      if (tries >= 60) setAwaitingAccount(false)
    }, 3000)
    return () => clearInterval(id)
  }, [awaitingAccount, tr])

  async function request(path, method, body) {
    setMessage(null)
    const res = await fetch(path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || res.statusText)
    return data
  }
  const post = (path, body) => request(path, 'POST', body)
  const del = (path) => request(path, 'DELETE')

  function switchLang(next) {
    setLang(next)
    localStorage.setItem('lang', next)
    post('/api/setup/language', { language: next }).catch(() => {})
  }

  function changeProvider(provider) {
    const preset = PROVIDERS[provider]
    setLlm((prev) => ({
      ...prev,
      provider,
      model: preset.models.includes(prev.model) ? prev.model : preset.models[0] || '',
    }))
  }

  async function saveBot() {
    try {
      const data = await post('/api/setup/bot', { bot_token: bot.token })
      setBot({ token: '' })
      if (data.warning) {
        setMessage({ kind: 'error', text: `${tr('bot_saved_offline')} ${data.warning}` })
      } else {
        setMessage({ kind: 'ok', text: `${tr('bot_ok')}: @${data.username || ''}` })
      }
      await loadStatus()
    } catch (e) {
      setMessage({ kind: 'error', text: String(e.message || e) })
    }
  }

  async function saveLlm() {
    try {
      const payload = {
        provider: llm.provider,
        model: llm.model.trim(),
        api_key: llm.api_key,
        temperature: num(llm.temperature, 0.2),
        timeout: num(llm.timeout, 30),
        max_tokens: num(llm.max_tokens, 1000),
        max_retries: num(llm.max_retries, 2),
      }
      await post('/api/setup/llm', payload)
      setMessage({ kind: 'ok', text: tr('llm_saved') })
      await loadStatus()
    } catch (e) {
      setMessage({ kind: 'error', text: String(e.message || e) })
    }
  }

  async function saveGcp() {
    try {
      const payload = { client_id: gcp.client_id, client_secret: gcp.client_secret }
      if (gcp.json.trim()) payload.client_secret_json = gcp.json
      await post('/api/setup/gcp', payload)
      setMessage({ kind: 'ok', text: tr('gcp_saved') })
      setGcp((p) => ({ ...p, json: '' }))
      await loadStatus()
    } catch (e) {
      setMessage({ kind: 'error', text: String(e.message || e) })
    }
  }

  async function addAccount() {
    setBusy(true)
    try {
      accountCountRef.current = (status?.gmail?.accounts || []).length
      await post('/api/oauth/open', {})
      setAwaitingAccount(true)
      setMessage({ kind: 'ok', text: tr('oauth_opened') })
    } catch (e) {
      setMessage({ kind: 'error', text: String(e.message || e) })
    } finally {
      setBusy(false)
    }
  }

  async function setDefaultAccount(id) {
    try {
      await post(`/api/gmail/accounts/${id}/default`, {})
      await loadStatus()
    } catch (e) {
      setMessage({ kind: 'error', text: String(e.message || e) })
    }
  }

  async function renameAccount(id, label) {
    try {
      await post(`/api/gmail/accounts/${id}/label`, { label })
      await loadStatus()
    } catch (e) {
      setMessage({ kind: 'error', text: String(e.message || e) })
    }
  }

  async function removeAccount(id) {
    if (!window.confirm(tr('confirm_remove'))) return
    try {
      await del(`/api/gmail/accounts/${id}`)
      await loadStatus()
    } catch (e) {
      setMessage({ kind: 'error', text: String(e.message || e) })
    }
  }

  if (!status) return <div className="wrap">{tr('loading')}</div>

  const preset = PROVIDERS[llm.provider] || PROVIDERS.openai
  const accounts = status.gmail.accounts || []

  return (
    <div className="wrap">
      <header className="app-header">
        <div className="header-row">
          <div>
            <h1>Chatbot Gmail</h1>
            <p>{tr('subtitle')}</p>
          </div>
          <div className="lang-switch">
            <button className={lang === 'vi' ? 'active' : ''} onClick={() => switchLang('vi')}>
              VI
            </button>
            <button className={lang === 'en' ? 'active' : ''} onClick={() => switchLang('en')}>
              EN
            </button>
          </div>
        </div>
        <div className="chips">
          <Chip
            ok={status.bot.configured}
            label={`${tr('chip_bot')}${status.bot.username ? ' (@' + status.bot.username + ')' : ''}`}
          />
          <Chip ok={status.llm.configured} label={tr('chip_llm')} />
          <Chip ok={status.gcp.configured} label={tr('chip_gcp')} />
          <Chip ok={status.gmail.configured} label={`${tr('chip_gmail')} (${accounts.length})`} />
        </div>
      </header>

      {message && <div className={`notice ${message.kind}`}>{message.text}</div>}

      <section>
        <h2>{tr('step1_title')}</h2>
        <p className="hint">{tr('step1_hint')}</p>
        {status.bot.running && <p className="hint ok-inline">● {tr('bot_connected')}</p>}
        <Field label={tr('bot_token')}>
          <input
            type="password"
            value={bot.token}
            placeholder={tr('bot_token_placeholder')}
            onChange={(e) => setBot({ token: e.target.value })}
          />
        </Field>
        <button onClick={saveBot} disabled={!bot.token.trim()}>
          {tr('save_bot')}
        </button>
      </section>

      <section>
        <h2>{tr('step2_title')}</h2>
        <p className="hint">{tr('step2_hint')}</p>
        <div className="provider-grid">
          {Object.entries(PROVIDERS).map(([key, p]) => (
            <button
              type="button"
              key={key}
              className={`provider-card ${llm.provider === key ? 'active' : ''}`}
              onClick={() => changeProvider(key)}
            >
              <span className="provider-name">{p.label}</span>
            </button>
          ))}
        </div>
        <div className="grid">
          <Field label={tr('model')}>
            <select value={llm.model} onChange={(e) => setLlm({ ...llm, model: e.target.value })}>
              {llm.model && !preset.models.includes(llm.model) && (
                <option value={llm.model}>{llm.model}</option>
              )}
              {preset.models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </Field>
          <Field label={tr('api_key')} hint={tr('api_key_hint')}>
            <input
              type="password"
              value={llm.api_key}
              placeholder="sk-..."
              onChange={(e) => setLlm({ ...llm, api_key: e.target.value })}
            />
          </Field>
        </div>
        <details className="advanced">
          <summary>{tr('advanced')}</summary>
          <div className="grid">
            <Field label={tr('temperature')} hint={tr('temperature_hint')}>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={llm.temperature}
                onChange={(e) => setLlm({ ...llm, temperature: e.target.value })}
              />
            </Field>
            <Field label={tr('timeout')} hint={tr('timeout_hint')}>
              <input
                type="number"
                min="1"
                value={llm.timeout}
                onChange={(e) => setLlm({ ...llm, timeout: e.target.value })}
              />
            </Field>
            <Field label={tr('max_tokens')} hint={tr('max_tokens_hint')}>
              <input
                type="number"
                min="1"
                value={llm.max_tokens}
                onChange={(e) => setLlm({ ...llm, max_tokens: e.target.value })}
              />
            </Field>
            <Field label={tr('max_retries')} hint={tr('max_retries_hint')}>
              <input
                type="number"
                min="0"
                value={llm.max_retries}
                onChange={(e) => setLlm({ ...llm, max_retries: e.target.value })}
              />
            </Field>
          </div>
        </details>
        <button onClick={saveLlm}>{tr('save_llm')}</button>
      </section>

      <section>
        <h2>{tr('step3_title')}</h2>
        <p className="hint">
          {tr('step3_hint_before')}
          <b>{tr('step3_hint_bold')}</b>
          {tr('step3_hint_mid')}
          <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noreferrer">
            console.cloud.google.com/apis/credentials
          </a>
          {tr('step3_hint_after')}
        </p>
        <Field label={tr('paste_json')}>
          <textarea
            rows="5"
            value={gcp.json}
            placeholder='{ "installed": { "client_id": "...", "client_secret": "..." } }'
            onChange={(e) => setGcp({ ...gcp, json: e.target.value })}
          />
        </Field>
        <p className="hint">{tr('or_manual')}</p>
        <div className="grid">
          <Field label={tr('client_id')}>
            <input
              value={gcp.client_id}
              onChange={(e) => setGcp({ ...gcp, client_id: e.target.value })}
            />
          </Field>
          <Field label={tr('client_secret')}>
            <input
              value={gcp.client_secret}
              onChange={(e) => setGcp({ ...gcp, client_secret: e.target.value })}
            />
          </Field>
        </div>
        <button onClick={saveGcp}>{tr('save_gcp')}</button>
      </section>

      <section>
        <h2>{tr('step4_title')}</h2>
        <p className="hint">{tr('step4_hint')}</p>
        {accounts.length === 0 ? (
          <p className="hint">{tr('no_accounts')}</p>
        ) : (
          <div className="account-list">
            {accounts.map((account) => (
              <AccountRow
                key={account.id}
                account={account}
                tr={tr}
                onSetDefault={setDefaultAccount}
                onRename={renameAccount}
                onRemove={removeAccount}
              />
            ))}
          </div>
        )}
        <button onClick={addAccount} disabled={busy || !status.gcp.configured}>
          {busy ? tr('adding_account') : tr('add_account')}
        </button>
        {!status.gcp.configured && <p className="hint warn">{tr('need_gcp')}</p>}
      </section>

      {status.all_done && <div className="notice ok">{tr('all_done')}</div>}

      <LogsPanel tr={tr} />
    </div>
  )
}
