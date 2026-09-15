import { useCallback, useEffect, useState } from 'react'
import { PROVIDERS, translations } from './i18n.js'

function Chip({ ok, label }) {
  return (
    <span className={`chip ${ok ? 'chip-ok' : 'chip-todo'}`}>
      {ok ? '✓' : '○'} {label}
    </span>
  )
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  )
}

export default function App() {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'vi')
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState(null)
  const [bot, setBot] = useState({ token: '' })
  const [llm, setLlm] = useState({ provider: 'openai', model: '', api_key: '', base_url: '' })
  const [gcp, setGcp] = useState({ client_id: '', client_secret: '', json: '' })
  const [busy, setBusy] = useState(false)

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
      base_url: data.llm.base_url || prev.base_url,
    }))
  }, [])

  useEffect(() => {
    loadStatus().catch((e) => setMessage({ kind: 'error', text: String(e) }))
  }, [loadStatus])

  async function post(path, body) {
    setMessage(null)
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || res.statusText)
    return data
  }

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
      base_url: preset.baseUrl,
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
      await post('/api/setup/llm', llm)
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

  async function connectGmail() {
    setBusy(true)
    try {
      const { url } = await post('/api/oauth/start', {})
      window.location.href = url
    } catch (e) {
      setMessage({ kind: 'error', text: String(e.message || e) })
      setBusy(false)
    }
  }

  if (!status) return <div className="wrap">{tr('loading')}</div>

  const preset = PROVIDERS[llm.provider] || PROVIDERS.custom

  return (
    <div className="wrap">
      <header>
        <div className="header-row">
          <h1>Chatbot Gmail</h1>
          <div className="lang-switch">
            <button className={lang === 'vi' ? 'active' : ''} onClick={() => switchLang('vi')}>
              VI
            </button>
            <button className={lang === 'en' ? 'active' : ''} onClick={() => switchLang('en')}>
              EN
            </button>
          </div>
        </div>
        <p>{tr('subtitle')}</p>
        <div className="chips">
          <Chip
            ok={status.bot.configured}
            label={`${tr('chip_bot')}${status.bot.username ? ' (@' + status.bot.username + ')' : ''}`}
          />
          <Chip ok={status.llm.configured} label={tr('chip_llm')} />
          <Chip ok={status.gcp.configured} label={tr('chip_gcp')} />
          <Chip
            ok={status.gmail.configured}
            label={`${tr('chip_gmail')}${status.gmail.email ? ' (' + status.gmail.email + ')' : ''}`}
          />
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
        <div className="grid">
          <Field label={tr('provider')}>
            <select value={llm.provider} onChange={(e) => changeProvider(e.target.value)}>
              {Object.entries(PROVIDERS).map(([key, p]) => (
                <option key={key} value={key}>
                  {p.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label={tr('model')}>
            <input
              list="model-options"
              value={llm.model}
              placeholder={preset.models[0] || 'model-name'}
              onChange={(e) => setLlm({ ...llm, model: e.target.value })}
            />
            <datalist id="model-options">
              {preset.models.map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          </Field>
          <Field label={tr('api_key')}>
            <input
              type="password"
              value={llm.api_key}
              placeholder="sk-..."
              onChange={(e) => setLlm({ ...llm, api_key: e.target.value })}
            />
          </Field>
          <Field label={tr('base_url')}>
            <input
              value={llm.base_url}
              placeholder="https://api.openai.com/v1"
              onChange={(e) => setLlm({ ...llm, base_url: e.target.value })}
            />
          </Field>
        </div>
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
        <button onClick={connectGmail} disabled={busy || !status.gcp.configured}>
          {busy ? tr('connecting') : tr('connect')}
        </button>
        {!status.gcp.configured && <p className="hint warn">{tr('need_gcp')}</p>}
      </section>

      {status.all_done && <div className="notice ok">{tr('all_done')}</div>}
    </div>
  )
}
