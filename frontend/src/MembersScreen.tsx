import { useCallback, useEffect, useRef, useState } from 'react'

import * as api from './api'
import { authModeLabel, MemberForm } from './MemberForm'

// FR-1：閒置、執行中、需要人核對。
const STATUS_LABELS: Record<api.MemberStatus, string> = {
  idle: '閒置',
  running: '執行中',
  needs_review: '需要人核對',
}

// FR-1：單回合花費上限；轉接器在這種認證模式下不支援時顯示「不適用」。
function budgetLabel(member: api.Member, adapter: api.Adapter | undefined): string {
  if (member.max_budget_usd !== null) {
    return `US$${member.max_budget_usd.toFixed(2)}`
  }
  return adapter?.budget_modes.includes(member.auth_mode) ? '不設上限' : '不適用'
}

export function MembersScreen({ onUnauthorized }: { onUnauthorized: () => void }) {
  const [adapters, setAdapters] = useState<api.AdapterList | null>(null)
  const [members, setMembers] = useState<api.Member[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  // null：沒開表單；member 是 null：新增；有值：修改那位成員。
  const [form, setForm] = useState<{ member: api.Member | null } | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const fail = useCallback(
    (failure: unknown) => {
      if (failure instanceof api.ApiError && failure.status === 401) {
        onUnauthorized()
      } else {
        setError(api.describeError(failure))
      }
    },
    [onUnauthorized],
  )

  // 連不上伺服器時的背景重讀；離開畫面時停掉。
  const retry = useRef<{ timer?: number; attempt: number; active: boolean }>({ attempt: 0, active: false })

  const load = useCallback(async () => {
    window.clearTimeout(retry.current.timer)
    try {
      const [adapterList, memberList] = await Promise.all([api.listAdapters(), api.listMembers()])
      setAdapters(adapterList)
      setMembers(memberList)
      setError(null)
      retry.current.attempt = 0
    } catch (failure) {
      fail(failure)
      if (api.isOffline(failure) && retry.current.active) {
        // 稍後再讀，伺服器恢復後提示自動消失。只讀清單，不重做任何操作。
        window.clearTimeout(retry.current.timer) // 同時有兩次讀取失敗時只留一個
        retry.current.timer = window.setTimeout(() => void load(), api.retryDelay(retry.current.attempt))
        retry.current.attempt += 1
      }
    }
  }, [fail])

  useEffect(() => {
    const state = retry.current
    state.active = true
    void load()
    return () => {
      state.active = false
      window.clearTimeout(state.timer)
    }
  }, [load])

  async function act(member: api.Member, action: () => Promise<unknown>) {
    setBusy(member.id)
    try {
      await action()
      await load()
    } catch (failure) {
      fail(failure)
    } finally {
      setBusy(null)
    }
  }

  function remove(member: api.Member) {
    if (window.confirm(`刪除成員「${member.name}」的設定？過去的對話會保留。`)) {
      void act(member, () => api.deleteMember(member.id))
    }
  }

  const registered = (code: string) => adapters?.adapters.find((item) => item.code === code)

  return (
    <section>
      <div className="section-header">
        <h2>成員</h2>
        <div className="actions">
          <button type="button" onClick={() => void load()}>
            重新整理
          </button>
          <button type="button" onClick={() => setForm({ member: null })} disabled={adapters === null}>
            新增成員
          </button>
        </div>
      </div>
      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {form !== null && adapters !== null && (
        <MemberForm
          key={form.member?.id ?? 'new'}
          adapters={adapters.adapters}
          termsNotice={adapters.terms_notice}
          member={form.member}
          onSaved={() => {
            setForm(null)
            void load()
          }}
          onCancel={() => setForm(null)}
          onUnauthorized={onUnauthorized}
        />
      )}
      {members === null && error === null && <p>載入中…</p>}
      {members !== null && members.length === 0 && <p>還沒有成員。按「新增成員」設定第一位。</p>}
      {members !== null && members.length > 0 && (
        <table className="members">
          <thead>
            <tr>
              <th>名稱</th>
              <th>轉接器</th>
              <th>模型</th>
              <th>推理強度</th>
              <th>認證模式</th>
              <th>逾時</th>
              <th>花費上限</th>
              <th>狀態</th>
              <th>動作</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => {
              const adapter = registered(member.adapter)
              return (
                <tr key={member.id} className={member.enabled ? undefined : 'disabled'}>
                  <td>{member.name}</td>
                  <td>
                    {member.adapter_name ?? `${member.adapter}（轉接器已移除）`}
                    {adapter !== undefined && !adapter.available && <span className="tag">未接上</span>}
                  </td>
                  <td>{member.model === '' ? '預設' : member.model}</td>
                  <td>{member.effort ?? '不指定'}</td>
                  <td>{authModeLabel(member.auth_mode)}</td>
                  <td>{member.timeout_minutes} 分鐘</td>
                  <td>{budgetLabel(member, adapter)}</td>
                  <td>
                    <span className={`status status-${member.status}`}>{STATUS_LABELS[member.status]}</span>
                    {!member.enabled && <span className="tag">已停用</span>}
                  </td>
                  <td className="actions">
                    <button
                      type="button"
                      onClick={() => setForm({ member })}
                      disabled={busy === member.id || adapter === undefined}
                      title={adapter === undefined ? '這個轉接器已經不在登記處，設定不能修改' : undefined}
                    >
                      修改
                    </button>
                    <button
                      type="button"
                      onClick={() => void act(member, () => api.updateMember(member.id, { enabled: !member.enabled }))}
                      disabled={busy === member.id}
                    >
                      {member.enabled ? '停用' : '啟用'}
                    </button>
                    <button type="button" onClick={() => remove(member)} disabled={busy === member.id}>
                      刪除
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </section>
  )
}
