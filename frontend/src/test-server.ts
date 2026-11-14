// 測試用的假後端：換掉全域的 fetch，不連任何網路。
import { vi } from 'vitest'

import type { Adapter, ConversationSummary, Member, Turn } from './api'

export interface Call {
  method: string
  path: string
  body: unknown
  headers: Record<string, string>
  credentials: string | undefined
}

export interface Reply {
  status?: number
  body?: unknown
  headers?: Record<string, string>
}

/** 'offline' 表示連不上伺服器。 */
export type Outcome = Reply | 'offline'

export const TERMS = '使用時須遵守該家的服務條款，由擁有者自行負責。'
export const GOOD_CODE = 'ABCD-EFGH'

export const ADAPTERS: Adapter[] = [
  { code: 'codex', name: 'Codex', auth_modes: ['api_key', 'subscription_cli'], supports_model: true, supports_effort: true, budget_modes: [], available: true },
  { code: 'plainbot', name: 'Plain Bot', auth_modes: ['api_key'], supports_model: false, supports_effort: false, budget_modes: [], available: false },
]

export function member(overrides: Partial<Member> = {}): Member {
  return {
    id: '11111111-1111-4111-8111-111111111111',
    adapter: 'codex',
    adapter_name: 'Codex',
    name: '成員一',
    model: '',
    effort: null,
    auth_mode: 'api_key',
    timeout_minutes: 15,
    max_budget_usd: null,
    enabled: true,
    status: 'idle',
    ...overrides,
  }
}

export function turn(overrides: Partial<Turn> = {}): Turn {
  return {
    id: '22222222-2222-4222-8222-222222222222',
    conversation_id: '33333333-3333-4333-8333-333333333333',
    member: '11111111-1111-4111-8111-111111111111',
    member_name: '成員一',
    adapter: 'codex',
    message: '你好',
    state: 'completed',
    error_kind: null,
    reply: '你好，我在。',
    thinking_seconds: null,
    started: 1000,
    finished: 1005,
    ...overrides,
  }
}

/** 測試用的 EventSource：不連網路，由測試決定什麼時候送出事件或斷線。 */
export class FakeEventSource {
  static opened: FakeEventSource[] = []
  readonly url: string
  closed = false
  private readonly listeners = new Map<string, Array<(event: { data?: string }) => void>>()

  constructor(url: string) {
    this.url = url
    FakeEventSource.opened.push(this)
  }

  addEventListener(type: string, listener: (event: { data?: string }) => void): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener])
  }

  close(): void {
    this.closed = true
  }

  /** 送出一個事件；data 會轉成 JSON 文字，和伺服器送的一樣。text 用來送不是 JSON 的內容。 */
  emit(type: string, data?: unknown, text?: string): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener({ data: text ?? JSON.stringify(data ?? {}) })
    }
  }
}

/** 換掉全域的 EventSource；回傳的陣列依序是每一次開啟的連線。 */
export function installEventSource(): FakeEventSource[] {
  FakeEventSource.opened = []
  vi.stubGlobal('EventSource', FakeEventSource)
  return FakeEventSource.opened
}

/** serverTime 回傳伺服器時鐘（秒）；有給的話每個回應都帶 Date 標頭，和真的伺服器一樣。 */
export function installFetch(handler: (call: Call) => Outcome, serverTime?: () => number): Call[] {
  const calls: Call[] = []
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const call: Call = {
      method: init.method ?? 'GET',
      path: String(input),
      body: typeof init.body === 'string' ? JSON.parse(init.body) : undefined,
      headers: { ...(init.headers as Record<string, string> | undefined) },
      credentials: init.credentials,
    }
    calls.push(call)
    const reply = handler(call)
    if (reply === 'offline') {
      throw new TypeError('fetch failed')
    }
    const status = reply.status ?? 200
    const headers = { ...reply.headers }
    if (serverTime !== undefined) {
      headers.Date = new Date(serverTime() * 1000).toUTCString()
    }
    return new Response(status === 204 ? null : JSON.stringify(reply.body ?? {}), { status, headers })
  })
  return calls
}

interface BackendOptions {
  paired?: boolean
  members?: Member[]
  adapters?: Adapter[]
  turns?: Turn[]
}

/** 行為接近真後端的假後端；override 回傳非 undefined 時優先採用（用來模擬錯誤）。 */
export function fakeBackend(options: BackendOptions = {}) {
  const state = {
    paired: options.paired ?? true,
    members: [...(options.members ?? [])],
    adapters: options.adapters ?? ADAPTERS,
    turns: [...(options.turns ?? [])],
    now: 2000, // 假後端的時鐘（秒）
    override: undefined as ((call: Call) => Outcome | undefined) | undefined,
  }
  const calls = installFetch((call) => {
    const forced = state.override?.(call)
    if (forced !== undefined) {
      return forced
    }
    const { method, path } = call
    if (method === 'GET' && path === '/api/session') {
      return { body: { paired: state.paired } }
    }
    if (method === 'POST' && path === '/api/pair') {
      if ((call.body as { code: string }).code !== GOOD_CODE) {
        return { status: 403, body: { detail: '配對碼不對或已失效' } }
      }
      state.paired = true
      return { body: { paired: true } }
    }
    if (method === 'DELETE' && path === '/api/session') {
      state.paired = false
      return { status: 204 }
    }
    if (!state.paired) {
      return { status: 401, body: { detail: '尚未配對' } }
    }
    if (method === 'GET' && path === '/api/adapters') {
      return { body: { adapters: state.adapters, terms_notice: TERMS } }
    }
    if (method === 'GET' && path === '/api/members') {
      return { body: { members: state.members } }
    }
    if (method === 'POST' && path === '/api/members') {
      const body = call.body as Record<string, unknown>
      const adapter = state.adapters.find((item) => item.code === body.adapter)
      const created = member({
        id: String(body.request_id),
        adapter: String(body.adapter),
        adapter_name: adapter?.name ?? null,
        name: String(body.name),
        model: String(body.model),
        effort: (body.effort as string | null) ?? null,
        auth_mode: String(body.auth_mode),
        timeout_minutes: Number(body.timeout_minutes),
        // 沒送時：支援的用預設 1 美元（和真後端一樣）。
        max_budget_usd:
          'max_budget_usd' in body
            ? (body.max_budget_usd as number | null)
            : adapter?.budget_modes.includes(String(body.auth_mode))
              ? 1
              : null,
      })
      state.members.push(created)
      return { status: 201, body: { member: created } }
    }
    const match = /^\/api\/members\/([0-9a-f-]+)$/.exec(path)
    const index = match === null ? -1 : state.members.findIndex((item) => item.id === match[1])
    if (index >= 0 && method === 'PATCH') {
      state.members[index] = { ...state.members[index], ...(call.body as Partial<Member>) }
      return { body: { member: state.members[index] } }
    }
    if (index >= 0 && method === 'DELETE') {
      state.members.splice(index, 1)
      return { status: 204 }
    }
    if (method === 'GET' && path === '/api/conversations') {
      const found = new Map<string, ConversationSummary>()
      for (const item of state.turns) {
        const summary = found.get(item.conversation_id) ?? {
          id: item.conversation_id,
          title: item.message.slice(0, 60),
          turns: 0,
          member: item.member,
          member_name: item.member_name,
          state: item.state,
          updated: item.started,
        }
        found.set(item.conversation_id, {
          ...summary,
          turns: summary.turns + 1,
          member_name: item.member_name,
          state: item.state,
          updated: item.finished ?? item.started,
        })
      }
      return { body: { conversations: [...found.values()].sort((a, b) => b.updated - a.updated) } }
    }
    const conversation = /^\/api\/conversations\/([0-9a-f-]+)$/.exec(path)
    if (conversation !== null) {
      const turns = state.turns.filter((item) => item.conversation_id === conversation[1])
      if (turns.length === 0) {
        return { status: 404, body: { detail: '找不到這段對話' } }
      }
      if (method === 'GET') {
        return { body: { conversation_id: conversation[1], turns } }
      }
      if (method === 'DELETE') {
        if (turns.some((item) => item.state === 'running')) {
          return { status: 409, body: { detail: '這段對話還有進行中的回合，不能刪除' } }
        }
        state.turns = state.turns.filter((item) => item.conversation_id !== conversation[1])
        return { status: 204 }
      }
    }
    if (method === 'POST' && path === '/api/turns') {
      const body = call.body as { request_id: string; conversation_id: string; member: string; text: string }
      const existing = state.turns.find((item) => item.id === body.request_id)
      if (existing !== undefined) {
        return { body: { turn: existing } } // 同一個請求重送：回傳原本的回合
      }
      const sender = state.members.find((item) => item.id === body.member)
      if (sender === undefined) {
        return { status: 422, body: { detail: '找不到這位成員' } }
      }
      if (!sender.enabled) {
        return { status: 409, body: { detail: '這位成員已停用' } }
      }
      const inConversation = state.turns.filter((item) => item.conversation_id === body.conversation_id)
      if (inConversation.some((item) => item.member !== body.member)) {
        return { status: 409, body: { detail: '這段對話屬於另一位成員，請開新對話' } }
      }
      if (inConversation.some((item) => item.state === 'running')) {
        return { status: 409, body: { detail: '這段對話還有進行中的回合' } }
      }
      const created = turn({
        id: body.request_id,
        conversation_id: body.conversation_id,
        member: body.member,
        member_name: sender.name,
        adapter: sender.adapter,
        message: body.text,
        state: 'running',
        reply: null,
        started: state.now,
        finished: null,
      })
      state.turns.push(created)
      return { status: 202, body: { turn: created } }
    }
    const single = /^\/api\/turns\/([0-9a-f-]+)(\/interrupt)?$/.exec(path)
    if (single !== null) {
      const found = state.turns.find((item) => item.id === single[1])
      if (found === undefined) {
        return { status: 404, body: { detail: '找不到這個回合' } }
      }
      if (method === 'GET' && single[2] === undefined) {
        return { body: { turn: found } }
      }
      if (method === 'POST' && single[2] !== undefined) {
        return found.state === 'running'
          ? { status: 202, body: { turn: found } }
          : { status: 409, body: { detail: '回合已經結束', turn: found } }
      }
    }
    return { status: 404, body: { detail: 'Not Found' } }
  }, () => state.now)
  /** 讓假後端裡的回合結束（測試接著自己送 done 事件，或讓畫面去查）。 */
  function finish(turnId: string, outcome: Partial<Turn>): Turn {
    const index = state.turns.findIndex((item) => item.id === turnId)
    state.turns[index] = { ...state.turns[index], finished: state.now + 5, ...outcome }
    return state.turns[index]
  }
  return { state, calls, finish }
}
