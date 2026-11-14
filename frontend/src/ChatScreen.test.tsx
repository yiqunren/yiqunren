import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'
import { type Call, fakeBackend, FakeEventSource, installEventSource, member, turn } from './test-server'

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
const OFFLINE = '連不上伺服器，請確認後端還在執行。'
const M2 = '44444444-4444-4444-8444-444444444444'
const C1 = '33333333-3333-4333-8333-333333333333'
const C2 = '55555555-5555-4555-8555-555555555555'
const T2 = '66666666-6666-4666-8666-666666666666'

beforeEach(() => {
  window.location.hash = ''
})

function open(hash: string) {
  window.location.hash = hash
  render(<App />)
}

function list() {
  return within(screen.getByRole('navigation', { name: '對話清單' }))
}

function write(text: string) {
  fireEvent.change(screen.getByLabelText('訊息'), { target: { value: text } })
}

function sendButton() {
  return screen.getByRole<HTMLButtonElement>('button', { name: '送出' })
}

function posts(calls: Call[]) {
  return calls.filter((call) => call.method === 'POST' && call.path === '/api/turns')
}

/** 一段對話：一個已完成的回合，加一個從 1935 秒開始、還在跑的回合（假後端的時鐘是 2000 秒）。 */
function runningConversation() {
  return [
    turn(),
    turn({ id: T2, message: '第二個問題', state: 'running', reply: null, started: 1935, finished: null }),
  ]
}

/** 等到進行中的回合顯示出來，而且事件連線已經開啟（連線是畫面更新之後才開的）。 */
async function attached() {
  await screen.findByText('第二個問題')
  await waitFor(() => expect(FakeEventSource.opened.length).toBeGreaterThan(0))
}

describe('對話清單', () => {
  it('列出所有對話，點了打開那一段，網址跟著換', async () => {
    fakeBackend({
      members: [member()],
      turns: [
        turn({ reply: '第一段的**回覆**' }),
        turn({ id: T2, conversation_id: C2, member_name: '舊名字', message: '另一段對話', state: 'failed', error_kind: 'timeout', reply: null, started: 1500, finished: 1600 }),
      ],
    })
    installEventSource()
    open('#/chat')
    await screen.findByText('另一段對話')
    const items = list().getAllByRole('button')
    // 最近有活動的排前面。
    expect(items.map((item) => item.textContent?.split('・').slice(0, 2).join('・'))).toEqual(['另一段對話舊名字・失敗', '你好成員一・完成'])
    expect(screen.getByRole('heading', { name: '新對話' })).toBeTruthy()

    fireEvent.click(items[1])
    await screen.findByRole('heading', { name: '和「成員一」的對話' })
    expect(window.location.hash).toBe(`#/chat/${C1}`)
    expect(screen.getByText('回覆').tagName).toBe('STRONG')
    expect(list().getAllByRole('button')[1].getAttribute('aria-current')).toBe('true')

    fireEvent.click(list().getAllByRole('button')[0])
    await screen.findByText('失敗：逾時（超過這位成員的單回合時間上限）。不會自動重試，要不要重送由你決定。')
    expect(window.location.hash).toBe(`#/chat/${C2}`)

    fireEvent.click(screen.getByRole('button', { name: '新對話' }))
    await screen.findByRole('heading', { name: '新對話' })
    expect(window.location.hash).toBe('#/chat')
  })

  it('網址指到不存在的對話時說明找不到', async () => {
    fakeBackend({ members: [member()] })
    open(`#/chat/${C2}`)
    expect((await screen.findByRole('alert')).textContent).toBe('找不到這段對話，可能已經被刪除。')
  })
})

describe('讀取時連不上伺服器', () => {
  function writes(calls: Call[]) {
    return calls.filter((call) => call.method !== 'GET')
  }

  it('清單讀不到時顯示提示並在背景再讀；伺服器恢復後提示自動消失', async () => {
    const { state, calls } = fakeBackend({ members: [member()], turns: [turn()] })
    state.override = (call) => (call.path === '/api/conversations' ? 'offline' : undefined)
    open('#/chat')
    expect((await screen.findByRole('alert')).textContent).toBe(OFFLINE)
    state.override = undefined
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull(), { timeout: 3000 })
    expect(list().getByText('你好')).toBeTruthy()
    expect(writes(calls)).toEqual([]) // 背景重讀只讀資料
  })

  it('對話內容讀不到時顯示提示並在背景再讀；伺服器恢復後顯示對話', async () => {
    const { state, calls } = fakeBackend({ members: [member()], turns: [turn({ reply: '之前的回覆' })] })
    state.override = (call) => (call.path === `/api/conversations/${C1}` ? 'offline' : undefined)
    open(`#/chat/${C1}`)
    expect((await screen.findByRole('alert')).textContent).toBe(OFFLINE)
    state.override = undefined
    await screen.findByText('之前的回覆', undefined, { timeout: 3000 })
    expect(screen.queryByRole('alert')).toBeNull()
    expect(writes(calls)).toEqual([])
  })

  it('回合結束時更新清單失敗，伺服器恢復後提示自動消失', async () => {
    const { state, finish } = fakeBackend({ members: [member()], turns: runningConversation() })
    const sources = installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    state.override = (call) => (call.path === '/api/conversations' ? 'offline' : undefined)
    finish(T2, { state: 'completed', reply: '答完了' })
    act(() => sources[0].emit('done', { state: 'completed', error_kind: null, reply: '答完了' }))
    expect((await screen.findByRole('alert')).textContent).toBe(OFFLINE)
    state.override = undefined
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull(), { timeout: 3000 })
    expect(screen.getByText('答完了')).toBeTruthy()
  })

  it('離開私聊畫面後不再背景重讀', async () => {
    const { state, calls } = fakeBackend({ members: [member()] })
    state.override = (call) => (call.path === '/api/conversations' ? 'offline' : undefined)
    open('#/chat')
    await screen.findByRole('alert')
    fireEvent.click(screen.getByRole('button', { name: '成員' }))
    await screen.findByRole('button', { name: '新增成員' })
    const before = calls.filter((call) => call.path === '/api/conversations').length
    await new Promise((resolve) => setTimeout(resolve, 1500))
    expect(calls.filter((call) => call.path === '/api/conversations').length).toBe(before)
  })
})

describe('送出訊息', () => {
  it('新對話選成員送出，顯示執行中，收到回覆後以 Markdown 顯示', async () => {
    const { calls, finish } = fakeBackend({
      members: [member(), member({ id: M2, name: '成員二' }), member({ id: 'a3', name: '停用的', enabled: false })],
    })
    const sources = installEventSource()
    open('#/chat')
    const select = await screen.findByLabelText<HTMLSelectElement>('成員')
    // 停用的成員不能選。
    expect(Array.from(select.options, (option) => option.textContent)).toEqual(['成員一（Codex）', '成員二（Codex）'])
    expect(sendButton().disabled).toBe(true) // 還沒有內容
    write('   \n ')
    expect(sendButton().disabled).toBe(true) // 只有空白
    fireEvent.change(select, { target: { value: M2 } })
    write('第一個問題\n第二行')
    fireEvent.click(sendButton())

    expect((await screen.findByRole('status')).textContent).toMatch(/^執行中… 已經過 0:0\d$/)
    const [post] = posts(calls)
    const body = post.body as { request_id: string; conversation_id: string; member: string; text: string }
    expect(body).toEqual({ request_id: body.request_id, conversation_id: body.conversation_id, member: M2, text: '第一個問題\n第二行' })
    expect(body.request_id).toMatch(UUID)
    expect(body.conversation_id).toMatch(UUID)
    expect(body.conversation_id).not.toBe(body.request_id)
    expect(post.headers['X-Yiqunren-CSRF']).toBe('1')
    // 網址換成這段對話；事件只連這個回合，而且只連一次。
    expect(window.location.hash).toBe(`#/chat/${body.conversation_id}`)
    await waitFor(() => expect(sources.map((source) => source.url)).toEqual([`/api/turns/${body.request_id}/events`]))
    expect(screen.getByRole('heading', { name: '和「成員二」的對話' })).toBeTruthy()
    expect(screen.queryByLabelText('成員')).toBeNull() // 有回合之後成員就固定了
    expect(screen.getByLabelText<HTMLTextAreaElement>('訊息').value).toBe('')
    await list().findByText('執行中')

    // 上一個回合還沒結束，不能送下一則。
    write('等不及的第二則')
    expect(sendButton().disabled).toBe(true)
    fireEvent.submit(sendButton().closest('form') as HTMLFormElement)
    expect(screen.getByText('上一個回合還沒結束，結束後才能送出。')).toBeTruthy()

    finish(body.request_id, { state: 'completed', reply: '**好**的' })
    act(() => sources[0].emit('done', { state: 'completed', error_kind: null, reply: '**好**的' }))
    expect(screen.getByText('好').tagName).toBe('STRONG')
    expect(screen.queryByRole('status')).toBeNull()
    expect(sources[0].closed).toBe(true)
    await list().findByText('完成')
    expect(posts(calls).length).toBe(1)

    // 續問：同一段對話、同一位成員、新的請求 ID。
    expect(sendButton().disabled).toBe(false)
    fireEvent.click(sendButton())
    await waitFor(() => expect(posts(calls).length).toBe(2))
    const next = posts(calls)[1].body as typeof body
    expect(next).toEqual({ request_id: next.request_id, conversation_id: body.conversation_id, member: M2, text: '等不及的第二則' })
    expect(next.request_id).not.toBe(body.request_id)
    await waitFor(() => expect(sources.map((source) => source.url)).toEqual([`/api/turns/${body.request_id}/events`, `/api/turns/${next.request_id}/events`]))
  })

  it('Ctrl＋Enter 送出；單按 Enter 不送出', async () => {
    const { calls } = fakeBackend({ members: [member()] })
    installEventSource()
    open('#/chat')
    await screen.findByLabelText('成員')
    write('快捷鍵')
    fireEvent.keyDown(screen.getByLabelText('訊息'), { key: 'Enter' })
    expect(posts(calls).length).toBe(0)
    fireEvent.keyDown(screen.getByLabelText('訊息'), { key: 'Enter', ctrlKey: true })
    await screen.findByRole('status')
    expect(posts(calls).map((call) => (call.body as { text: string }).text)).toEqual(['快捷鍵'])
  })

  it('沒送成功時留著內容；同樣內容重送沿用同一個請求 ID，內容改了才換新的', async () => {
    const { state, calls } = fakeBackend({ members: [member()] })
    installEventSource()
    open('#/chat')
    await screen.findByLabelText('成員')
    state.override = (call) => (call.path === '/api/turns' ? 'offline' : undefined)
    write('甲')
    fireEvent.click(sendButton())
    expect((await screen.findByRole('alert')).textContent).toBe(OFFLINE)
    expect(screen.getByLabelText<HTMLTextAreaElement>('訊息').value).toBe('甲')
    expect(window.location.hash).toBe('#/chat')

    fireEvent.click(sendButton())
    await waitFor(() => expect(posts(calls).length).toBe(2))
    await waitFor(() => expect(sendButton().disabled).toBe(false))
    write('乙')
    fireEvent.click(sendButton())
    await waitFor(() => expect(posts(calls).length).toBe(3))
    await waitFor(() => expect(sendButton().disabled).toBe(false))
    const ids = posts(calls).map((call) => (call.body as { request_id: string }).request_id)
    expect(ids[1]).toBe(ids[0])
    expect(ids[2]).not.toBe(ids[0])
    // 三次都是同一段對話。
    expect(new Set(posts(calls).map((call) => (call.body as { conversation_id: string }).conversation_id)).size).toBe(1)

    // 連得上之後，用原本的請求 ID 重送成功。
    state.override = undefined
    fireEvent.click(sendButton())
    await screen.findByRole('status')
    expect((posts(calls)[3].body as { request_id: string }).request_id).toBe(ids[2])
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('伺服器說那個請求所屬的對話已刪除時，再送就換新的請求 ID', async () => {
    const { state, calls } = fakeBackend({ members: [member()] })
    installEventSource()
    open('#/chat')
    await screen.findByLabelText('成員')
    state.override = (call) =>
      call.path === '/api/turns' ? { status: 410, body: { detail: '這個請求所屬的對話已被刪除' } } : undefined
    write('甲')
    fireEvent.click(sendButton())
    expect((await screen.findByRole('alert')).textContent).toBe('這個請求所屬的對話已被刪除')
    state.override = undefined
    fireEvent.click(sendButton())
    await screen.findByRole('status')
    const ids = posts(calls).map((call) => (call.body as { request_id: string }).request_id)
    expect(ids.length).toBe(2)
    expect(ids[1]).not.toBe(ids[0])
  })

  it('伺服器拒絕時顯示原因', async () => {
    const { state } = fakeBackend({ members: [member()] })
    installEventSource()
    open('#/chat')
    await screen.findByLabelText('成員')
    state.override = (call) =>
      call.path === '/api/turns' ? { status: 503, body: { detail: '這位成員的轉接器還沒接上' } } : undefined
    write('甲')
    fireEvent.click(sendButton())
    expect((await screen.findByRole('alert')).textContent).toBe('這位成員的轉接器還沒接上')
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('沒有可用的成員時說明要先新增', async () => {
    fakeBackend({ members: [member({ enabled: false })] })
    open('#/chat')
    await screen.findByText('還沒有可用的成員，請先到「成員」新增或啟用一位。')
    expect(screen.queryByLabelText('訊息')).toBeNull()
  })
})

describe('進行中的回合', () => {
  it('重新整理後接回：顯示執行中與經過時間（用伺服器的時鐘），結束後顯示結果', async () => {
    const { finish } = fakeBackend({ members: [member()], turns: runningConversation() })
    const sources = installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    // 伺服器時鐘 2000 秒、回合從 1935 秒開始：65 秒。這台裝置的時鐘差很多也不影響。
    expect(screen.getByRole('status').textContent).toMatch(/^執行中… 已經過 1:0[5-9]$/)
    expect(sources.map((source) => source.url)).toEqual([`/api/turns/${T2}/events`])
    expect(screen.getByText('你好，我在。')).toBeTruthy() // 之前的回合照樣看得到
    expect(screen.getByRole<HTMLButtonElement>('button', { name: '刪除這段對話' }).disabled).toBe(true)

    // 伺服器重送「中斷中」事件：之前按過中斷。
    act(() => sources[0].emit('stopping'))
    expect(screen.getByRole('status').textContent).toMatch(/^中斷中，等成員的程序停止… 已經過 1:0[5-9]$/)
    expect(screen.getByRole<HTMLButtonElement>('button', { name: '中斷' }).disabled).toBe(true)

    finish(T2, { state: 'interrupted' })
    act(() => sources[0].emit('done', { state: 'interrupted', error_kind: null, reply: null }))
    expect(screen.getByText('已中斷。成員的程序已經停止。')).toBeTruthy()
    expect(screen.queryByRole('status')).toBeNull()
    expect(screen.queryByRole('button', { name: '中斷' })).toBeNull()
    await waitFor(() => expect(screen.getByRole<HTMLButtonElement>('button', { name: '刪除這段對話' }).disabled).toBe(false))
    expect(sendButton()).toBeTruthy()
  })

  it('按中斷送出要求，結果由事件告知；無法確認時顯示未知', async () => {
    const { calls } = fakeBackend({ members: [member()], turns: runningConversation() })
    const sources = installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    fireEvent.click(screen.getByRole('button', { name: '中斷' }))
    await waitFor(() => expect(screen.getByRole('status').textContent).toMatch(/^中斷中/))
    const stop = calls.filter((call) => call.method === 'POST' && call.path.endsWith('/interrupt'))
    expect(stop.map((call) => [call.path, call.headers['X-Yiqunren-CSRF'], call.body])).toEqual([
      [`/api/turns/${T2}/interrupt`, '1', undefined],
    ])
    expect(screen.getByRole<HTMLButtonElement>('button', { name: '中斷' }).disabled).toBe(true)
    // 還沒收到結果之前，不把回合當成已中斷。
    expect(screen.queryByText('已中斷。成員的程序已經停止。')).toBeNull()

    act(() => sources[0].emit('done', { state: 'unknown', error_kind: null, reply: null }))
    expect(
      screen.getByText('未知：無法確認這個回合的結果，或成員的程序是否已經停止。請自行核對後再決定要不要重送；不會自動重試。'),
    ).toBeTruthy()
  })

  it('按中斷時回合剛好已經結束，直接顯示結果', async () => {
    const { finish } = fakeBackend({ members: [member()], turns: runningConversation() })
    installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    finish(T2, { state: 'completed', reply: '其實已經答完了' })
    fireEvent.click(screen.getByRole('button', { name: '中斷' }))
    await screen.findByText('其實已經答完了')
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('中斷要求沒送達時照實說，回合仍顯示執行中', async () => {
    const { state } = fakeBackend({ members: [member()], turns: runningConversation() })
    installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    state.override = (call) =>
      call.path.endsWith('/interrupt') ? { status: 502, body: { detail: '中斷要求沒有送達轉接器，回合可能仍在執行' } } : undefined
    fireEvent.click(screen.getByRole('button', { name: '中斷' }))
    expect((await screen.findByRole('alert')).textContent).toBe('中斷要求沒有送達轉接器，回合可能仍在執行')
    expect(screen.getByRole('status').textContent).toMatch(/^執行中…/)
    expect(screen.getByRole<HTMLButtonElement>('button', { name: '中斷' }).disabled).toBe(false)
  })

  it('事件連線斷了：回合還在跑就稍後重連，已經結束就直接顯示結果', async () => {
    const { calls, finish } = fakeBackend({ members: [member()], turns: runningConversation() })
    const sources = installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    act(() => sources[0].emit('error'))
    expect(sources[0].closed).toBe(true)
    await screen.findByText('和伺服器的連線中斷，重新連線中…')
    expect(screen.getByRole('status').textContent).toMatch(/^執行中…/) // 不把斷線當成失敗
    expect(calls.filter((call) => call.path === `/api/turns/${T2}`).length).toBe(1)
    await waitFor(() => expect(sources.length).toBe(2), { timeout: 3000 })
    expect(sources[1].url).toBe(`/api/turns/${T2}/events`)
    act(() => sources[1].emit('open'))
    expect(screen.queryByText('和伺服器的連線中斷，重新連線中…')).toBeNull()

    finish(T2, { state: 'completed', reply: '斷線期間答完了' })
    act(() => sources[1].emit('error'))
    await screen.findByText('斷線期間答完了')
    expect(screen.queryByRole('status')).toBeNull()
    expect(sources.length).toBe(2)
  })

  it('事件內容看不懂時不亂猜，改去查回合狀態', async () => {
    const { finish } = fakeBackend({ members: [member()], turns: runningConversation() })
    const sources = installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    finish(T2, { state: 'failed', error_kind: 'reply_too_long' })
    act(() => sources[0].emit('done', undefined, '不是 JSON'))
    await screen.findByText('失敗：回覆過長（超過長度上限，回覆沒有保存）。不會自動重試，要不要重送由你決定。')
    expect(sources[0].closed).toBe(true)
  })

  it('事件說的結束狀態不是那四種時，一樣改去查回合狀態', async () => {
    const { finish } = fakeBackend({ members: [member()], turns: runningConversation() })
    const sources = installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    finish(T2, { state: 'unknown' })
    act(() => sources[0].emit('done', { state: 'succeeded', error_kind: null, reply: '不該顯示的內容' }))
    await screen.findByText(/^未知：無法確認這個回合的結果/)
    expect(screen.queryByText('不該顯示的內容')).toBeNull()
  })

  it('連線斷掉時發現配對已失效，回到配對畫面', async () => {
    const { state } = fakeBackend({ members: [member()], turns: runningConversation() })
    const sources = installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    state.paired = false
    act(() => sources[0].emit('error'))
    await screen.findByRole('heading', { name: '配對這個瀏覽器' })
    expect(screen.queryByText('第二個問題')).toBeNull()
    expect(sources.length).toBe(1)
  })

  it('離開對話時關掉事件連線', async () => {
    fakeBackend({ members: [member()], turns: runningConversation() })
    const sources = installEventSource()
    open(`#/chat/${C1}`)
    await attached()
    expect(sources[0].closed).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: '成員' }))
    await screen.findByRole('heading', { name: '成員' })
    expect(sources[0].closed).toBe(true)
  })
})

describe('回合結果', () => {
  it('失敗只顯示固定分類；訊息照原樣當純文字，回覆裡的 HTML 不會變成元素', async () => {
    fakeBackend({
      members: [member()],
      turns: [
        turn({ message: '<b>粗</b> **不是粗體**\n第二行', reply: '回覆 <img src="x" onerror="alert(1)">' }),
        turn({ id: T2, message: '乙', state: 'failed', error_kind: 'internal_error', reply: null, started: 1100 }),
        turn({ id: 'a3', message: '丙', state: 'failed', error_kind: 'something_new', reply: null, started: 1200 }),
      ],
    })
    open(`#/chat/${C1}`)
    await screen.findByText('回覆 <img src="x" onerror="alert(1)">')
    expect(document.querySelector('img')).toBeNull()
    // 對話裡擁有者的那一則（清單的標題也有同樣的字，所以直接看對話區）。
    const owner = document.querySelectorAll('.chat-main .bubble.owner')[0]
    expect(owner.textContent).toBe('你<b>粗</b> **不是粗體**\n第二行')
    expect(owner.querySelector('b, strong')).toBeNull()
    expect(screen.getByText('失敗：內部錯誤。不會自動重試，要不要重送由你決定。')).toBeTruthy()
    expect(screen.getByText('失敗：其他錯誤。不會自動重試，要不要重送由你決定。')).toBeTruthy()
  })

  it('FR-2 的每個固定分類都有自己的說明', async () => {
    const kinds = ['auth_failed', 'quota_exceeded', 'service_busy', 'model_unavailable', 'refused', 'budget_exceeded',
      'timeout', 'reply_too_long', 'internal_error']
    fakeBackend({
      members: [member()],
      turns: kinds.map((kind, index) =>
        turn({ id: `k${index}`, message: `問題${index}`, state: 'failed', error_kind: kind, reply: null, started: 1000 + index })),
    })
    open(`#/chat/${C1}`)
    await screen.findByText('問題8', { selector: '.chat-main *' })
    const shown = [...document.querySelectorAll('.chat-main [role], .chat-main p')]
      .map((node) => node.textContent ?? '')
      .filter((text) => text.startsWith('失敗：'))
    expect(new Set(shown).size).toBe(kinds.length)
    expect(shown.some((text) => text.includes('其他錯誤'))).toBe(false)
    expect(screen.getByText('失敗：超過花費上限（這位成員的單回合花費上限不夠，回覆沒有保存）。不會自動重試，要不要重送由你決定。')).toBeTruthy()
  })
})

describe('成員已不能續問', () => {
  it('成員被刪除後，對話只能看與刪除', async () => {
    fakeBackend({ members: [member({ id: M2, name: '別人' })], turns: [turn({ member_name: '當時的名字' })] })
    open(`#/chat/${C1}`)
    await screen.findByRole('heading', { name: /^和「當時的名字」的對話/ })
    expect(screen.getByText('這位成員已被刪除，這段對話只能看與刪除，不能續問。')).toBeTruthy()
    expect(screen.queryByLabelText('訊息')).toBeNull()
    expect(screen.getByText('你好，我在。')).toBeTruthy()
    expect(screen.getByRole<HTMLButtonElement>('button', { name: '刪除這段對話' }).disabled).toBe(false)
  })

  it('成員停用時不能續問', async () => {
    fakeBackend({ members: [member({ enabled: false })], turns: [turn()] })
    open(`#/chat/${C1}`)
    await screen.findByText('這位成員已停用，啟用後才能續問。')
    expect(screen.queryByLabelText('訊息')).toBeNull()
  })
})

describe('刪除對話', () => {
  it('先確認；刪除後回到新對話，清單不再有它', async () => {
    const { calls } = fakeBackend({ members: [member()], turns: [turn()] })
    open(`#/chat/${C1}`)
    await screen.findByText('你好，我在。')
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    fireEvent.click(screen.getByRole('button', { name: '刪除這段對話' }))
    expect(confirm).toHaveBeenCalledWith('刪除這段對話？訊息、回覆與回合紀錄會一併刪掉，無法復原。')
    expect(calls.some((call) => call.method === 'DELETE')).toBe(false)

    confirm.mockReturnValue(true)
    fireEvent.click(screen.getByRole('button', { name: '刪除這段對話' }))
    await screen.findByRole('heading', { name: '新對話' })
    expect(window.location.hash).toBe('#/chat')
    const removal = calls.filter((call) => call.method === 'DELETE')
    expect(removal.map((call) => [call.path, call.headers['X-Yiqunren-CSRF']])).toEqual([[`/api/conversations/${C1}`, '1']])
    await screen.findByText('還沒有對話。')
    expect(screen.queryByText('你好，我在。')).toBeNull()
  })

  it('伺服器拒絕時顯示原因，對話留著', async () => {
    const { state } = fakeBackend({ members: [member()], turns: [turn()] })
    open(`#/chat/${C1}`)
    await screen.findByText('你好，我在。')
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    state.override = (call) =>
      call.method === 'DELETE' ? { status: 409, body: { detail: '這段對話還有進行中的回合，不能刪除' } } : undefined
    fireEvent.click(screen.getByRole('button', { name: '刪除這段對話' }))
    expect((await screen.findByRole('alert')).textContent).toBe('這段對話還有進行中的回合，不能刪除')
    expect(screen.getByText('你好，我在。')).toBeTruthy()
    expect(window.location.hash).toBe(`#/chat/${C1}`)
  })
})
