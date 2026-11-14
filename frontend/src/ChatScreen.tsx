// 私聊畫面（FR-2）：左邊是所有對話的清單，右邊是選中的對話或新對話。
import { useCallback, useEffect, useRef, useState } from 'react'

import * as api from './api'
import { ConversationView } from './ConversationView'

const STATE_LABELS: Record<api.TurnState, string> = {
  running: '執行中',
  completed: '完成',
  failed: '失敗',
  interrupted: '已中斷',
  unknown: '未知',
}

interface Props {
  /** 網址指定的對話；null 表示新對話。 */
  conversationId: string | null
  onOpen: (conversationId: string | null) => void
  onUnauthorized: () => void
}

export function ChatScreen({ conversationId, onOpen, onUnauthorized }: Props) {
  const [members, setMembers] = useState<api.Member[] | null>(null)
  const [conversations, setConversations] = useState<api.ConversationSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  // 新對話的 ID 由前端產生；第一個回合送出後，伺服器上才有這段對話。
  const [draftId, setDraftId] = useState(() => api.newRequestId())
  // 連不上伺服器時的背景重讀；離開畫面時停掉。
  const retry = useRef<{ timer?: number; attempt: number; active: boolean }>({ attempt: 0, active: false })

  const load = useCallback(async () => {
    window.clearTimeout(retry.current.timer)
    try {
      const [memberList, conversationList] = await Promise.all([api.listMembers(), api.listConversations()])
      setMembers(memberList)
      setConversations(conversationList)
      setError(null)
      retry.current.attempt = 0
    } catch (failure) {
      if (failure instanceof api.ApiError && failure.status === 401) {
        onUnauthorized()
        return
      }
      setError(api.describeError(failure))
      if (api.isOffline(failure) && retry.current.active) {
        // 稍後再讀，伺服器恢復後提示自動消失。只讀資料，不重送任何東西。
        window.clearTimeout(retry.current.timer) // 同時有兩次讀取失敗時只留一個
        retry.current.timer = window.setTimeout(() => void load(), api.retryDelay(retry.current.attempt))
        retry.current.attempt += 1
      }
    }
  }, [onUnauthorized])

  useEffect(() => {
    const state = retry.current
    state.active = true
    void load()
    return () => {
      state.active = false
      window.clearTimeout(state.timer)
    }
  }, [load])

  const changed = useCallback(() => {
    void load()
  }, [load])

  const fresh = conversationId === null
  const started = useCallback(
    (id: string) => {
      if (fresh) {
        onOpen(id) // 網址換成這段對話，重新整理後接得回來
        setDraftId(api.newRequestId())
      }
      void load()
    },
    [fresh, onOpen, load],
  )

  const deleted = useCallback(() => {
    onOpen(null)
    void load()
  }, [onOpen, load])

  const selected = conversationId ?? draftId

  return (
    <section>
      <div className="section-header">
        <h2>私聊</h2>
        <div className="actions">
          <button type="button" onClick={() => void load()}>
            重新整理
          </button>
          <button type="button" onClick={() => onOpen(null)} disabled={fresh}>
            新對話
          </button>
        </div>
      </div>
      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="chat">
        <nav className="conversations" aria-label="對話清單">
          {conversations === null && error === null && <p>載入中…</p>}
          {conversations !== null && conversations.length === 0 && <p className="hint">還沒有對話。</p>}
          {conversations !== null && conversations.length > 0 && (
            <ul>
              {conversations.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="conversation-item"
                    aria-current={item.id === conversationId ? 'true' : undefined}
                    onClick={() => onOpen(item.id)}
                  >
                    <span className="conversation-title">{item.title}</span>
                    <span className="hint">
                      {item.member_name ?? '成員'}・<span className={`state-${item.state}`}>{STATE_LABELS[item.state]}</span>・
                      {new Date(item.updated * 1000).toLocaleString()}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>
        <div className="chat-main">
          {members === null ? (
            error === null && <p>載入中…</p>
          ) : (
            <ConversationView
              key={selected}
              conversationId={selected}
              fresh={fresh}
              members={members}
              onChanged={changed}
              onStarted={started}
              onDeleted={deleted}
              onUnauthorized={onUnauthorized}
            />
          )}
        </div>
      </div>
    </section>
  )
}
