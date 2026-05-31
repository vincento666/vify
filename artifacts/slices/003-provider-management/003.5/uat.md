# UAT 003.5: LLM adapter parser contract

Status: PASS

Browser check:

- URL: `file:///Users/vincento/work/develop/hify/artifacts/slices/003-provider-management/003.5/fixture-report.html`
- Screenshot: `screenshots/fixture-report.png`

Expected user-visible result:

- Fixture report shows parsed OpenAI sync, OpenAI stream, Anthropic, and Ollama responses.

Evidence:

- RED: `red.txt` fails before `llm_adapters.py` exists.
- Unit: `unit.txt` passes parser fixture assertions.
- Integration: `integration.txt` executes all parser fixtures and generates the report.
- E2E: `e2e.txt` marks parser-only E2E as N/A with executable fixture proof.
- Browser UAT: `browser-uat.txt` captures the fixture report in Chromium.
- Quality: `ruff.txt` and `mypy.txt` pass.
