# 第三方軟體聲明（THIRD_PARTY_NOTICES）

本檔記錄不是本專案自己撰寫、但被本 repo 使用或會隨網頁介面一起發布的第三方軟體：來源、版本與授權。本專案自己的程式碼授權見 `LICENSE`。從舊專案匯入的檔案不記在這裡，記在 `PROVENANCE.md`。

## 範圍與限制

- 本檔目前只涵蓋**網頁介面（`frontend/`）的 npm 套件**。Python 後端依賴（`pyproject.toml`、`uv.lock`）還沒有列入，發布安裝包前要補。
- `frontend/` 沒有字型、圖片或其他素材：除程式碼與 `package.json`、`package-lock.json` 外，只有 `index.html` 與 `src/styles.css`，都是本專案自己寫的。
- 資料來源是 `frontend/package-lock.json`（`lockfileVersion` 3）與已安裝的 `frontend/node_modules/` 裡各套件的授權檔，不是對打包結果做的內容分析。「隨網頁介面發布」指鎖檔裡沒有標為開發用（`dev`）的套件，是可能被打包進去的範圍；實際被打進 `app/web/static/` 的只會是其中一部分。
- 鎖檔裡全部 233 個套件的下載來源都是 npm 官方 registry（`registry.npmjs.org`），每一筆都有完整性雜湊（`integrity`）。套件是在本 repo 以 `npm` 安裝並產生鎖檔，沒有複製其他專案的鎖檔或 `node_modules`。
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
