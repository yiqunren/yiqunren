// 回合事件（SSE）。伺服器每次連線都從資料庫從頭重送這個回合的事件，所以重新整理或重新連線後狀態接得回來。
import * as api from './api'

export interface TurnDone {
  state: api.TurnState
  error_kind: string | null
  reply: string | null
}

export interface TurnWatch {
  /** 連上了。 */
  onOpen: () => void
  /** 中斷要求已送達轉接器，等它確認程序停止。 */
  onStopping: () => void
  onDone: (done: TurnDone) => void
  /** 連線斷了、被伺服器拒絕，或收到看不懂的內容。這時連線已經關掉，要不要重連由呼叫者決定。 */
  onError: () => void
}

const FINAL_STATES: readonly string[] = ['completed', 'failed', 'interrupted', 'unknown']

function parseDone(text: unknown): TurnDone | null {
  let data: unknown
  try {
    data = JSON.parse(String(text))
  } catch {
    return null
  }
  if (typeof data !== 'object' || data === null) {
    return null
  }
  const { state, error_kind: errorKind, reply } = data as Record<string, unknown>
  if (typeof state !== 'string' || !FINAL_STATES.includes(state)) {
    return null
  }
  return {
    state: state as api.TurnState,
    error_kind: typeof errorKind === 'string' ? errorKind : null,
    reply: typeof reply === 'string' ? reply : null,
  }
}

/** 開始接收一個回合的事件；回傳的函式用來停止。進度事件的內容各家轉接器不同，這裡不處理。 */
export function watchTurn(turnId: string, watch: TurnWatch): () => void {
  // 同源連線，瀏覽器會自動帶上配對 Cookie；GET 不需要 CSRF 標頭。
  const source = new EventSource(api.turnEventsPath(turnId))
  let active = true
  const close = () => {
    active = false
    source.close()
  }
  source.addEventListener('open', () => {
    if (active) {
      watch.onOpen()
    }
  })
  source.addEventListener('stopping', () => {
    if (active) {
      watch.onStopping()
    }
  })
  source.addEventListener('done', (event) => {
    if (!active) {
      return
    }
    close()
    const done = parseDone((event as MessageEvent).data)
    if (done === null) {
      watch.onError()
    } else {
      watch.onDone(done)
    }
  })
  source.addEventListener('error', () => {
    if (active) {
      close() // 不用瀏覽器內建的自動重連：先查回合狀態，再決定要不要重連。
      watch.onError()
    }
  })
  return close
}
