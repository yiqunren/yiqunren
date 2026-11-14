import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Markdown, safeUrl } from './Markdown'

function show(text: string): HTMLElement {
  return render(<Markdown text={text} />).container
}

describe('Markdown 顯示', () => {
  it('顯示標題、粗體、清單、程式碼、表格與刪除線', () => {
    const page = show(
      ['# 標題', '', '這是**粗體**和 `行內程式碼`，還有~~刪掉的~~。', '', '- 第一項', '- 第二項', '', '```', 'x = 1', '```', '', '| 甲 | 乙 |', '| --- | --- |', '| 1 | 2 |'].join('\n'),
    )
    expect(page.querySelector('h1')?.textContent).toBe('標題')
    expect(page.querySelector('strong')?.textContent).toBe('粗體')
    expect(page.querySelector('p code')?.textContent).toBe('行內程式碼')
    expect(page.querySelector('del')?.textContent).toBe('刪掉的')
    expect(Array.from(page.querySelectorAll('li'), (item) => item.textContent)).toEqual(['第一項', '第二項'])
    expect(page.querySelector('pre code')?.textContent).toBe('x = 1\n')
    expect(Array.from(page.querySelectorAll('th'), (cell) => cell.textContent)).toEqual(['甲', '乙'])
    expect(Array.from(page.querySelectorAll('td'), (cell) => cell.textContent)).toEqual(['1', '2'])
  })

  it('原始 HTML 不會變成元素，只當文字顯示', () => {
    const page = show('前面 <img src="x" onerror="alert(1)"> 後面\n\n<script>alert(2)</script>\n\n<iframe src="https://example.com"></iframe>')
    expect(page.querySelector('img, script, iframe')).toBeNull()
    expect(page.querySelectorAll('[onerror]').length).toBe(0)
    expect(page.textContent).toContain('<img src="x" onerror="alert(1)">')
    expect(page.textContent).toContain('<script>alert(2)</script>')
  })

  it('圖片不載入，只顯示成文字', () => {
    const page = show('![機密圖](https://example.com/leak.png?data=secret) 和 ![](https://example.com/b.png)')
    expect(page.querySelector('img')).toBeNull()
    expect(page.textContent).toBe('［圖片：機密圖，未載入］ 和 ［圖片，未載入］')
    expect(page.querySelectorAll('[src]').length).toBe(0)
  })

  it('http、https、mailto 的連結在新分頁開啟，而且不帶來源頁資訊', () => {
    const page = show('[甲](https://example.com/a) [乙](http://example.com/b) [丙](mailto:someone@example.com) www.example.org')
    const links = Array.from(page.querySelectorAll('a'))
    expect(links.map((link) => link.getAttribute('href'))).toEqual([
      'https://example.com/a',
      'http://example.com/b',
      'mailto:someone@example.com',
      'http://www.example.org',
    ])
    for (const link of links) {
      expect(link.getAttribute('target')).toBe('_blank')
      expect(link.getAttribute('rel')).toBe('noopener noreferrer')
    }
  })

  it('其他網址的連結不會變成連結，只留文字', () => {
    const page = show(
      ['[一](javascript:alert(1))', '[二](data:text/html,<b>x</b>)', '[三](/api/session)', '[四](#/members)', '[五](//example.com/x)', '[六](vbscript:x)', '[七](  JavaScript:alert(1))'].join(' '),
    )
    expect(page.querySelector('a')).toBeNull()
    expect(page.querySelectorAll('[href]').length).toBe(0)
    for (const text of ['一', '二', '三', '四', '五', '六']) {
      expect(page.textContent).toContain(text)
    }
  })
})

describe('網址檢查', () => {
  it('只放行 http、https、mailto', () => {
    expect(safeUrl('https://example.com/a?b=1#c')).toBe('https://example.com/a?b=1#c')
    expect(safeUrl('HTTP://example.com')).toBe('HTTP://example.com')
    expect(safeUrl('mailto:someone@example.com')).toBe('mailto:someone@example.com')
    for (const url of ['javascript:alert(1)', ' javascript:alert(1)', 'data:text/html,x', '/local', 'relative/path', '#anchor', '//example.com', 'ftp://example.com', 'httpx://example.com', '']) {
      expect(safeUrl(url)).toBeUndefined()
    }
  })
})
