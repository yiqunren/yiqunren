import { type FormEvent, useRef, useState } from 'react'

import * as api from './api'

const AUTH_MODE_LABELS: Record<string, string> = { api_key: 'API key', subscription_cli: '訂閱 CLI' }

export function authModeLabel(mode: string): string {
  return AUTH_MODE_LABELS[mode] ?? mode
}

interface Props {
  adapters: api.Adapter[]
  termsNotice: string
  /** null 是新增；有值是修改這位成員（轉接器不能改，FR-1）。 */
  member: api.Member | null
  onSaved: () => void
  onCancel: () => void
  onUnauthorized: () => void
}

export function MemberForm({ adapters, termsNotice, member, onSaved, onCancel, onUnauthorized }: Props) {
  const [adapterCode, setAdapterCode] = useState(member?.adapter ?? adapters[0]?.code ?? '')
  const adapter = adapters.find((item) => item.code === adapterCode)
  const [name, setName] = useState(member?.name ?? '')
  const [authMode, setAuthMode] = useState(member?.auth_mode ?? adapter?.auth_modes[0] ?? '')
  const [model, setModel] = useState(member?.model ?? '')
  const [effort, setEffort] = useState(member?.effort ?? '')
  const [timeout, setTimeoutMinutes] = useState(String(member?.timeout_minutes ?? 15))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // NFR-1：同樣的內容重送要用同一個請求 ID（例如網路中斷後再按一次）；內容改了才換新的。
  const pending = useRef<{ key: string; id: string } | null>(null)

  if (adapter === undefined) {
    return (
      <section className="panel">
        <p role="alert">沒有可用的轉接器，不能設定成員。</p>
        <button type="button" onClick={onCancel}>
          關閉
        </button>
      </section>
    )
  }
  const current = adapter

  function changeAdapter(code: string) {
    const next = adapters.find((item) => item.code === code)
    if (next === undefined) {
      return
    }
    setAdapterCode(code)
    if (!next.auth_modes.includes(authMode)) {
      setAuthMode(next.auth_modes[0] ?? '')
    }
    if (!next.supports_model) {
      setModel('')
    }
    if (!next.supports_effort) {
      setEffort('')
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    const minutes = Number(timeout)
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 60) {
      setError('單回合逾時要填 1 到 60 的整數（分鐘）。')
      return
    }
    const settings: api.MemberSettings = {
      name: name.trim(),
      model: current.supports_model ? model.trim() : '',
      effort: current.supports_effort && effort.trim() !== '' ? effort.trim() : null,
      auth_mode: authMode,
      timeout_minutes: minutes,
    }
    if (settings.name === '') {
      setError('請填顯示名稱。')
      return
    }
    setBusy(true)
    setError(null)
    try {
      if (member === null) {
        const payload = { adapter: current.code, ...settings }
        const key = JSON.stringify(payload)
        if (pending.current?.key !== key) {
          pending.current = { key, id: api.newRequestId() }
        }
        await api.createMember({ request_id: pending.current.id, ...payload })
      } else {
        const changes: api.MemberChanges = {}
        if (settings.name !== member.name) changes.name = settings.name
        if (settings.model !== member.model) changes.model = settings.model
        if (settings.effort !== member.effort) changes.effort = settings.effort
        if (settings.auth_mode !== member.auth_mode) changes.auth_mode = settings.auth_mode
        if (settings.timeout_minutes !== member.timeout_minutes) changes.timeout_minutes = settings.timeout_minutes
        if (Object.keys(changes).length > 0) {
          await api.updateMember(member.id, changes)
        }
      }
      onSaved()
    } catch (failure) {
      if (failure instanceof api.ApiError && failure.status === 401) {
        onUnauthorized()
      } else {
        setError(api.describeError(failure))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h3>{member === null ? '新增成員' : `修改成員：${member.name}`}</h3>
      <form className="member-form" onSubmit={(event) => void submit(event)}>
        <label>
          轉接器
          {member === null ? (
            <select value={adapterCode} onChange={(event) => changeAdapter(event.target.value)}>
              {adapters.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.available ? item.name : `${item.name}（尚未接上）`}
                </option>
              ))}
            </select>
          ) : (
            <input value={current.name} readOnly aria-describedby="adapter-fixed" />
          )}
        </label>
        {member !== null && (
          <p id="adapter-fixed" className="hint">
            轉接器新增後不能改；要換就新增另一位成員。
          </p>
        )}
        {!current.available && (
          <p className="notice">這家的轉接器目前還沒接上：可以先設定成員，但送出回合會失敗。</p>
        )}
        <label>
          顯示名稱
          <input value={name} onChange={(event) => setName(event.target.value)} maxLength={80} required />
        </label>
        <label>
          認證模式
          <select value={authMode} onChange={(event) => setAuthMode(event.target.value)}>
            {current.auth_modes.map((mode) => (
              <option key={mode} value={mode}>
                {authModeLabel(mode)}
              </option>
            ))}
          </select>
        </label>
        {authMode === 'subscription_cli' && <p className="notice">{termsNotice}</p>}
        {current.supports_model && (
          <label>
            模型
            <input
              value={model}
              onChange={(event) => setModel(event.target.value)}
              placeholder="空白表示用該家預設"
              maxLength={100}
              spellCheck={false}
            />
          </label>
        )}
        {current.supports_effort && (
          <label>
            推理強度
            <input
              value={effort}
              onChange={(event) => setEffort(event.target.value)}
              placeholder="空白表示不指定"
              maxLength={20}
              spellCheck={false}
            />
          </label>
        )}
        <label>
          單回合逾時（分鐘）
          <input
            type="number"
            min={1}
            max={60}
            step={1}
            value={timeout}
            onChange={(event) => setTimeoutMinutes(event.target.value)}
            required
          />
        </label>
        <div className="actions">
          <button type="submit" disabled={busy}>
            {member === null ? '新增成員' : '儲存'}
          </button>
          <button type="button" onClick={onCancel} disabled={busy}>
            取消
          </button>
        </div>
      </form>
      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
