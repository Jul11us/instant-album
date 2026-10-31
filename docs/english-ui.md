# English interface / 英文界面

The app ships one Chinese source. Choosing English replaces already-rendered interface text through a small string table (`src/i18n.js`) and keeps watching the page for newly rendered text with a `MutationObserver`. Nothing about the photos, drafts, backups or exports changes language on disk; only what is shown and the labels inside exported metadata files follow the switch.

界面只有一份中文源码。英文模式不改模板，而是用 `src/i18n.js` 里的词表替换已经显示的文字，并用 `MutationObserver` 补上之后渲染的内容。照片、草稿、备份和导出文件本身不变，只有显示的界面文字会切换。

## What is covered / 覆盖范围

- Home, scan, framing confirmation, scan checks and failure recovery
- Editing: filters, adjustments, frames, caption, date stamp, memories and backs
- Export options, ZIP/memories file, album pages, library and full backup
- Shooting checks and batch apply
- Camera selection, and the English note on top of the shooting guide

Camera-specific recommendations, the long shooting tips and 3D part descriptions are still Chinese. The guide and the 3D detail panel say so in English. This is deliberate: those are sourced product facts and should be translated carefully rather than word by word.

机型推荐参数、详细拍摄建议和 3D 零件说明仍是中文，页面顶部会注明。这部分有具体来源，应该逐条核对后再翻，不先机翻。

## Rules for new text / 新文字怎么写

1. Write the user-facing string in Chinese in `src/app.html`, as before.
2. Add the exact Chinese string and its English value to `EN` in `src/i18n.js`.
3. If the string contains a number, name or file name, add a pattern to `EN_RULES` instead. Patterns run only when no exact match exists.
4. Do not add i18n attributes to user content. Captions, stories and album names are skipped through `contenteditable` / `data-no-i18n`.
5. Strings that only exist in English (such as the notice above the guide) are written directly in `LANG === 'en'` branches.

Dynamic text set after a render is picked up automatically. Text inside `<canvas>` is not; use `tr()` in the drawing code when it should follow the language.

## Preference / 语言选择

The choice is stored in `localStorage` as `tiejin.lang` (`en` or `zh`). The default is Chinese, so existing Chinese users and the regression tests are unaffected. Clearing site data returns the app to Chinese.

`tests/test_batch_and_lang.py` checks the switch, persistence across reloads, switching back, the four first-run checks and batch apply.
