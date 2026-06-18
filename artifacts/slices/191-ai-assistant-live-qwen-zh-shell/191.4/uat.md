# UAT 191.4

- Playwright browser UAT passed with `PASS ai assistant shell e2e`.
- Screenshot:
  `artifacts/slices/191-ai-assistant-live-qwen-zh-shell/191.4/ai-assistant-one-screen-qwen-uat.png`.
- In-app browser read-only check:
  - page-level vertical overflow: `0`;
  - composer visible inside viewport: `true`;
  - clear history/context button is in center header: `true`;
  - per-session delete icons present: `23`;
  - Qwen3.5-27B label visible: `true`.
- Real OpenRouter Qwen3.5-27B smoke passed via environment-gated test.
