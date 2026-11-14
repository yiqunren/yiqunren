// 測試用的假後端：換掉全域的 fetch，不連任何網路。
import { vi } from 'vitest'

import type { Adapter, Member } from './api'

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
  { code: 'codex', name: 'Codex', auth_modes: ['api_key', 'subscription_cli'], supports_model: true, supports_effort: true, available: true },
  { code: 'plainbot', name: 'Plain Bot', auth_modes: ['api_key'], supports_model: false, supports_effort: false, available: false },
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
    enabled: true,
    status: 'idle',
    ...overrides,
  }
}

export function installFetch(handler: (call: Call) => Outcome): Call[] {
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
    return new Response(status === 204 ? null : JSON.stringify(reply.body ?? {}), { status, headers: reply.headers })
  })
  return calls
}

interface BackendOptions {
  paired?: boolean
  members?: Member[]
  adapters?: Adapter[]
}

/** 行為接近真後端的假後端；override 回傳非 undefined 時優先採用（用來模擬錯誤）。 */
export function fakeBackend(options: BackendOptions = {}) {
  const state = {
    paired: options.paired ?? true,
    members: [...(options.members ?? [])],
    adapters: options.adapters ?? ADAPTERS,
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
    return { status: 404, body: { detail: 'Not Found' } }
  })
  return { state, calls }
}
