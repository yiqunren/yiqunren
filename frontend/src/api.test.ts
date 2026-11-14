import { describe, expect, it } from 'vitest'

import * as api from './api'
import { installFetch, member } from './test-server'

describe('請求 ID', () => {
  it('是 UUID 第 4 版，而且每次不同', () => {
    const ids = Array.from({ length: 200 }, () => api.newRequestId())
    for (const id of ids) {
      expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
    }
    expect(new Set(ids).size).toBe(ids.length)
  })
})

describe('呼叫後端', () => {
  it('只有改變狀態的請求帶 CSRF 標頭，而且只對同源帶 Cookie', async () => {
    const calls = installFetch((call) =>
      call.method === 'DELETE' ? { status: 204 } : { body: { paired: true, members: [], member: member(), adapters: [] } },
    )
    await api.getSession()
    await api.listMembers()
    await api.pair('ABCD-EFGH')
    await api.updateMember('m1', { enabled: false })
    await api.deleteMember('m1')
    await api.logout()
    expect(calls.map((call) => [call.method, call.path, call.headers['X-Yiqunren-CSRF']])).toEqual([
      ['GET', '/api/session', undefined],
      ['GET', '/api/members', undefined],
      ['POST', '/api/pair', '1'],
      ['PATCH', '/api/members/m1', '1'],
      ['DELETE', '/api/members/m1', '1'],
      ['DELETE', '/api/session', '1'],
    ])
    expect(calls.every((call) => call.credentials === 'same-origin')).toBe(true)
    expect(calls[2].body).toEqual({ code: 'ABCD-EFGH' })
    expect(calls[2].headers['Content-Type']).toBe('application/json')
    expect(calls[0].headers['Content-Type']).toBeUndefined()
  })

  it('沒有內容的回應（204）不當成錯誤', async () => {
    installFetch(() => ({ status: 204 }))
    await expect(api.deleteMember('m1')).resolves.toBeUndefined()
  })

  it('把各種失敗轉成看得懂的一句話', async () => {
    const cases: Array<[Parameters<typeof installFetch>[0], number, string]> = [
      [() => ({ status: 409, body: { detail: '這位成員還有進行中的回合' } }), 409, '這位成員還有進行中的回合'],
      [() => ({ status: 422, body: { detail: [{ loc: ['body', 'name'], msg: 'bad' }] } }), 422, '輸入的內容不合格，請檢查各欄位。'],
      [() => ({ status: 429, body: { detail: '請求太頻繁' }, headers: { 'Retry-After': '12' } }), 429, '操作太頻繁，請 12 秒後再試。'],
      [() => ({ status: 429, body: {} }), 429, '操作太頻繁，請稍後再試。'],
      [() => ({ status: 413, body: {} }), 413, '送出的內容太大。'],
      [() => ({ status: 500, body: {} }), 500, '伺服器回應錯誤（500）。'],
      [() => 'offline', 0, '連不上伺服器，請確認後端還在執行。'],
    ]
    for (const [handler, status, message] of cases) {
      installFetch(handler)
      const failure = await api.listMembers().catch((error: unknown) => error)
      expect(failure).toBeInstanceOf(api.ApiError)
      expect((failure as api.ApiError).status).toBe(status)
      expect(api.describeError(failure)).toBe(message)
    }
    expect(api.describeError(new Error('other'))).toBe('發生未預期的錯誤，請重新整理頁面再試。')
  })
})
