# UAT: 193.25 Scrollbar Gutter Stability

## Scope

- Prevent the center AI Assistant message stream from shifting horizontally when
  expanded run echoes make the vertical scrollbar appear.
- Keep the scrollbar close to content by reducing the stream's right padding.

## Evidence

- RED: `red-scrollbar-gutter.txt`
- Focused green: `unit-scrollbar-gutter.txt`
- AI Assistant + rem gate: `unit-rem.txt`
- Full frontend unit: `frontend-unit-full.txt`
- Frontend build: `frontend-build.txt`
- In-app browser measurement: `in-app-browser-uat.json`
- In-app browser screenshot:
  `screenshots/scrollbar-gutter-stable-expanded.png`
- Diff check: `git-diff-check.txt`

## Browser UAT Notes

- Opened `http://127.0.0.1:5173/ai-assistant` in the Codex in-app browser.
- Selected the existing `命令回显 UAT` session.
- Measured the center stream before expanding run echoes:
  `clientWidth = 303`, `scrollbarGutter = stable`, `hasOverflow = false`.
- Expanded all run/event echo headers until the stream overflowed:
  `scrollHeight = 915`, `clientHeight = 593`, `hasOverflow = true`.
- Re-measured the center stream after expansion:
  `clientWidth = 303`, `clientWidthDelta = 0`,
  `overflowY = auto`, `overflowX = hidden`, `paddingRight = 5.25px`.

## Remaining Risk

- `scrollbar-gutter` behavior depends on browser support. The target Codex
  in-app browser/Chromium path is covered by UAT.
