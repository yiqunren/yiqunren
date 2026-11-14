# 第三方軟體聲明（THIRD_PARTY_NOTICES）

本檔記錄不是本專案自己撰寫、但被本 repo 使用或會隨網頁介面一起發布的第三方軟體：來源、版本與授權。本專案自己的程式碼授權見 `LICENSE`。從舊專案匯入的檔案不記在這裡，記在 `PROVENANCE.md`。

## 範圍與限制

- 本檔涵蓋兩部分：**網頁介面（`frontend/`）的 npm 套件**（第一到三節），以及 **Python 後端依賴**（第四節，來源是 `pyproject.toml` 與 `uv.lock`）。Codex、Grok、Claude Code 等 AI 的 CLI 是使用者自己安裝的軟體，不隨本專案發布，不在這裡。
- `frontend/` 沒有字型、圖片或其他素材：除程式碼與 `package.json`、`package-lock.json` 外，只有 `index.html` 與 `src/styles.css`，都是本專案自己寫的。
- 第一到三節的資料來源是 `frontend/package-lock.json`（`lockfileVersion` 3）與已安裝的 `frontend/node_modules/` 裡各套件的授權檔，不是對打包結果做的內容分析。「隨網頁介面發布」指鎖檔裡沒有標為開發用（`dev`）的套件，是可能被打包進去的範圍；實際被打進 `app/web/static/` 的只會是其中一部分。
- 前端鎖檔裡全部 233 個套件的下載來源都是 npm 官方 registry（`registry.npmjs.org`），每一筆都有完整性雜湊（`integrity`）。套件是在本 repo 以 `npm` 安裝並產生鎖檔，沒有複製其他專案的鎖檔或 `node_modules`。
- 版本、授權欄位與版權行都照鎖檔與套件內的檔案原樣整理；授權標示以各套件宣告的為準，沒有另外做法律判斷。新增或升級套件後要重新整理這份清單。

## 一、隨網頁介面發布的套件（105 個）

授權分布：MIT 104 個、ISC 1 個。均允許商用與再散布，條件是保留版權聲明與授權全文（下方第三節）。

直接依賴：`react`、`react-dom`、`react-markdown`、`remark-gfm`；其餘是它們的相依套件。

每一列：套件、版本、授權、原始碼位置、版權聲明、授權全文編號（對應第三節）。

### @types/debug 4.1.13

- 授權：MIT（全文 1）
- 原始碼：https://github.com/DefinitelyTyped/DefinitelyTyped
- npm：https://www.npmjs.com/package/@types/debug/v/4.1.13
- 版權：Copyright (c) Microsoft Corporation.

### @types/estree 1.0.10

- 授權：MIT（全文 1）
- 原始碼：https://github.com/DefinitelyTyped/DefinitelyTyped
- npm：https://www.npmjs.com/package/@types/estree/v/1.0.10
- 版權：Copyright (c) Microsoft Corporation.

### @types/estree-jsx 1.0.5

- 授權：MIT（全文 1）
- 原始碼：https://github.com/DefinitelyTyped/DefinitelyTyped
- npm：https://www.npmjs.com/package/@types/estree-jsx/v/1.0.5
- 版權：Copyright (c) Microsoft Corporation.

### @types/hast 3.0.5

- 授權：MIT（全文 1）
- 原始碼：https://github.com/DefinitelyTyped/DefinitelyTyped
- npm：https://www.npmjs.com/package/@types/hast/v/3.0.5
- 版權：Copyright (c) Microsoft Corporation.

### @types/mdast 4.0.4

- 授權：MIT（全文 1）
- 原始碼：https://github.com/DefinitelyTyped/DefinitelyTyped
- npm：https://www.npmjs.com/package/@types/mdast/v/4.0.4
- 版權：Copyright (c) Microsoft Corporation.

### @types/ms 2.1.0

- 授權：MIT（全文 1）
- 原始碼：https://github.com/DefinitelyTyped/DefinitelyTyped
- npm：https://www.npmjs.com/package/@types/ms/v/2.1.0
- 版權：Copyright (c) Microsoft Corporation.

### @types/react 19.3.0（直接依賴）

- 授權：MIT（全文 1）
- 原始碼：https://github.com/DefinitelyTyped/DefinitelyTyped
- npm：https://www.npmjs.com/package/@types/react/v/19.3.0
- 版權：Copyright (c) Microsoft Corporation.

### @types/unist 3.0.3

- 授權：MIT（全文 1）
- 原始碼：https://github.com/DefinitelyTyped/DefinitelyTyped
- npm：https://www.npmjs.com/package/@types/unist/v/3.0.3
- 版權：Copyright (c) Microsoft Corporation.

### @types/unist 2.0.11

- 授權：MIT（全文 1）
- 原始碼：https://github.com/DefinitelyTyped/DefinitelyTyped
- npm：https://www.npmjs.com/package/@types/unist/v/2.0.11
- 版權：Copyright (c) Microsoft Corporation.

### @ungap/structured-clone 1.4.0

- 授權：ISC（全文 2）
- 原始碼：https://github.com/ungap/structured-clone
- npm：https://www.npmjs.com/package/@ungap/structured-clone/v/1.4.0
- 版權：Copyright (c) 2021, Andrea Giammarchi, @WebReflection

### bail 2.0.2

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/bail
- npm：https://www.npmjs.com/package/bail/v/2.0.2
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### ccount 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/ccount
- npm：https://www.npmjs.com/package/ccount/v/2.0.1
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### character-entities 2.0.2

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/character-entities
- npm：https://www.npmjs.com/package/character-entities/v/2.0.2
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### character-entities-html4 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/character-entities-html4
- npm：https://www.npmjs.com/package/character-entities-html4/v/2.1.0
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### character-entities-legacy 3.0.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/character-entities-legacy
- npm：https://www.npmjs.com/package/character-entities-legacy/v/3.0.0
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### character-reference-invalid 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/character-reference-invalid
- npm：https://www.npmjs.com/package/character-reference-invalid/v/2.0.1
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### comma-separated-tokens 2.0.3

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/comma-separated-tokens
- npm：https://www.npmjs.com/package/comma-separated-tokens/v/2.0.3
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

### csstype 3.2.3

- 授權：MIT（全文 4）
- 原始碼：https://github.com/frenic/csstype
- npm：https://www.npmjs.com/package/csstype/v/3.2.3
- 版權：Copyright (c) 2017-2018 Fredrik Nicol

### debug 4.4.3

- 授權：MIT（全文 3）
- 原始碼：https://github.com/debug-js/debug
- npm：https://www.npmjs.com/package/debug/v/4.4.3
- 版權：Copyright (c) 2014-2017 TJ Holowaychuk <tj@vision-media.ca>
- 版權：Copyright (c) 2018-2021 Josh Junon

### decode-named-character-reference 1.3.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/decode-named-character-reference
- npm：https://www.npmjs.com/package/decode-named-character-reference/v/1.3.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### dequal 2.0.3

- 授權：MIT（全文 5）
- 原始碼：https://github.com/lukeed/dequal
- npm：https://www.npmjs.com/package/dequal/v/2.0.3
- 版權：Copyright (c) Luke Edwards <luke.edwards05@gmail.com> (lukeed.com)

### devlop 1.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/devlop
- npm：https://www.npmjs.com/package/devlop/v/1.1.0
- 版權：Copyright (c) 2023 Titus Wormer <tituswormer@gmail.com>

### escape-string-regexp 5.0.0

- 授權：MIT（全文 6）
- 原始碼：https://github.com/sindresorhus/escape-string-regexp
- npm：https://www.npmjs.com/package/escape-string-regexp/v/5.0.0
- 版權：Copyright (c) Sindre Sorhus <sindresorhus@gmail.com> (https://sindresorhus.com)

### estree-util-is-identifier-name 3.0.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/estree-util-is-identifier-name
- npm：https://www.npmjs.com/package/estree-util-is-identifier-name/v/3.0.0
- 版權：Copyright (c) 2020 Titus Wormer <tituswormer@gmail.com>

### extend 3.0.2

- 授權：MIT（全文 5）
- 原始碼：https://github.com/justmoon/node-extend
- npm：https://www.npmjs.com/package/extend/v/3.0.2
- 版權：Copyright (c) 2014 Stefan Thomas

### hast-util-to-jsx-runtime 2.3.7

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/hast-util-to-jsx-runtime
- npm：https://www.npmjs.com/package/hast-util-to-jsx-runtime/v/2.3.7
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### hast-util-whitespace 3.0.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/hast-util-whitespace
- npm：https://www.npmjs.com/package/hast-util-whitespace/v/3.0.0
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

### html-url-attributes 3.0.1

- 授權：MIT（全文 7）
- 原始碼：https://github.com/rehypejs/rehype-minify/tree/main/packages/html-url-attributes
- npm：https://www.npmjs.com/package/html-url-attributes/v/3.0.1
- 版權：Copyright (c) Titus Wormer

### inline-style-parser 0.2.9

- 授權：MIT（全文 3）
- 原始碼：https://github.com/remarkablemark/inline-style-parser
- npm：https://www.npmjs.com/package/inline-style-parser/v/0.2.9
- 版權：Copyright (c) 2012 TJ Holowaychuk <tj@vision-media.ca>

### is-alphabetical 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/is-alphabetical
- npm：https://www.npmjs.com/package/is-alphabetical/v/2.0.1
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

### is-alphanumerical 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/is-alphanumerical
- npm：https://www.npmjs.com/package/is-alphanumerical/v/2.0.1
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

### is-decimal 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/is-decimal
- npm：https://www.npmjs.com/package/is-decimal/v/2.0.1
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

### is-hexadecimal 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/is-hexadecimal
- npm：https://www.npmjs.com/package/is-hexadecimal/v/2.0.1
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

### is-plain-obj 4.1.0

- 授權：MIT（全文 6）
- 原始碼：https://github.com/sindresorhus/is-plain-obj
- npm：https://www.npmjs.com/package/is-plain-obj/v/4.1.0
- 版權：Copyright (c) Sindre Sorhus <sindresorhus@gmail.com> (https://sindresorhus.com)

### longest-streak 3.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/longest-streak
- npm：https://www.npmjs.com/package/longest-streak/v/3.1.0
- 版權：Copyright (c) 2015 Titus Wormer <mailto:tituswormer@gmail.com>

### markdown-table 3.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/markdown-table
- npm：https://www.npmjs.com/package/markdown-table/v/3.1.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-find-and-replace 3.0.4

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-find-and-replace
- npm：https://www.npmjs.com/package/mdast-util-find-and-replace/v/3.0.4
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-from-markdown 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-from-markdown
- npm：https://www.npmjs.com/package/mdast-util-from-markdown/v/2.1.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-gfm 3.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-gfm
- npm：https://www.npmjs.com/package/mdast-util-gfm/v/3.1.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-gfm-autolink-literal 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-gfm-autolink-literal
- npm：https://www.npmjs.com/package/mdast-util-gfm-autolink-literal/v/2.1.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-gfm-footnote 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-gfm-footnote
- npm：https://www.npmjs.com/package/mdast-util-gfm-footnote/v/2.1.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-gfm-strikethrough 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-gfm-strikethrough
- npm：https://www.npmjs.com/package/mdast-util-gfm-strikethrough/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-gfm-table 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-gfm-table
- npm：https://www.npmjs.com/package/mdast-util-gfm-table/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-gfm-task-list-item 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-gfm-task-list-item
- npm：https://www.npmjs.com/package/mdast-util-gfm-task-list-item/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-mdx-expression 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-mdx-expression
- npm：https://www.npmjs.com/package/mdast-util-mdx-expression/v/2.0.1
- 版權：Copyright (c) 2020 Titus Wormer <tituswormer@gmail.com>

### mdast-util-mdx-jsx 3.2.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-mdx-jsx
- npm：https://www.npmjs.com/package/mdast-util-mdx-jsx/v/3.2.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-mdxjs-esm 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-mdxjs-esm
- npm：https://www.npmjs.com/package/mdast-util-mdxjs-esm/v/2.0.1
- 版權：Copyright (c) 2020 Titus Wormer <tituswormer@gmail.com>

### mdast-util-phrasing 4.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-phrasing
- npm：https://www.npmjs.com/package/mdast-util-phrasing/v/4.1.0
- 版權：Copyright (c) 2017 Titus Wormer <tituswormer@gmail.com>
- 版權：Copyright (c) 2017 Victor Felder <victor@draft.li>

### mdast-util-to-hast 13.2.2

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-to-hast
- npm：https://www.npmjs.com/package/mdast-util-to-hast/v/13.2.2
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-to-markdown 2.2.3

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-to-markdown
- npm：https://www.npmjs.com/package/mdast-util-to-markdown/v/2.2.3
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### mdast-util-to-string 4.0.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/mdast-util-to-string
- npm：https://www.npmjs.com/package/mdast-util-to-string/v/4.0.0
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### micromark 4.0.3

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark
- npm：https://www.npmjs.com/package/micromark/v/4.0.3
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-core-commonmark 2.0.4

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-core-commonmark
- npm：https://www.npmjs.com/package/micromark-core-commonmark/v/2.0.4
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-extension-gfm 3.0.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark-extension-gfm
- npm：https://www.npmjs.com/package/micromark-extension-gfm/v/3.0.0
- 版權：Copyright (c) 2020 Titus Wormer <tituswormer@gmail.com>

### micromark-extension-gfm-autolink-literal 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark-extension-gfm-autolink-literal
- npm：https://www.npmjs.com/package/micromark-extension-gfm-autolink-literal/v/2.1.0
- 版權：Copyright (c) 2020 Titus Wormer <tituswormer@gmail.com>

### micromark-extension-gfm-footnote 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark-extension-gfm-footnote
- npm：https://www.npmjs.com/package/micromark-extension-gfm-footnote/v/2.1.0
- 版權：Copyright (c) 2021 Titus Wormer <tituswormer@gmail.com>

### micromark-extension-gfm-strikethrough 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark-extension-gfm-strikethrough
- npm：https://www.npmjs.com/package/micromark-extension-gfm-strikethrough/v/2.1.0
- 版權：Copyright (c) 2020 Titus Wormer <tituswormer@gmail.com>

### micromark-extension-gfm-table 2.1.2

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark-extension-gfm-table
- npm：https://www.npmjs.com/package/micromark-extension-gfm-table/v/2.1.2
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-extension-gfm-tagfilter 2.0.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark-extension-gfm-tagfilter
- npm：https://www.npmjs.com/package/micromark-extension-gfm-tagfilter/v/2.0.0
- 版權：Copyright (c) 2020 Titus Wormer <tituswormer@gmail.com>

### micromark-extension-gfm-task-list-item 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark-extension-gfm-task-list-item
- npm：https://www.npmjs.com/package/micromark-extension-gfm-task-list-item/v/2.1.0
- 版權：Copyright (c) 2020 Titus Wormer <tituswormer@gmail.com>

### micromark-factory-destination 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-factory-destination
- npm：https://www.npmjs.com/package/micromark-factory-destination/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-factory-label 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-factory-label
- npm：https://www.npmjs.com/package/micromark-factory-label/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-factory-space 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-factory-space
- npm：https://www.npmjs.com/package/micromark-factory-space/v/2.1.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-factory-title 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-factory-title
- npm：https://www.npmjs.com/package/micromark-factory-title/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-factory-whitespace 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-factory-whitespace
- npm：https://www.npmjs.com/package/micromark-factory-whitespace/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-character 2.1.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-character
- npm：https://www.npmjs.com/package/micromark-util-character/v/2.1.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-chunked 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-chunked
- npm：https://www.npmjs.com/package/micromark-util-chunked/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-classify-character 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-classify-character
- npm：https://www.npmjs.com/package/micromark-util-classify-character/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-combine-extensions 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-combine-extensions
- npm：https://www.npmjs.com/package/micromark-util-combine-extensions/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-decode-numeric-character-reference 2.0.2

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-decode-numeric-character-reference
- npm：https://www.npmjs.com/package/micromark-util-decode-numeric-character-reference/v/2.0.2
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-decode-string 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-decode-string
- npm：https://www.npmjs.com/package/micromark-util-decode-string/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-edit-map 1.0.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-edit-map
- npm：https://www.npmjs.com/package/micromark-util-edit-map/v/1.0.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-encode 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-encode
- npm：https://www.npmjs.com/package/micromark-util-encode/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-html-tag-name 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-html-tag-name
- npm：https://www.npmjs.com/package/micromark-util-html-tag-name/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-normalize-identifier 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-normalize-identifier
- npm：https://www.npmjs.com/package/micromark-util-normalize-identifier/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-resolve-all 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-resolve-all
- npm：https://www.npmjs.com/package/micromark-util-resolve-all/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-sanitize-uri 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-sanitize-uri
- npm：https://www.npmjs.com/package/micromark-util-sanitize-uri/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-subtokenize 2.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-subtokenize
- npm：https://www.npmjs.com/package/micromark-util-subtokenize/v/2.1.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-symbol 2.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-symbol
- npm：https://www.npmjs.com/package/micromark-util-symbol/v/2.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### micromark-util-types 2.0.3

- 授權：MIT（全文 3）
- 原始碼：https://github.com/micromark/micromark/tree/main/packages/micromark-util-types
- npm：https://www.npmjs.com/package/micromark-util-types/v/2.0.3
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### ms 2.1.3

- 授權：MIT（全文 5）
- 原始碼：https://github.com/vercel/ms
- npm：https://www.npmjs.com/package/ms/v/2.1.3
- 版權：Copyright (c) 2020 Vercel, Inc.

### parse-entities 4.0.2

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/parse-entities
- npm：https://www.npmjs.com/package/parse-entities/v/4.0.2
- 版權：Copyright (c) Titus Wormer <mailto:tituswormer@gmail.com>

### property-information 7.2.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/property-information
- npm：https://www.npmjs.com/package/property-information/v/7.2.0
- 版權：Copyright (c) Titus Wormer <mailto:tituswormer@gmail.com>

### react 19.3.1（直接依賴）

- 授權：MIT（全文 6）
- 原始碼：https://github.com/react/react
- npm：https://www.npmjs.com/package/react/v/19.3.1
- 版權：Copyright (c) Meta Platforms, Inc. and affiliates.

### react-dom 19.3.1（直接依賴）

- 授權：MIT（全文 6）
- 原始碼：https://github.com/react/react
- npm：https://www.npmjs.com/package/react-dom/v/19.3.1
- 版權：Copyright (c) Meta Platforms, Inc. and affiliates.

### react-markdown 10.1.0（直接依賴）

- 授權：MIT（全文 5）
- 原始碼：https://github.com/remarkjs/react-markdown
- npm：https://www.npmjs.com/package/react-markdown/v/10.1.0
- 版權：Copyright (c) Espen Hovlandsdal

### remark-gfm 4.0.1（直接依賴）

- 授權：MIT（全文 3）
- 原始碼：https://github.com/remarkjs/remark-gfm
- npm：https://www.npmjs.com/package/remark-gfm/v/4.0.1
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### remark-parse 11.0.0

- 授權：MIT（全文 7）
- 原始碼：https://github.com/remarkjs/remark/tree/main/packages/remark-parse
- npm：https://www.npmjs.com/package/remark-parse/v/11.0.0
- 版權：Copyright (c) 2014 Titus Wormer <tituswormer@gmail.com>

### remark-rehype 11.1.2

- 授權：MIT（全文 3）
- 原始碼：https://github.com/remarkjs/remark-rehype
- npm：https://www.npmjs.com/package/remark-rehype/v/11.1.2
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### remark-stringify 11.0.0

- 授權：MIT（全文 7）
- 原始碼：https://github.com/remarkjs/remark/tree/main/packages/remark-stringify
- npm：https://www.npmjs.com/package/remark-stringify/v/11.0.0
- 版權：Copyright (c) 2014 Titus Wormer <tituswormer@gmail.com>

### scheduler 0.28.0

- 授權：MIT（全文 6）
- 原始碼：https://github.com/react/react
- npm：https://www.npmjs.com/package/scheduler/v/0.28.0
- 版權：Copyright (c) Meta Platforms, Inc. and affiliates.

### space-separated-tokens 2.0.2

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/space-separated-tokens
- npm：https://www.npmjs.com/package/space-separated-tokens/v/2.0.2
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

### stringify-entities 4.0.4

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/stringify-entities
- npm：https://www.npmjs.com/package/stringify-entities/v/4.0.4
- 版權：Copyright (c) 2015 Titus Wormer <mailto:tituswormer@gmail.com>

### style-to-object 2.0.2

- 授權：MIT（全文 5）
- 原始碼：https://github.com/remarkablemark/style-to-object
- npm：https://www.npmjs.com/package/style-to-object/v/2.0.2
- 版權：Copyright (c) 2017 Menglin "Mark" Xu <mark@remarkablemark.org>

### trim-lines 3.0.1

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/trim-lines
- npm：https://www.npmjs.com/package/trim-lines/v/3.0.1
- 版權：Copyright (c) 2015 Titus Wormer <mailto:tituswormer@gmail.com>

### trough 2.2.0

- 授權：MIT（全文 7）
- 原始碼：https://github.com/wooorm/trough
- npm：https://www.npmjs.com/package/trough/v/2.2.0
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

### unified 11.0.5

- 授權：MIT（全文 7）
- 原始碼：https://github.com/unifiedjs/unified
- npm：https://www.npmjs.com/package/unified/v/11.0.5
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### unist-util-is 6.0.1

- 授權：MIT（全文 8）
- 原始碼：https://github.com/syntax-tree/unist-util-is
- npm：https://www.npmjs.com/package/unist-util-is/v/6.0.1
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### unist-util-position 5.0.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/unist-util-position
- npm：https://www.npmjs.com/package/unist-util-position/v/5.0.0
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### unist-util-stringify-position 4.0.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/unist-util-stringify-position
- npm：https://www.npmjs.com/package/unist-util-stringify-position/v/4.0.0
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

### unist-util-visit 5.2.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/unist-util-visit
- npm：https://www.npmjs.com/package/unist-util-visit/v/5.2.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### unist-util-visit-parents 6.1.0

- 授權：MIT（全文 3）
- 原始碼：https://github.com/syntax-tree/unist-util-visit-parents
- npm：https://www.npmjs.com/package/unist-util-visit-parents/v/6.1.0
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### vfile 6.0.3

- 授權：MIT（全文 7）
- 原始碼：https://github.com/vfile/vfile
- npm：https://www.npmjs.com/package/vfile/v/6.0.3
- 版權：Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

### vfile-message 4.0.4

- 授權：MIT（全文 3）
- 原始碼：https://github.com/vfile/vfile-message
- npm：https://www.npmjs.com/package/vfile-message/v/4.0.4
- 版權：Copyright (c) Titus Wormer <tituswormer@gmail.com>

### zwitch 2.0.4

- 授權：MIT（全文 3）
- 原始碼：https://github.com/wooorm/zwitch
- npm：https://www.npmjs.com/package/zwitch/v/2.0.4
- 版權：Copyright (c) 2016 Titus Wormer <tituswormer@gmail.com>

## 二、只在開發與建置時使用的套件（128 個）

這些套件在鎖檔裡標為開發用（`dev`），不屬於網頁介面的執行期相依；它們用來測試、型別檢查與打包。授權分布：MIT 83 個、Apache-2.0 25 個、MPL-2.0 12 個、BSD-2-Clause 2 個、ISC 2 個、BSD-3-Clause 2 個、BlueOak-1.0.0 1 個、0BSD 1 個。

直接的開發依賴：`@testing-library/dom` 10.4.2、`@testing-library/react` 16.3.3、`@types/react` 19.3.0、`@types/react-dom` 19.3.0、`@vitejs/plugin-react` 6.3.0、`jsdom` 31.0.1、`typescript` 7.0.2、`vite` 8.3.8、`vitest` 5.1.0。

其中授權比 MIT 與 BSD 類更需要留意的（只在開發與建置時使用，本專案沒有修改它們；沒有逐一檢查打包工具是否把自己的少量輔助程式碼寫進輸出）：

- Apache-2.0：`@typescript/typescript-aix-ppc64`、`@typescript/typescript-darwin-arm64`、`@typescript/typescript-darwin-x64`、`@typescript/typescript-freebsd-arm64`、`@typescript/typescript-freebsd-x64`、`@typescript/typescript-linux-arm`，等共 25 個
- MPL-2.0：`lightningcss`、`lightningcss-android-arm64`、`lightningcss-darwin-arm64`、`lightningcss-darwin-x64`、`lightningcss-freebsd-x64`、`lightningcss-linux-arm-gnueabihf`，等共 12 個

如果之後改成把某個開發用套件隨發布內容一起提供（例如把打包工具放進安裝包），要先把它移到第一節並附上授權全文。

## 三、授權全文

同一編號的套件授權文字相同（除了各套件自己的版權行，已列在第一節，以及空白排版）。全文取自第一個列出的套件發布檔裡的授權檔，內容不改。

### 全文 1：MIT

適用：`@types/debug`、`@types/estree`、`@types/estree-jsx`、`@types/hast`、`@types/mdast`、`@types/ms`、`@types/react`、`@types/unist`

以第一個套件（`@types/debug`）的授權檔為準：

```text
    MIT License

    Copyright (c) Microsoft Corporation.

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE
```

### 全文 2：ISC

適用：`@ungap/structured-clone`

以第一個套件（`@ungap/structured-clone`）的授權檔為準：

```text
ISC License

Copyright (c) 2021, Andrea Giammarchi, @WebReflection

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
```

### 全文 3：MIT

適用：`bail`、`ccount`、`character-entities`、`character-entities-html4`、`character-entities-legacy`、`character-reference-invalid`、`comma-separated-tokens`、`debug`、`decode-named-character-reference`、`devlop`、`estree-util-is-identifier-name`、`hast-util-to-jsx-runtime`、`hast-util-whitespace`、`inline-style-parser`、`is-alphabetical`、`is-alphanumerical`、`is-decimal`、`is-hexadecimal`、`longest-streak`、`markdown-table`、`mdast-util-find-and-replace`、`mdast-util-from-markdown`、`mdast-util-gfm`、`mdast-util-gfm-autolink-literal`、`mdast-util-gfm-footnote`、`mdast-util-gfm-strikethrough`、`mdast-util-gfm-table`、`mdast-util-gfm-task-list-item`、`mdast-util-mdx-expression`、`mdast-util-mdx-jsx`、`mdast-util-mdxjs-esm`、`mdast-util-phrasing`、`mdast-util-to-hast`、`mdast-util-to-markdown`、`mdast-util-to-string`、`micromark`、`micromark-core-commonmark`、`micromark-extension-gfm`、`micromark-extension-gfm-autolink-literal`、`micromark-extension-gfm-footnote`、`micromark-extension-gfm-strikethrough`、`micromark-extension-gfm-table`、`micromark-extension-gfm-tagfilter`、`micromark-extension-gfm-task-list-item`、`micromark-factory-destination`、`micromark-factory-label`、`micromark-factory-space`、`micromark-factory-title`、`micromark-factory-whitespace`、`micromark-util-character`、`micromark-util-chunked`、`micromark-util-classify-character`、`micromark-util-combine-extensions`、`micromark-util-decode-numeric-character-reference`、`micromark-util-decode-string`、`micromark-util-edit-map`、`micromark-util-encode`、`micromark-util-html-tag-name`、`micromark-util-normalize-identifier`、`micromark-util-resolve-all`、`micromark-util-sanitize-uri`、`micromark-util-subtokenize`、`micromark-util-symbol`、`micromark-util-types`、`parse-entities`、`property-information`、`remark-gfm`、`remark-rehype`、`space-separated-tokens`、`stringify-entities`、`trim-lines`、`unist-util-position`、`unist-util-stringify-position`、`unist-util-visit`、`unist-util-visit-parents`、`vfile-message`、`zwitch`

以第一個套件（`bail`）的授權檔為準：

```text
(The MIT License)

Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### 全文 4：MIT

適用：`csstype`

以第一個套件（`csstype`）的授權檔為準：

```text
Copyright (c) 2017-2018 Fredrik Nicol

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 全文 5：MIT

適用：`dequal`、`extend`、`ms`、`react-markdown`、`style-to-object`

以第一個套件（`dequal`）的授權檔為準：

```text
The MIT License (MIT)

Copyright (c) Luke Edwards <luke.edwards05@gmail.com> (lukeed.com)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

### 全文 6：MIT

適用：`escape-string-regexp`、`is-plain-obj`、`react`、`react-dom`、`scheduler`

以第一個套件（`escape-string-regexp`）的授權檔為準：

```text
MIT License

Copyright (c) Sindre Sorhus <sindresorhus@gmail.com> (https://sindresorhus.com)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### 全文 7：MIT

適用：`html-url-attributes`、`remark-parse`、`remark-stringify`、`trough`、`unified`、`vfile`

以第一個套件（`html-url-attributes`）的授權檔為準：

```text
(The MIT License)

Copyright (c) Titus Wormer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

### 全文 8：MIT

適用：`unist-util-is`

以第一個套件（`unist-util-is`）的授權檔為準：

```text
(The MIT license)

Copyright (c) 2015 Titus Wormer <tituswormer@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## 四、Python 後端依賴

資料來源：`pyproject.toml`、鎖檔 `uv.lock`（共 24 個第三方套件，下載來源都是 PyPI 官方 index，`https://pypi.org/simple`），以及 `.venv` 裡已安裝套件的 `*.dist-info`（`METADATA` 與授權檔）。套件由本 repo 以 `uv sync` 安裝並產生鎖檔，沒有複製其他專案的鎖檔或虛擬環境。授權標示以各套件宣告的為準，沒有另外做法律判斷。

### 4.1 隨後端發布的套件（14 個）

由 `fastapi` 與 `uvicorn` 往下展開的相依。授權分布：MIT 8 個、BSD-3-Clause 4 個、Apache-2.0 1 個、PSF-2.0 1 個。

- `pydantic-core` 是編譯過的 Rust 擴充模組；它的 wheel 裡只附 pydantic 自己的授權檔，沒有附它所用的 Rust 套件的授權聲明，本檔沒有核對那一層。
- `fastapi` 依賴 `opentelemetry-api`（只是遙測介面，不含傳送功能）。本專案在建立 app 時明確關閉內建遙測（NFR-4），不裝 `opentelemetry-sdk` 與任何匯出器。

#### annotated-doc 0.0.6

- 授權：MIT（全文 1）
- 原始碼：https://github.com/fastapi/annotated-doc
- PyPI：https://pypi.org/project/annotated-doc/0.0.6/
- 版權：Copyright (c) 2025 Sebastián Ramírez

#### annotated-types 0.8.0

- 授權：MIT（全文 1）
- 原始碼：https://github.com/annotated-types/annotated-types
- PyPI：https://pypi.org/project/annotated-types/0.8.0/
- 版權：Copyright (c) 2022 the contributors

#### anyio 4.16.0

- 授權：MIT（全文 1）
- 原始碼：https://github.com/agronholm/anyio
- PyPI：https://pypi.org/project/anyio/4.16.0/
- 版權：Copyright (c) 2018 Alex Grönholm

#### click 8.5.1

- 授權：BSD-3-Clause（全文 2）
- 原始碼：https://github.com/pallets/click/
- PyPI：https://pypi.org/project/click/8.5.1/
- 版權：Copyright 2014 Pallets

#### fastapi 0.162.5（直接依賴）

- 授權：MIT（全文 1）
- 原始碼：https://github.com/fastapi/fastapi
- PyPI：https://pypi.org/project/fastapi/0.162.5/
- 版權：Copyright (c) 2018 Sebastián Ramírez

#### h11 0.16.0

- 授權：MIT（全文 1）
- 原始碼：https://github.com/python-hyper/h11
- PyPI：https://pypi.org/project/h11/0.16.0/
- 版權：Copyright (c) 2016 Nathaniel J. Smith <njs@pobox.com> and other contributors

#### idna 3.20

- 授權：BSD-3-Clause（全文 4）
- 原始碼：https://github.com/kjd/idna
- PyPI：https://pypi.org/project/idna/3.20/
- 版權：Copyright (c) 2013-2026, Kim Davies and contributors.

#### opentelemetry-api 1.45.2

- 授權：Apache-2.0（全文 5）
- 原始碼：https://github.com/open-telemetry/opentelemetry-python
- PyPI：https://pypi.org/project/opentelemetry-api/1.45.2/
- 版權：授權檔是未填版權人的標準範本，沒有單獨的版權行。

#### pydantic 2.14.3

- 授權：MIT（全文 1）
- 原始碼：https://github.com/pydantic/pydantic
- PyPI：https://pypi.org/project/pydantic/2.14.3/
- 版權：Copyright (c) 2017 to present Pydantic Services Inc. and individual contributors.

#### pydantic-core 2.50.4

- 授權：MIT（全文 1）
- 原始碼：https://github.com/pydantic/pydantic
- PyPI：https://pypi.org/project/pydantic-core/2.50.4/
- 版權：Copyright (c) 2022 Samuel Colvin

#### starlette 1.10.0

- 授權：BSD-3-Clause（全文 3）
- 原始碼：https://github.com/Kludex/starlette
- PyPI：https://pypi.org/project/starlette/1.10.0/
- 版權：Copyright © 2018, [Encode OSS Ltd](https://www.encode.io/).

#### typing-extensions 4.16.0

- 授權：PSF-2.0（全文 10）
- 原始碼：https://github.com/python/typing_extensions
- PyPI：https://pypi.org/project/typing-extensions/4.16.0/
- 版權：Copyright (c) 1991 - 1995, Stichting Mathematisch Centrum Amsterdam,

#### typing-inspection 0.4.5

- 授權：MIT（全文 11）
- 原始碼：https://github.com/pydantic/typing-inspection
- PyPI：https://pypi.org/project/typing-inspection/0.4.5/
- 版權：Copyright (c) Pydantic Services Inc. 2025 to present

#### uvicorn 0.54.0（直接依賴）

- 授權：BSD-3-Clause（全文 3）
- 原始碼：https://github.com/Kludex/uvicorn
- PyPI：https://pypi.org/project/uvicorn/0.54.0/
- 版權：Copyright © 2017-present, [Encode OSS Ltd](https://www.encode.io/).

### 4.2 只在開發與測試時使用的套件（10 個）

由 `pytest` 與 `httpx2`（`pyproject.toml` 的 `dev` 群組）展開、且不屬於上一節的套件；不隨後端發布。授權分布：MIT 4 個、BSD-3-Clause 4 個、Apache-2.0 OR BSD-2-Clause 1 個、BSD-2-Clause 1 個。直接的開發依賴是 `httpx2`、`pytest`（它們本身另外列在這一節，不在 4.1）。

#### colorama 0.4.6

- 授權：BSD-3-Clause（全文 12）。套件只宣告分類「BSD License」，沒有標 SPDX 代號；依授權條文（三個條款）判斷為三條款版。
- 原始碼：https://github.com/tartley/colorama
- PyPI：https://pypi.org/project/colorama/0.4.6/
- 版權：Copyright (c) 2010 Jonathan Hartley
- 只在 Windows 安裝（鎖檔標記 `sys_platform == 'win32'`，是 `pytest` 的相依），本機（Linux）沒有安裝。授權取自 PyPI 上的官方 wheel，下載後核對 SHA-256 與鎖檔相同（2026-11-15）。

#### httpcore2 2.16.0

- 授權：BSD-3-Clause（全文 3）
- 原始碼：https://github.com/pydantic/httpx2/blob/main/src/httpcore2
- PyPI：https://pypi.org/project/httpcore2/2.16.0/
- 版權：Copyright © 2026 to present Pydantic Services Inc. and individual contributors.
- 版權：Copyright © 2020, [Encode OSS Ltd](https://www.encode.io/).

#### httpx2 2.16.0（直接依賴）

- 授權：BSD-3-Clause（全文 3）
- 原始碼：https://github.com/pydantic/httpx2
- PyPI：https://pypi.org/project/httpx2/2.16.0/
- 版權：Copyright © 2026 to present Pydantic Services Inc. and individual contributors.
- 版權：Copyright © 2019, [Encode OSS Ltd](https://www.encode.io/).

#### httpx2-jsfetch 1.0

- 授權：BSD-3-Clause（全文 3）
- 原始碼：套件沒有標示（授權檔與 `httpx2` 逐字相同，同屬 Pydantic 的 httpx2 專案）
- PyPI：https://pypi.org/project/httpx2-jsfetch/1.0/
- 版權：Copyright © 2026 to present Pydantic Services Inc. and individual contributors.
- 版權：Copyright © 2019, [Encode OSS Ltd](https://www.encode.io/).
- 只在 Emscripten（瀏覽器內的 Python，例如 Pyodide）安裝（鎖檔標記 `sys_platform == 'emscripten'`，是 `httpx2` 的相依），本機沒有安裝。授權取自 PyPI 上的官方 wheel，下載後核對 SHA-256 與鎖檔相同（2026-11-15）。

#### iniconfig 2.3.1

- 授權：MIT（全文 1）
- 原始碼：https://github.com/pytest-dev/iniconfig
- PyPI：https://pypi.org/project/iniconfig/2.3.1/
- 版權：Copyright (c) 2010 - 2023 Holger Krekel and others

#### packaging 26.3

- 授權：Apache-2.0 OR BSD-2-Clause（全文 6、7、8）
- 原始碼：https://github.com/pypa/packaging
- PyPI：https://pypi.org/project/packaging/26.3/
- 版權：Copyright (c) Donald Stufft and individual contributors.

#### pluggy 1.7.0

- 授權：MIT（全文 1）
- 原始碼：https://github.com/pytest-dev/pluggy
- PyPI：https://pypi.org/project/pluggy/1.7.0/
- 版權：Copyright (c) 2015 holger krekel (rather uses bitbucket/hpk42)

#### pygments 2.21.0

- 授權：BSD-2-Clause（全文 9）
- 原始碼：https://github.com/pygments/pygments
- PyPI：https://pypi.org/project/pygments/2.21.0/
- 版權：Copyright (c) 2006-2022 by the respective authors (see AUTHORS file).
- 版權人清單：該套件授權檔旁的 `AUTHORS` 檔（未收錄於本檔）。

#### pytest 9.2.0（直接依賴）

- 授權：MIT（全文 1）
- 原始碼：https://github.com/pytest-dev/pytest
- PyPI：https://pypi.org/project/pytest/9.2.0/
- 版權：Copyright (c) 2004 Holger Krekel and others

#### truststore 0.10.5

- 授權：MIT（全文 1）
- 原始碼：https://github.com/sethmlarson/truststore
- PyPI：https://pypi.org/project/truststore/0.10.5/
- 版權：Copyright (c) 2022 Seth Michael Larson

### 4.3 Python 套件授權全文

同一編號的授權文字相同（除了各套件自己的版權行，已列在上面，以及空白排版）。全文取自「全文所列第一個套件」已安裝的授權檔，內容不改。

#### 全文 1

適用：`annotated-doc`、`annotated-types`、`anyio`、`fastapi`、`h11`、`iniconfig`、`pluggy`、`pydantic`、`pydantic-core`、`pytest`、`truststore`

取自 `annotated-doc` 的 `LICENSE`：

```text
The MIT License (MIT)

Copyright (c) 2025 Sebastián Ramírez

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

#### 全文 2

適用：`click`

取自 `click` 的 `LICENSE.txt`：

```text
Copyright 2014 Pallets

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1.  Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

2.  Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

3.  Neither the name of the copyright holder nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

#### 全文 3

適用：`httpcore2`、`httpx2`、`httpx2-jsfetch`、`starlette`、`uvicorn`

取自 `httpcore2` 的 `LICENSE.md`：

```text
Copyright © 2026 to present Pydantic Services Inc. and individual contributors.
Copyright © 2020, [Encode OSS Ltd](https://www.encode.io/).
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

#### 全文 4

適用：`idna`

取自 `idna` 的 `LICENSE.md`：

```text
BSD 3-Clause License

Copyright (c) 2013-2026, Kim Davies and contributors.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

#### 全文 5

適用：`opentelemetry-api`

取自 `opentelemetry-api` 的 `LICENSE`：

```text
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "[]"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright [yyyy] [name of copyright owner]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
```

#### 全文 6

適用：`packaging`

取自 `packaging` 的 `LICENSE`：

```text
This software is made available under the terms of *either* of the licenses
found in LICENSE.APACHE or LICENSE.BSD. Contributions to this software is made
under the terms of *both* these licenses.
```

#### 全文 7

適用：`packaging`

取自 `packaging` 的 `LICENSE.APACHE`：

```text
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS
```

#### 全文 8

適用：`packaging`

取自 `packaging` 的 `LICENSE.BSD`：

```text
Copyright (c) Donald Stufft and individual contributors.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

#### 全文 9

適用：`pygments`

取自 `pygments` 的 `LICENSE`：

```text
Copyright (c) 2006-2022 by the respective authors (see AUTHORS file).
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

#### 全文 10

適用：`typing-extensions`

取自 `typing-extensions` 的 `LICENSE`：

```text
A. HISTORY OF THE SOFTWARE
==========================

Python was created in the early 1990s by Guido van Rossum at Stichting
Mathematisch Centrum (CWI, see https://www.cwi.nl) in the Netherlands
as a successor of a language called ABC.  Guido remains Python's
principal author, although it includes many contributions from others.

In 1995, Guido continued his work on Python at the Corporation for
National Research Initiatives (CNRI, see https://www.cnri.reston.va.us)
in Reston, Virginia where he released several versions of the
software.

In May 2000, Guido and the Python core development team moved to
BeOpen.com to form the BeOpen PythonLabs team.  In October of the same
year, the PythonLabs team moved to Digital Creations, which became
Zope Corporation.  In 2001, the Python Software Foundation (PSF, see
https://www.python.org/psf/) was formed, a non-profit organization
created specifically to own Python-related Intellectual Property.
Zope Corporation was a sponsoring member of the PSF.

All Python releases are Open Source (see https://opensource.org for
the Open Source Definition).  Historically, most, but not all, Python
releases have also been GPL-compatible; the table below summarizes
the various releases.

    Release         Derived     Year        Owner       GPL-
                    from                                compatible? (1)

    0.9.0 thru 1.2              1991-1995   CWI         yes
    1.3 thru 1.5.2  1.2         1995-1999   CNRI        yes
    1.6             1.5.2       2000        CNRI        no
    2.0             1.6         2000        BeOpen.com  no
    1.6.1           1.6         2001        CNRI        yes (2)
    2.1             2.0+1.6.1   2001        PSF         no
    2.0.1           2.0+1.6.1   2001        PSF         yes
    2.1.1           2.1+2.0.1   2001        PSF         yes
    2.1.2           2.1.1       2002        PSF         yes
    2.1.3           2.1.2       2002        PSF         yes
    2.2 and above   2.1.1       2001-now    PSF         yes

Footnotes:

(1) GPL-compatible doesn't mean that we're distributing Python under
    the GPL.  All Python licenses, unlike the GPL, let you distribute
    a modified version without making your changes open source.  The
    GPL-compatible licenses make it possible to combine Python with
    other software that is released under the GPL; the others don't.

(2) According to Richard Stallman, 1.6.1 is not GPL-compatible,
    because its license has a choice of law clause.  According to
    CNRI, however, Stallman's lawyer has told CNRI's lawyer that 1.6.1
    is "not incompatible" with the GPL.

Thanks to the many outside volunteers who have worked under Guido's
direction to make these releases possible.


B. TERMS AND CONDITIONS FOR ACCESSING OR OTHERWISE USING PYTHON
===============================================================

Python software and documentation are licensed under the
Python Software Foundation License Version 2.

Starting with Python 3.8.6, examples, recipes, and other code in
the documentation are dual licensed under the PSF License Version 2
and the Zero-Clause BSD license.

Some software incorporated into Python is under different licenses.
The licenses are listed with code falling under that license.


PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
--------------------------------------------

1. This LICENSE AGREEMENT is between the Python Software Foundation
("PSF"), and the Individual or Organization ("Licensee") accessing and
otherwise using this software ("Python") in source or binary form and
its associated documentation.

2. Subject to the terms and conditions of this License Agreement, PSF hereby
grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
analyze, test, perform and/or display publicly, prepare derivative works,
distribute, and otherwise use Python alone or in any derivative version,
provided, however, that PSF's License Agreement and PSF's notice of copyright,
i.e., "Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023 Python Software Foundation;
All Rights Reserved" are retained in Python alone or in any derivative version
prepared by Licensee.

3. In the event Licensee prepares a derivative work that is based on
or incorporates Python or any part thereof, and wants to make
the derivative work available to others as provided herein, then
Licensee hereby agrees to include in any such work a brief summary of
the changes made to Python.

4. PSF is making Python available to Licensee on an "AS IS"
basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
INFRINGE ANY THIRD PARTY RIGHTS.

5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6. This License Agreement will automatically terminate upon a material
breach of its terms and conditions.

7. Nothing in this License Agreement shall be deemed to create any
relationship of agency, partnership, or joint venture between PSF and
Licensee.  This License Agreement does not grant permission to use PSF
trademarks or trade name in a trademark sense to endorse or promote
products or services of Licensee, or any third party.

8. By copying, installing or otherwise using Python, Licensee
agrees to be bound by the terms and conditions of this License
Agreement.


BEOPEN.COM LICENSE AGREEMENT FOR PYTHON 2.0
-------------------------------------------

BEOPEN PYTHON OPEN SOURCE LICENSE AGREEMENT VERSION 1

1. This LICENSE AGREEMENT is between BeOpen.com ("BeOpen"), having an
office at 160 Saratoga Avenue, Santa Clara, CA 95051, and the
Individual or Organization ("Licensee") accessing and otherwise using
this software in source or binary form and its associated
documentation ("the Software").

2. Subject to the terms and conditions of this BeOpen Python License
Agreement, BeOpen hereby grants Licensee a non-exclusive,
royalty-free, world-wide license to reproduce, analyze, test, perform
and/or display publicly, prepare derivative works, distribute, and
otherwise use the Software alone or in any derivative version,
provided, however, that the BeOpen Python License is retained in the
Software, alone or in any derivative version prepared by Licensee.

3. BeOpen is making the Software available to Licensee on an "AS IS"
basis.  BEOPEN MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, BEOPEN MAKES NO AND
DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF THE SOFTWARE WILL NOT
INFRINGE ANY THIRD PARTY RIGHTS.

4. BEOPEN SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF THE
SOFTWARE FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS
AS A RESULT OF USING, MODIFYING OR DISTRIBUTING THE SOFTWARE, OR ANY
DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

5. This License Agreement will automatically terminate upon a material
breach of its terms and conditions.

6. This License Agreement shall be governed by and interpreted in all
respects by the law of the State of California, excluding conflict of
law provisions.  Nothing in this License Agreement shall be deemed to
create any relationship of agency, partnership, or joint venture
between BeOpen and Licensee.  This License Agreement does not grant
permission to use BeOpen trademarks or trade names in a trademark
sense to endorse or promote products or services of Licensee, or any
third party.  As an exception, the "BeOpen Python" logos available at
http://www.pythonlabs.com/logos.html may be used according to the
permissions granted on that web page.

7. By copying, installing or otherwise using the software, Licensee
agrees to be bound by the terms and conditions of this License
Agreement.


CNRI LICENSE AGREEMENT FOR PYTHON 1.6.1
---------------------------------------

1. This LICENSE AGREEMENT is between the Corporation for National
Research Initiatives, having an office at 1895 Preston White Drive,
Reston, VA 20191 ("CNRI"), and the Individual or Organization
("Licensee") accessing and otherwise using Python 1.6.1 software in
source or binary form and its associated documentation.

2. Subject to the terms and conditions of this License Agreement, CNRI
hereby grants Licensee a nonexclusive, royalty-free, world-wide
license to reproduce, analyze, test, perform and/or display publicly,
prepare derivative works, distribute, and otherwise use Python 1.6.1
alone or in any derivative version, provided, however, that CNRI's
License Agreement and CNRI's notice of copyright, i.e., "Copyright (c)
1995-2001 Corporation for National Research Initiatives; All Rights
Reserved" are retained in Python 1.6.1 alone or in any derivative
version prepared by Licensee.  Alternately, in lieu of CNRI's License
Agreement, Licensee may substitute the following text (omitting the
quotes): "Python 1.6.1 is made available subject to the terms and
conditions in CNRI's License Agreement.  This Agreement together with
Python 1.6.1 may be located on the internet using the following
unique, persistent identifier (known as a handle): 1895.22/1013.  This
Agreement may also be obtained from a proxy server on the internet
using the following URL: http://hdl.handle.net/1895.22/1013".

3. In the event Licensee prepares a derivative work that is based on
or incorporates Python 1.6.1 or any part thereof, and wants to make
the derivative work available to others as provided herein, then
Licensee hereby agrees to include in any such work a brief summary of
the changes made to Python 1.6.1.

4. CNRI is making Python 1.6.1 available to Licensee on an "AS IS"
basis.  CNRI MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, CNRI MAKES NO AND
DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON 1.6.1 WILL NOT
INFRINGE ANY THIRD PARTY RIGHTS.

5. CNRI SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
1.6.1 FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON 1.6.1,
OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6. This License Agreement will automatically terminate upon a material
breach of its terms and conditions.

7. This License Agreement shall be governed by the federal
intellectual property law of the United States, including without
limitation the federal copyright law, and, to the extent such
U.S. federal law does not apply, by the law of the Commonwealth of
Virginia, excluding Virginia's conflict of law provisions.
Notwithstanding the foregoing, with regard to derivative works based
on Python 1.6.1 that incorporate non-separable material that was
previously distributed under the GNU General Public License (GPL), the
law of the Commonwealth of Virginia shall govern this License
Agreement only as to issues arising under or with respect to
Paragraphs 4, 5, and 7 of this License Agreement.  Nothing in this
License Agreement shall be deemed to create any relationship of
agency, partnership, or joint venture between CNRI and Licensee.  This
License Agreement does not grant permission to use CNRI trademarks or
trade name in a trademark sense to endorse or promote products or
services of Licensee, or any third party.

8. By clicking on the "ACCEPT" button where indicated, or by copying,
installing or otherwise using Python 1.6.1, Licensee agrees to be
bound by the terms and conditions of this License Agreement.

        ACCEPT


CWI LICENSE AGREEMENT FOR PYTHON 0.9.0 THROUGH 1.2
--------------------------------------------------

Copyright (c) 1991 - 1995, Stichting Mathematisch Centrum Amsterdam,
The Netherlands.  All rights reserved.

Permission to use, copy, modify, and distribute this software and its
documentation for any purpose and without fee is hereby granted,
provided that the above copyright notice appear in all copies and that
both that copyright notice and this permission notice appear in
supporting documentation, and that the name of Stichting Mathematisch
Centrum or CWI not be used in advertising or publicity pertaining to
distribution of the software without specific, written prior
permission.

STICHTING MATHEMATISCH CENTRUM DISCLAIMS ALL WARRANTIES WITH REGARD TO
THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS, IN NO EVENT SHALL STICHTING MATHEMATISCH CENTRUM BE LIABLE
FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

ZERO-CLAUSE BSD LICENSE FOR CODE IN THE PYTHON DOCUMENTATION
----------------------------------------------------------------------

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
```

#### 全文 11

適用：`typing-inspection`

取自 `typing-inspection` 的 `LICENSE`：

```text
MIT License

Copyright (c) Pydantic Services Inc. 2025 to present

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

#### 全文 12

適用：`colorama`

取自 PyPI 上 `colorama` 0.4.6 官方 wheel 的 `LICENSE.txt`（SHA-256 已與鎖檔核對）：

```text
Copyright (c) 2010 Jonathan Hartley
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holders, nor those of its contributors
  may be used to endorse or promote products derived from this software without
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
