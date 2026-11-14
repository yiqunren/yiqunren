// 一段私聊對話（FR-2）：歷史回合、進行中回合的狀態與中斷、送出新訊息、刪除整段對話。
import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react'

import * as api from './api'
import { Markdown } from './Markdown'
import { type TurnPhase, watchTurn } from './turn-events'

// 失敗的固定分類（後端只會給這幾種）；不顯示原始錯誤全文。
const ERROR_LABELS: Record<string, string> = {
  auth_failed: '認證失敗（請確認啟動後端時設定的 API key 有效）',
  quota_exceeded: '額度不足（該家帳戶的額度或餘額不夠）',
  service_busy: '該家服務忙碌（太頻繁或暫時出錯，稍後再試）',
  model_unavailable: '模型不存在或不支援（請檢查成員設定的模型名稱）',
  refused: '模型拒絕回答',
  budget_exceeded: '超過花費上限（這位成員的單回合花費上限不夠，回覆沒有保存）',
  timeout: '逾時（超過這位成員的單回合時間上限）',
  reply_too_long: '回覆過長（超過長度上限，回覆沒有保存）',
  internal_error: '內部錯誤',
}

// FR-2：轉接器回報階段時顯示「思考中」「回答中」，沒回報時是「執行中」。
const PHASE_LABELS: Record<TurnPhase | 'running', string> = {
  running: '執行中…',
  thinking: '思考中…',
  answering: '回答中…',
}

function thinkingLabel(seconds: number): string {
  return seconds < 1 ? '思考了不到 1 秒' : `思考了 ${Math.round(seconds)} 秒`
}

function upsert(turns: api.Turn[], turn: api.Turn): api.Turn[] {
  return turns.some((item) => item.id === turn.id)
    ? turns.map((item) => (item.id === turn.id ? turn : item))
    : [...turns, turn]
}

function Elapsed({ since }: { since: number }) {
  const [now, setNow] = useState(() => api.serverNow())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(api.serverNow()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const seconds = Math.max(0, Math.floor(now - since))
  return (
    <span>
      {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}
    </span>
  )
}

interface Props {
  conversationId: string
  /** 還沒送出第一個回合的新對話：伺服器上還沒有它，要先選成員。 */
  fresh: boolean
  members: api.Member[]
  /** 回合開始或結束、對話內容有變時通知上層更新清單。 */
  onChanged: () => void
  /** 第一個回合送出成功。 */
  onStarted: (conversationId: string) => void
  onDeleted: () => void
  onUnauthorized: () => void
}

export function ConversationView({ conversationId, fresh, members, onChanged, onStarted, onDeleted, onUnauthorized }: Props) {
  // null：還在載入。
  const [turns, setTurns] = useState<api.Turn[] | null>(fresh ? [] : null)
  const [missing, setMissing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [text, setText] = useState('')
  const [chosen, setChosen] = useState('')
  const [sending, setSending] = useState(false)
  const [interrupting, setInterrupting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  // 中斷要求已送達的回合。
  const [stopping, setStopping] = useState<string | null>(null)
  // 進行中回合最近回報的階段（FR-2）；事件每次連線都從頭重送，重新整理後接得回來。
  const [phase, setPhase] = useState<{ turn: string; phase: TurnPhase } | null>(null)
  const [reconnecting, setReconnecting] = useState(false)
  // 送出中的請求：同樣內容重送沿用同一個請求 ID（NFR-1），內容改了才換新的。
  const pending = useRef<{ key: string; id: string } | null>(null)
  const bottom = useRef<HTMLDivElement | null>(null)

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

  const loaded = turns !== null
  useEffect(() => {
    if (loaded) {
      return
    }
    let cancelled = false
    let timer: number | undefined
    let attempt = 0
    const fetchTurns = () => {
      api.getConversation(conversationId).then(
        (found) => {
          if (!cancelled) {
            setError(null)
            setTurns(found)
          }
        },
        (failure: unknown) => {
          if (cancelled) {
            return
          }
          if (failure instanceof api.ApiError && failure.status === 404) {
            setMissing(true)
            return
          }
          fail(failure)
          if (api.isOffline(failure)) {
            // 連不上伺服器：稍後再讀，恢復後直接顯示對話。只讀資料，不重送任何東西。
            timer = window.setTimeout(fetchTurns, api.retryDelay(attempt))
            attempt += 1
          }
        },
      )
    }
    fetchTurns()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [conversationId, loaded, fail])

  const running = turns?.find((turn) => turn.state === 'running') ?? null
  const runningId = running?.id ?? null

  // 進行中的回合：接事件，等它結束。連線斷了先查回合狀態，還在跑就稍後重連。
  useEffect(() => {
    if (runningId === null) {
      return
    }
    let cancelled = false
    let close = () => {}
    let timer: number | undefined
    let attempt = 0

    const settle = (turn: api.Turn) => {
      setTurns((current) => upsert(current ?? [], turn))
      setReconnecting(false)
      onChanged()
    }

    const connect = () => {
      close = watchTurn(runningId, {
        onOpen: () => {
          attempt = 0
          setReconnecting(false)
        },
        onPhase: (next) => setPhase({ turn: runningId, phase: next }),
        onStopping: () => setStopping(runningId),
        onDone: (done) => {
          setTurns((current) =>
            (current ?? []).map((turn) => (turn.id === runningId ? { ...turn, ...done, finished: api.serverNow() } : turn)),
          )
          setReconnecting(false)
          onChanged()
        },
        onError: () => void recover(),
      })
    }

    const recover = async () => {
      try {
        const turn = await api.getTurn(runningId)
        if (cancelled) {
          return
        }
        if (turn.state !== 'running') {
          settle(turn)
          return
        }
      } catch (failure) {
        if (cancelled) {
          return
        }
        if (failure instanceof api.ApiError && failure.status === 401) {
          onUnauthorized()
          return
        }
        if (failure instanceof api.ApiError && failure.status === 404) {
          setMissing(true) // 對話在別處被刪掉了
          onChanged()
          return
        }
        // 連不上伺服器或暫時性的錯誤：稍後再試。
      }
      setReconnecting(true)
      timer = window.setTimeout(connect, api.retryDelay(attempt)) // 事件連線斷掉後稍後再連
      attempt += 1
    }

    connect()
    return () => {
      cancelled = true
      close()
      window.clearTimeout(timer)
    }
  }, [runningId, onChanged, onUnauthorized])

  const count = turns?.length ?? 0
  const lastState = turns?.[count - 1]?.state
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: 'end' })
  }, [count, lastState])

  if (missing) {
    return <p role="alert">找不到這段對話，可能已經被刪除。</p>
  }
  if (turns === null) {
    return error === null ? <p>載入中…</p> : <p className="error" role="alert">{error}</p>
  }

  // 一段對話只屬於一位成員：有回合之後就固定是第一個回合的成員。
  const choices = members.filter((member) => member.enabled)
  const memberId = turns[0]?.member ?? (chosen !== '' ? chosen : (choices[0]?.id ?? ''))
  const member = members.find((item) => item.id === memberId)
  const memberName = member?.name ?? turns[turns.length - 1]?.member_name ?? '成員'
  const removed = turns.length > 0 && member === undefined

  let blocked: string | null = null
  if (removed) {
    blocked = '這位成員已被刪除，這段對話只能看與刪除，不能續問。'
  } else if (member !== undefined && !member.enabled) {
    blocked = '這位成員已停用，啟用後才能續問。'
  } else if (member === undefined) {
    blocked = '還沒有可用的成員，請先到「成員」新增或啟用一位。'
  }

  async function send(event?: FormEvent) {
    event?.preventDefault()
    if (member === undefined || blocked !== null || sending || running !== null || text.trim() === '') {
      return
    }
    const key = JSON.stringify([conversationId, member.id, text])
    if (pending.current?.key !== key) {
      pending.current = { key, id: api.newRequestId() }
    }
    setSending(true)
    setError(null)
    try {
      const turn = await api.startTurn({
        request_id: pending.current.id,
        conversation_id: conversationId,
        member: member.id,
        text,
      })
      pending.current = null
      setText('')
      setTurns((current) => upsert(current ?? [], turn))
      onStarted(conversationId)
    } catch (failure) {
      if (failure instanceof api.ApiError && failure.status === 410) {
        pending.current = null // 那個請求所屬的對話已被刪除；再送就是新的請求
      }
      fail(failure)
    } finally {
      setSending(false)
    }
  }

  function sendOnShortcut(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter 留給換行與輸入法選字；Ctrl 或 ⌘ 加 Enter 才送出。
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      void send()
    }
  }

  async function interrupt(turn: api.Turn) {
    setInterrupting(true)
    setError(null)
    try {
      await api.interruptTurn(turn.id)
      setStopping(turn.id) // 要求已送達；結果（已中斷或未知）由回合事件告知
    } catch (failure) {
      if (failure instanceof api.ApiError && failure.status === 409) {
        // 回合剛好已經結束：直接讀結果。
        try {
          const latest = await api.getTurn(turn.id)
          setTurns((current) => upsert(current ?? [], latest))
          onChanged()
        } catch (inner) {
          fail(inner)
        }
      } else {
        fail(failure)
      }
    } finally {
      setInterrupting(false)
    }
  }

  async function remove() {
    if (!window.confirm('刪除這段對話？訊息、回覆與回合紀錄會一併刪掉，無法復原。')) {
      return
    }
    setDeleting(true)
    setError(null)
    try {
      await api.deleteConversation(conversationId)
      onDeleted()
    } catch (failure) {
      fail(failure)
      setDeleting(false)
    }
  }

  return (
    <div className="conversation">
      <div className="section-header">
        <h3>
          {turns.length === 0 ? '新對話' : `和「${memberName}」的對話`}
          {removed && <span className="tag">成員已刪除</span>}
        </h3>
        {turns.length > 0 && (
          <button
            type="button"
            onClick={() => void remove()}
            disabled={deleting || running !== null}
            title={running !== null ? '還有進行中的回合，不能刪除' : undefined}
          >
            刪除這段對話
          </button>
        )}
      </div>

      {turns.map((turn) => (
        <article key={turn.id} className="turn">
          <div className="bubble owner">
            <div className="who">你</div>
            <div className="plain">{turn.message}</div>
          </div>
          <div className="bubble member">
            <div className="who">{turn.member_name ?? memberName}</div>
            {turn.state === 'running' && (
              <div className="running">
                <p role="status">
                  {stopping === turn.id
                    ? '中斷中，等成員的程序停止…'
                    : PHASE_LABELS[phase?.turn === turn.id ? phase.phase : 'running']}{' '}
                  已經過 <Elapsed since={turn.started} />
                </p>
                {reconnecting && <p className="hint">和伺服器的連線中斷，重新連線中…</p>}
                <button type="button" onClick={() => void interrupt(turn)} disabled={interrupting || stopping === turn.id}>
                  中斷
                </button>
              </div>
            )}
            {turn.state === 'completed' && typeof turn.thinking_seconds === 'number' && (
              <p className="hint thinking">{thinkingLabel(turn.thinking_seconds)}</p>
            )}
            {turn.state === 'completed' && <Markdown text={turn.reply ?? ''} />}
            {turn.state === 'failed' && (
              <p className="outcome outcome-failed">
                失敗：{ERROR_LABELS[turn.error_kind ?? ''] ?? '其他錯誤'}。不會自動重試，要不要重送由你決定。
              </p>
            )}
            {turn.state === 'interrupted' && <p className="outcome">已中斷。成員的程序已經停止。</p>}
            {turn.state === 'unknown' && (
              <p className="outcome outcome-unknown">
                未知：無法確認這個回合的結果，或成員的程序是否已經停止。請自行核對後再決定要不要重送；不會自動重試。
              </p>
            )}
          </div>
        </article>
      ))}
      <div ref={bottom} />

      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {blocked !== null ? (
        <p className="notice">{blocked}</p>
      ) : (
        <form className="composer" onSubmit={(event) => void send(event)}>
          {turns.length === 0 && (
            <label>
              成員
              <select value={memberId} onChange={(event) => setChosen(event.target.value)}>
                {choices.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}（{item.adapter_name ?? item.adapter}）
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            訊息
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              onKeyDown={sendOnShortcut}
              rows={4}
              maxLength={api.MAX_MESSAGE_CHARS}
            />
          </label>
          <div className="actions">
            <button type="submit" disabled={sending || running !== null || text.trim() === ''}>
              送出
            </button>
            <span className="hint">
              {running !== null ? '上一個回合還沒結束，結束後才能送出。' : 'Ctrl＋Enter 也可以送出。'}
            </span>
          </div>
        </form>
      )}
    </div>
  )
}
