import { useCallback, useEffect, useState } from 'react'

import * as api from './api'
import { MembersScreen } from './MembersScreen'
import { PairingScreen } from './PairingScreen'

type Phase = 'loading' | 'unpaired' | 'paired' | 'unreachable'

export function App() {
  const [phase, setPhase] = useState<Phase>('loading')
  const [notice, setNotice] = useState<string | null>(null)

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
        {phase === 'paired' && <MembersScreen onUnauthorized={expired} />}
      </main>
    </div>
  )
}
