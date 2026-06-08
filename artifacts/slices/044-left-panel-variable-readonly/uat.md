## 044 Left Panel Variable Readonly UAT

- URL: `http://127.0.0.1:5173/chatflows/create`
- Scenario: open the Chatflow create canvas, click the left settings panel runtime context variable `{{sys.query}}`.
- Expected: the left panel behaves as a readonly runtime context reference list; clicking a variable does not auto-select the END node and does not mutate the END response content.
- Result: PASS.
- Screenshot: `screenshots/left-panel-variables.png`

Gate summary:
- RED: `red.txt` captured the previous side effect where clicking `{{sys.query}}` opened the END node config panel.
- E2E/UAT: `e2e-readonly.txt`
- Collapse regression: `e2e-collapse-regression.txt`
- Unit/rem: `unit-rem.txt`, `unit-full.txt`
- Build: `build.txt`
