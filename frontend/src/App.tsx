import { useCallback, useEffect, useState } from 'react'

import * as api from './api'
import { ChatScreen } from './ChatScreen'
import { MembersScreen } from './MembersScreen'
import { PairingScreen } from './PairingScreen'

type Phase = 'loading' | 'unpaired' | 'paired' | 'unreachable'

// 畫面記在網址的 # 後面（#/members、#/chat、#/chat/<對話 ID>），重新整理後回到同一個畫面。
// # 後面的內容不會送到伺服器。
type Route = { screen: 'members' } | { screen: 'chat'; conversationId: string | null }

const CHAT_ROUTE = /^#\/chat(?:\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}))?$/

function parseRoute(hash: string): Route {
  const chat = CHAT_ROUTE.exec(hash)
  return chat === null ? { screen: 'members' } : { screen: 'chat', conversationId: chat[1] ?? null }
}

function routeHash(route: Route): string {
  if (route.screen === 'members') {
    return '#/members'
  }
  return route.conversationId === null ? '#/chat' : `#/chat/${route.conversationId}`
}

export function App() {
  const [phase, setPhase] = useState<Phase>('loading')
  const [notice, setNotice] = useState<string | null>(null)
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash))

  useEffect(() => {
    // 上一頁、下一頁，或直接改網址。
    const sync = () => setRoute(parseRoute(window.location.hash))
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  const go = useCallback((next: Route) => {
    window.location.hash = routeHash(next)
    setRoute(next)
  }, [])

  const openConversation = useCallback(
    (conversationId: string | null) => go({ screen: 'chat', conversationId }),
    [go],
  )

  const check = useCallback(async () => {
    setPhase('loading')
    try {
      const session = await api.getSession()
      setPhase(session.paired ? 'paired' : 'unpaired')
    } catch {
      setPhase('unreachable')
    }
  }, [])

  useEffect(() => {
    void check()
  }, [check])

  // 配對失效（例如 30 天沒使用，或在本機被撤銷）時回到配對畫面。
  const expired = useCallback(() => {
    setNotice('配對已失效，請重新配對。')
    setPhase('unpaired')
  }, [])

  async function logout() {
    try {
      await api.logout()
      setNotice(null)
      setPhase('unpaired')
    } catch (error) {
      setNotice(api.describeError(error))
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>議群人</h1>
        {phase === 'paired' && (
          <button type="button" onClick={() => void logout()}>
            登出這個瀏覽器
          </button>
        )}
      </header>
      {notice !== null && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      <main>
        {phase === 'loading' && <p>載入中…</p>}
        {phase === 'unreachable' && (
          <div>
            <p role="alert">連不上伺服器，請確認後端還在執行。</p>
            <button type="button" onClick={() => void check()}>
              重試
            </button>
          </div>
        )}
        {phase === 'unpaired' && (
          <PairingScreen
            onPaired={() => {
              setNotice(null)
              setPhase('paired')
            }}
          />
        )}
        {phase === 'paired' && (
          <nav className="tabs" aria-label="畫面">
            <button
              type="button"
              aria-current={route.screen === 'members' ? 'page' : undefined}
              onClick={() => go({ screen: 'members' })}
            >
              成員
            </button>
            <button
              type="button"
              aria-current={route.screen === 'chat' ? 'page' : undefined}
              onClick={() => go({ screen: 'chat', conversationId: null })}
            >
              私聊
            </button>
          </nav>
        )}
        {phase === 'paired' && route.screen === 'members' && <MembersScreen onUnauthorized={expired} />}
        {phase === 'paired' && route.screen === 'chat' && (
          <ChatScreen conversationId={route.conversationId} onOpen={openConversation} onUnauthorized={expired} />
        )}
      </main>
    </div>
  )
}
