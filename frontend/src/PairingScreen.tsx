import { type FormEvent, useState } from 'react'

import * as api from './api'

export function PairingScreen({ onPaired }: { onPaired: () => void }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.pair(code)
      onPaired()
    } catch (failure) {
      setError(api.describeError(failure))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h2>配對這個瀏覽器</h2>
      <p>第一次使用要先配對。請在執行伺服器的那台電腦上另開一個終端，執行下面的指令取得配對碼：</p>
      <pre className="command">python -m app.web pair</pre>
      <p>配對碼 10 分鐘內有效，只能用一次；輸錯 5 次就要重新產生。</p>
      <form onSubmit={(event) => void submit(event)}>
        <label>
          配對碼
          <input
            name="code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="ABCD-EFGH"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            maxLength={32}
            required
          />
        </label>
        <button type="submit" disabled={busy}>
          配對
        </button>
      </form>
      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
