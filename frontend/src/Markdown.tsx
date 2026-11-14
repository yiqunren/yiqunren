// 成員回覆的 Markdown 顯示（FR-2）。回覆內容不可信任：
// - 不渲染原始 HTML（react-markdown 預設把它當文字顯示；這裡不加任何會解析 HTML 的外掛）。
// - 不載入圖片或其他外部資源，圖片只顯示成文字。
// - 連結只允許 http、https、mailto，在新分頁開啟，而且不帶來源頁資訊。
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const SAFE_LINK = /^(https?:\/\/|mailto:)/i

/** 不在允許清單裡的網址（含相對路徑、站內錨點、javascript:、data:）一律拿掉。 */
export function safeUrl(url: string): string | undefined {
  const trimmed = url.trim()
  return SAFE_LINK.test(trimmed) ? trimmed : undefined
}

export function Markdown({ text }: { text: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={safeUrl}
        components={{
          a({ href, children }) {
            if (href === undefined || href === '') {
              return <span>{children}</span> // 網址不被允許：只留文字
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            )
          },
          img({ alt }) {
            return <span className="markdown-image">［圖片{alt ? `：${alt}` : ''}，未載入］</span>
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}
