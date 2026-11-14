import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { MembersScreen } from './MembersScreen'
import { type Call, fakeBackend, member, TERMS } from './test-server'

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
const OFFLINE = '連不上伺服器，請確認後端還在執行。'

function show() {
  const onUnauthorized = vi.fn()
  render(<MembersScreen onUnauthorized={onUnauthorized} />)
  return onUnauthorized
}

function row(name: string) {
  const line = screen.getByText(name).closest('tr')
  if (line === null) {
    throw new Error(`找不到「${name}」那一列`)
  }
  return within(line)
}

function form(): HTMLFormElement {
  const found = screen.getByRole('button', { name: '取消' }).closest('form')
  if (found === null) {
    throw new Error('表單沒有打開')
  }
  return found
}

async function openNewForm() {
  await screen.findByRole('heading', { name: '成員' })
  await waitFor(() => expect(screen.getByRole<HTMLButtonElement>('button', { name: '新增成員' }).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '新增成員' }))
  return form()
}

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

function sent(calls: Call[], method: string) {
  return calls.filter((call) => call.method === method && call.path.startsWith('/api/members'))
}

describe('成員列表', () => {
  it('顯示每位成員的設定與狀態', async () => {
    fakeBackend({
      members: [
        member({ id: 'a1', name: '閒置的', model: 'gpt-x', effort: 'high', auth_mode: 'subscription_cli', timeout_minutes: 30 }),
        member({ id: 'a2', name: '執行中的', status: 'running' }),
        member({ id: 'a3', name: '要核對的', status: 'needs_review', enabled: false }),
        member({ id: 'a4', name: '沒接上的', adapter: 'plainbot', adapter_name: 'Plain Bot' }),
        member({ id: 'a5', name: '孤兒', adapter: 'gone', adapter_name: null }),
      ],
    })
    show()
    await screen.findByText('閒置的')
    for (const text of ['Codex', 'gpt-x', 'high', '訂閱 CLI', '30 分鐘', '閒置']) {
      expect(row('閒置的').getByText(text)).toBeTruthy()
    }
    for (const text of ['執行中', '預設', '不指定', 'API key', '15 分鐘']) {
      expect(row('執行中的').getByText(text)).toBeTruthy()
    }
    expect(row('執行中的').queryByText('已停用')).toBeNull()
    expect(row('執行中的').queryByText('未接上')).toBeNull()
    expect(row('要核對的').getByText('需要人核對')).toBeTruthy()
    expect(row('要核對的').getByText('已停用')).toBeTruthy()
    expect(row('要核對的').getByRole('button', { name: '啟用' })).toBeTruthy()
    expect(row('沒接上的').getByText('未接上')).toBeTruthy()
    expect(row('孤兒').getByText('gone（轉接器已移除）')).toBeTruthy()
    expect(row('孤兒').getByRole<HTMLButtonElement>('button', { name: '修改' }).disabled).toBe(true)
    expect(row('閒置的').getByRole<HTMLButtonElement>('button', { name: '修改' }).disabled).toBe(false)
  })

  it('把名稱與伺服器訊息當純文字顯示，不當成 HTML', async () => {
    const { state } = fakeBackend({ members: [member({ name: '<img src=x onerror=alert(1)>', model: '<b>bold</b>' })] })
    show()
    await screen.findByText('<img src=x onerror=alert(1)>')
    expect(screen.getByText('<b>bold</b>')).toBeTruthy()
    state.override = (call) => (call.method === 'GET' ? { status: 500, body: { detail: '<script>alert(1)</script>' } } : undefined)
    fireEvent.click(screen.getByRole('button', { name: '重新整理' }))
    expect((await screen.findByRole('alert')).textContent).toBe('<script>alert(1)</script>')
    expect(document.querySelector('img, b, script')).toBeNull()
  })

  it('配對失效時通知上層', async () => {
    fakeBackend({ paired: false })
    const onUnauthorized = show()
    await waitFor(() => expect(onUnauthorized).toHaveBeenCalled())
    expect(screen.queryByRole('alert')).toBeNull()
  })
})

describe('新增成員', () => {
  it('欄位跟著轉接器支援的項目變，送出的內容正確', async () => {
    const { calls } = fakeBackend()
    show()
    await openNewForm()
    expect(screen.getByLabelText('模型')).toBeTruthy()
    expect(screen.getByLabelText('推理強度')).toBeTruthy()
    expect(screen.queryByText(TERMS)).toBeNull()
    expect(screen.getByRole('option', { name: 'Plain Bot（尚未接上）' })).toBeTruthy()

    fill('認證模式', 'subscription_cli')
    expect(screen.getByText(TERMS)).toBeTruthy() // FR-1：選訂閱 CLI 要提示服務條款

    fill('轉接器', 'plainbot') // 不支援模型、推理強度，也只有 API key 模式
    expect(screen.queryByLabelText('模型')).toBeNull()
    expect(screen.queryByLabelText('推理強度')).toBeNull()
    expect(screen.queryByText(TERMS)).toBeNull()
    expect(screen.getByLabelText<HTMLSelectElement>('認證模式').value).toBe('api_key')
    expect(screen.getByText('這家的轉接器目前還沒接上：可以先設定成員，但送出回合會失敗。')).toBeTruthy()

    fill('轉接器', 'codex')
    fill('顯示名稱', '  新成員  ')
    fill('模型', 'gpt-5.1')
    fill('認證模式', 'subscription_cli')
    fill('單回合逾時（分鐘）', '30')
    fireEvent.submit(form())

    expect(row((await screen.findByText('新成員')).textContent ?? '').getByText('gpt-5.1')).toBeTruthy()
    expect(screen.queryByRole('button', { name: '取消' })).toBeNull()
    const [post] = sent(calls, 'POST')
    const body = post.body as Record<string, unknown>
    expect(body.request_id).toMatch(UUID)
    expect(body).toEqual({
      request_id: body.request_id,
      adapter: 'codex',
      name: '新成員',
      model: 'gpt-5.1',
      effort: null,
      auth_mode: 'subscription_cli',
      timeout_minutes: 30,
    })
    expect(post.headers['X-Yiqunren-CSRF']).toBe('1')
  })

  it('不支援的欄位不送出值', async () => {
    const { calls } = fakeBackend()
    show()
    await openNewForm()
    fill('模型', 'gpt-5.1')
    fill('推理強度', 'high')
    fill('轉接器', 'plainbot')
    fill('顯示名稱', '簡單的')
    fireEvent.submit(form())
    await screen.findByText('簡單的')
    expect(sent(calls, 'POST')[0].body).toMatchObject({ adapter: 'plainbot', model: '', effort: null, auth_mode: 'api_key' })
  })

  it('同樣的內容重送用同一個請求 ID，內容改了才換新的', async () => {
    const { state, calls } = fakeBackend()
    show()
    await openNewForm()
    fill('顯示名稱', '甲')
    state.override = (call) => (call.method === 'POST' ? 'offline' : undefined)
    fireEvent.submit(form())
    expect((await screen.findByRole('alert')).textContent).toBe(OFFLINE)
    fireEvent.submit(form())
    await waitFor(() => expect(sent(calls, 'POST')).toHaveLength(2))
    expect((await screen.findByRole('alert')).textContent).toBe(OFFLINE)
    state.override = undefined
    fill('顯示名稱', '乙')
    fireEvent.submit(form())
    await screen.findByText('乙')
    const ids = sent(calls, 'POST').map((call) => (call.body as { request_id: string }).request_id)
    expect(ids).toHaveLength(3)
    expect(ids[0]).toMatch(UUID)
    expect(ids[1]).toBe(ids[0])
    expect(ids[2]).not.toBe(ids[0])
    expect(state.members.map((item) => item.name)).toEqual(['乙'])
  })

  it('逾時與名稱不合格時不送出', async () => {
    const { calls } = fakeBackend()
    show()
    await openNewForm()
    fill('顯示名稱', '有名字')
    for (const minutes of ['0', '61', '1.5', '']) {
      fill('單回合逾時（分鐘）', minutes)
      fireEvent.submit(form())
      expect(screen.getByRole('alert').textContent).toBe('單回合逾時要填 1 到 60 的整數（分鐘）。')
    }
    fill('單回合逾時（分鐘）', '60')
    fill('顯示名稱', '   ')
    fireEvent.submit(form())
    expect(screen.getByRole('alert').textContent).toBe('請填顯示名稱。')
    expect(sent(calls, 'POST')).toHaveLength(0)
  })

  it('伺服器拒絕時顯示原因，表單留著', async () => {
    const { state } = fakeBackend()
    show()
    await openNewForm()
    fill('顯示名稱', '被拒絕的')
    state.override = (call) => (call.method === 'POST' ? { status: 422, body: { detail: '這個轉接器不支援這種認證模式' } } : undefined)
    fireEvent.submit(form())
    expect((await screen.findByRole('alert')).textContent).toBe('這個轉接器不支援這種認證模式')
    expect(form()).toBeTruthy()
  })
})

describe('修改、停用與刪除', () => {
  it('只送出有改的欄位；轉接器不能改', async () => {
    const { calls } = fakeBackend({ members: [member({ name: '舊名', model: 'gpt-x', effort: 'high' })] })
    show()
    fireEvent.click(row((await screen.findByText('舊名')).textContent ?? '').getByRole('button', { name: '修改' }))
    const adapter = screen.getByLabelText<HTMLInputElement>('轉接器')
    expect([adapter.tagName, adapter.value, adapter.readOnly]).toEqual(['INPUT', 'Codex', true])
    expect(screen.getByLabelText<HTMLInputElement>('模型').value).toBe('gpt-x')
    fill('顯示名稱', '新名')
    fill('推理強度', '')
    fireEvent.submit(form())
    await screen.findByText('新名')
    expect(sent(calls, 'PATCH').map((call) => call.body)).toEqual([{ name: '新名', effort: null }])
    expect(row('新名').getByText('不指定')).toBeTruthy()

    // 沒有改任何東西就不送請求。
    fireEvent.click(row('新名').getByRole('button', { name: '修改' }))
    fireEvent.submit(form())
    await waitFor(() => expect(screen.queryByRole('button', { name: '取消' })).toBeNull())
    expect(sent(calls, 'PATCH')).toHaveLength(1)
    expect(sent(calls, 'POST')).toHaveLength(0)
  })

  it('停用與啟用', async () => {
    const { calls } = fakeBackend({ members: [member()] })
    show()
    fireEvent.click(row((await screen.findByText('成員一')).textContent ?? '').getByRole('button', { name: '停用' }))
    await waitFor(() => expect(row('成員一').getByText('已停用')).toBeTruthy())
    fireEvent.click(row('成員一').getByRole('button', { name: '啟用' }))
    await waitFor(() => expect(row('成員一').queryByText('已停用')).toBeNull())
    expect(sent(calls, 'PATCH').map((call) => call.body)).toEqual([{ enabled: false }, { enabled: true }])
  })

  it('刪除前要確認；伺服器拒絕時顯示原因', async () => {
    const { state, calls } = fakeBackend({ members: [member()] })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    show()
    fireEvent.click(row((await screen.findByText('成員一')).textContent ?? '').getByRole('button', { name: '刪除' }))
    expect(confirm).toHaveBeenCalledWith('刪除成員「成員一」的設定？過去的對話會保留。')
    expect(sent(calls, 'DELETE')).toHaveLength(0)

    confirm.mockReturnValue(true)
    state.override = (call) => (call.method === 'DELETE' ? { status: 409, body: { detail: '這位成員還有進行中的回合' } } : undefined)
    fireEvent.click(row('成員一').getByRole('button', { name: '刪除' }))
    expect((await screen.findByRole('alert')).textContent).toBe('這位成員還有進行中的回合')
    expect(screen.getByText('成員一')).toBeTruthy()

    state.override = undefined
    fireEvent.click(row('成員一').getByRole('button', { name: '刪除' }))
    await screen.findByText('還沒有成員。按「新增成員」設定第一位。')
    expect(sent(calls, 'DELETE')).toHaveLength(2)
    expect(state.members).toEqual([])
  })
})
