## Browser UAT

- Target: `http://127.0.0.1:5173/chatflows/create`
- Flow: add an LLM node, add one local input variable, type `{` in the system prompt, and inspect the inline variable suggestion picker.
- Result: the variable candidate renders `input_1` in full, the `String` badge is compact and aligned next to the variable name, and no `in...` truncation or stretched type background appears.
- Screenshot: `screenshots/e2e-inline-variable-layout.png`

Note: in-app Browser Playwright text entry was blocked by the runtime message `Browser Use virtual clipboard is not installed`; visual UAT was completed through the Playwright E2E browser screenshot for the same page and interaction.
