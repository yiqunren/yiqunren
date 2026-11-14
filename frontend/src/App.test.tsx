import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { App } from './App'
import { fakeBackend, GOOD_CODE, member } from './test-server'

beforeEach(() => {
  window.location.hash = ''
})

function enterCode(code: string) {
  fireEvent.change(screen.getByLabelText('配對碼'), { target: { value: code } })
  fireEvent.click(screen.getByRole('button', { name: '配對' }))
}

describe('配對', () => {
  it('沒配對時顯示配對畫面；配對碼不對時顯示原因，對了才進成員畫面', async () => {
    const { calls } = fakeBackend({ paired: false })
    render(<App />)
    await screen.findByRole('heading', { name: '配對這個瀏覽器' })
    expect(screen.getByText('python -m app.web pair')).toBeTruthy()
    expect(screen.queryByRole('heading', { name: '成員' })).toBeNull()
    expect(screen.queryByRole('button', { name: '登出這個瀏覽器' })).toBeNull()
    // 還沒配對時不去讀任何要配對的資料。
    expect(calls.map((call) => call.path)).toEqual(['/api/session'])

    enterCode('WRNG-CODE')
    expect((await screen.findByRole('alert')).textContent).toBe('配對碼不對或已失效')
    expect(screen.queryByRole('heading', { name: '成員' })).toBeNull()

    enterCode(GOOD_CODE)
    await screen.findByRole('heading', { name: '成員' })
    expect(screen.queryByRole('heading', { name: '配對這個瀏覽器' })).toBeNull()
    await screen.findByText('還沒有成員。按「新增成員」設定第一位。')
    const pairCalls = calls.filter((call) => call.path === '/api/pair')
    expect(pairCalls.map((call) => call.body)).toEqual([{ code: 'WRNG-CODE' }, { code: GOOD_CODE }])
  })

  it('嘗試太頻繁時告知幾秒後再試', async () => {
    const { state } = fakeBackend({ paired: false })
    render(<App />)
    await screen.findByRole('heading', { name: '配對這個瀏覽器' })
    state.override = (call) =>
      call.path === '/api/pair' ? { status: 429, body: { detail: '請求太頻繁' }, headers: { 'Retry-After': '42' } } : undefined
    enterCode(GOOD_CODE)
    expect((await screen.findByRole('alert')).textContent).toBe('操作太頻繁，請 42 秒後再試。')
  })
})

describe('已配對', () => {
  it('直接顯示成員，登出後回到配對畫面', async () => {
    const { calls } = fakeBackend({ members: [member({ name: 'Codex 深度' })] })
    render(<App />)
    await screen.findByText('Codex 深度')
    fireEvent.click(screen.getByRole('button', { name: '登出這個瀏覽器' }))
    await screen.findByRole('heading', { name: '配對這個瀏覽器' })
    expect(screen.queryByText('Codex 深度')).toBeNull()
    const logout = calls.find((call) => call.method === 'DELETE' && call.path === '/api/session')
    expect(logout?.headers['X-Yiqunren-CSRF']).toBe('1')
  })

  it('配對失效時回到配對畫面並說明', async () => {
    const { state } = fakeBackend({ members: [member()] })
    render(<App />)
    await screen.findByText('成員一')
    state.paired = false // 例如在本機執行了 unpair
    fireEvent.click(screen.getByRole('button', { name: '重新整理' }))
    await screen.findByRole('heading', { name: '配對這個瀏覽器' })
    expect(screen.getByRole('status').textContent).toBe('配對已失效，請重新配對。')
    expect(screen.queryByText('成員一')).toBeNull()
  })
})

describe('畫面切換', () => {
  it('成員與私聊用分頁切換，網址跟著換；上一頁回到原本的畫面', async () => {
    fakeBackend({ members: [member()] })
    render(<App />)
    await screen.findByRole('heading', { name: '成員' })
    expect(screen.getByRole('button', { name: '成員' }).getAttribute('aria-current')).toBe('page')
    fireEvent.click(screen.getByRole('button', { name: '私聊' }))
    await screen.findByRole('heading', { name: '私聊' })
    expect(window.location.hash).toBe('#/chat')
    expect(screen.queryByRole('heading', { name: '成員' })).toBeNull()
    expect(screen.getByRole('button', { name: '私聊' }).getAttribute('aria-current')).toBe('page')
    // 瀏覽器的上一頁只會改網址並發出 hashchange。
    window.location.hash = '#/members'
    window.dispatchEvent(new Event('hashchange'))
    await screen.findByRole('heading', { name: '成員' })
    expect(screen.queryByRole('heading', { name: '私聊' })).toBeNull()
  })

  it('看不懂的網址回到成員畫面，不會把它當成對話 ID 去查', async () => {
    const { calls } = fakeBackend({ members: [member()] })
    window.location.hash = '#/chat/../../api/session'
    render(<App />)
    await screen.findByRole('heading', { name: '成員' })
    expect(calls.some((call) => call.path.startsWith('/api/conversations'))).toBe(false)
  })

  it('還沒配對時不顯示分頁', async () => {
    fakeBackend({ paired: false })
    window.location.hash = '#/chat'
    render(<App />)
    await screen.findByRole('heading', { name: '配對這個瀏覽器' })
    expect(screen.queryByRole('button', { name: '私聊' })).toBeNull()
    expect(screen.queryByRole('heading', { name: '私聊' })).toBeNull()
  })
})

describe('連不上伺服器', () => {
  it('顯示說明，重試成功後繼續', async () => {
    const { state } = fakeBackend({ paired: false })
    state.override = () => 'offline'
    render(<App />)
    expect((await screen.findByRole('alert')).textContent).toBe('連不上伺服器，請確認後端還在執行。')
    state.override = undefined
    fireEvent.click(screen.getByRole('button', { name: '重試' }))
    await screen.findByRole('heading', { name: '配對這個瀏覽器' })
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
  })
})
