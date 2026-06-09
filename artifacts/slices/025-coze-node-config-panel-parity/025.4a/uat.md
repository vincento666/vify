# 025.4a Browser UAT

Date: 2026-06-05

Target: `http://127.0.0.1:5173/chatflows/1719/canvas`

Verified:

- Clicking the model name opens the model selector, captured in `screenshots/uat-model-selector.png`.
- Clicking the gear opens the model parameter panel, captured in `screenshots/uat-model-parameters.png`.
- Clicking add skill opens resource type tabs and no mixed `workflow-resource-registry` dropdown is present, captured in `screenshots/uat-skill-tabs.png`.
- LLM system/user prompt headers no longer show a separate `变量` button.
- Typing `{{` opens the variable picker in the Playwright E2E gate; screenshot: `screenshots/green-llm-interactions.png`.

Note:

The in-app browser typing channel could not type into the textarea because the Browser Use virtual clipboard is not installed. The inline `{{` behavior passed through the real-browser Playwright E2E and is recorded in `e2e-llm-interactions.txt`.
