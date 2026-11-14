// 後端 API 的呼叫與型別。Cookie 由瀏覽器自動帶上；改變狀態的請求都要帶 CSRF 標頭（NFR-3）。

export interface Adapter {
  code: string
  name: string
  auth_modes: string[]
  supports_model: boolean
  supports_effort: boolean
  /** 伺服器目前有沒有這家的執行者；不代表該家的 CLI 已安裝或已登入。 */
  available: boolean
}

export interface AdapterList {
  adapters: Adapter[]
  /** 選訂閱 CLI 模式時要顯示的提示（FR-1）。 */
  terms_notice: string
}

export type MemberStatus = 'idle' | 'running' | 'needs_review'

export interface Member {
  id: string
  adapter: string
  /** 轉接器已從登記處移除時是 null。 */
  adapter_name: string | null
  name: string
  model: string
  effort: string | null
  auth_mode: string
  timeout_minutes: number
  enabled: boolean
  status: MemberStatus
}

export interface MemberSettings {
  name: string
  model: string
  effort: string | null
  auth_mode: string
  timeout_minutes: number
}

export interface NewMember extends MemberSettings {
  request_id: string
  adapter: string
}

export type MemberChanges = Partial<MemberSettings> & { enabled?: boolean }

/** status 是 0 表示連不上伺服器。 */
export class ApiError extends Error {
  readonly status: number
  readonly detail: string | null
  readonly retryAfter: number | null

  constructor(status: number, detail: string | null, retryAfter: number | null) {
    super(detail ?? `HTTP ${status}`)
    this.status = status
    this.detail = detail
    this.retryAfter = retryAfter
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {}
  if (method !== 'GET') {
    headers['X-Yiqunren-CSRF'] = '1'
  }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  let response: Response
  try {
    response = await fetch(path, {
      method,
      headers,
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, null, null)
  }
  if (response.status === 204) {
    return undefined as T // 沒有內容
  }
  let data: unknown
  try {
    data = await response.json()
  } catch {
    data = null // 不是 JSON（例如中途的代理回了別的內容）
  }
  if (!response.ok) {
    const detail = isRecord(data) && typeof data.detail === 'string' ? data.detail : null
    const seconds = Number(response.headers.get('Retry-After'))
    throw new ApiError(response.status, detail, Number.isFinite(seconds) && seconds > 0 ? seconds : null)
  }
  return data as T
}

/** 把錯誤轉成給擁有者看的一句話；伺服器的說明文字照原樣當純文字顯示。 */
export function describeError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return '發生未預期的錯誤，請重新整理頁面再試。'
  }
  if (error.status === 0) {
    return '連不上伺服器，請確認後端還在執行。'
  }
  if (error.status === 429) {
    return error.retryAfter === null ? '操作太頻繁，請稍後再試。' : `操作太頻繁，請 ${error.retryAfter} 秒後再試。`
  }
  if (error.detail !== null) {
    return error.detail
  }
  if (error.status === 422) {
    return '輸入的內容不合格，請檢查各欄位。'
  }
  if (error.status === 413) {
    return '送出的內容太大。'
  }
  return `伺服器回應錯誤（${error.status}）。`
}

/** NFR-1 的請求 ID：UUID 第 4 版。不用 crypto.randomUUID，因為它在非本機的 HTTP 連線上不能用。 */
export function newRequestId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function getSession(): Promise<{ paired: boolean }> {
  return request('GET', '/api/session')
}

export function pair(code: string): Promise<{ paired: boolean }> {
  return request('POST', '/api/pair', { code })
}

export function logout(): Promise<void> {
  return request('DELETE', '/api/session')
}

export function listAdapters(): Promise<AdapterList> {
  return request('GET', '/api/adapters')
}

export async function listMembers(): Promise<Member[]> {
  const data = await request<{ members: Member[] }>('GET', '/api/members')
  return data.members
}

export async function createMember(member: NewMember): Promise<Member> {
  const data = await request<{ member: Member }>('POST', '/api/members', member)
  return data.member
}

export async function updateMember(id: string, changes: MemberChanges): Promise<Member> {
  const data = await request<{ member: Member }>('PATCH', `/api/members/${encodeURIComponent(id)}`, changes)
  return data.member
}

export function deleteMember(id: string): Promise<void> {
  return request('DELETE', `/api/members/${encodeURIComponent(id)}`)
}
