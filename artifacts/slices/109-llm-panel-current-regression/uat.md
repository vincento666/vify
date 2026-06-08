# 109 LLM Panel Current Regression

## Scope

- Model selector opens from the model display control and supports search.
- Model settings opens a floating parameter panel with long range sliders and compact numeric steppers.
- Model and skill pickers are floating overlays and do not reflow panel sections.
- LLM skill picker uses tabbed resource selection instead of the old mixed registry list.
- Chatflow LLM prompt fields use inline `{{` variable completion and no separate variable button.
- Callable skill runtime policy remains persisted in config, while ordinary panel hides old tool policy fields.

## RED

- `e2e-workflow-model-parameter-slider.txt`: initial browser click hit a transient detached `模型设置` button while the config panel was still settling.
- `e2e-workflow-model-selector-search.txt`: initial browser click hit a transient detached model display button while the config panel was still settling.
- `e2e-workflow-llm-callable-skills.txt`: old assertion expected `工具选择` / `最大调用轮次` / `工具结果` in the ordinary panel.
- `e2e-workflow-llm-callable-skills-after-fix.txt`: browser E2E still waited on a real LLM node run, which is not stable as a UI gate.

## GREEN

- `unit-frontend.txt`: node config + workflow canvas rem governance, 24 tests passed.
- `integration-llm.txt`: LLM callable skills and model parameters backend integration, 3 tests passed.
- `e2e-workflow-model-parameter-slider-after-fix.txt`: PASS workflow model parameter slider 028.
- `e2e-workflow-model-selector-search-after-fix.txt`: PASS workflow model selector search 028.
- `e2e-workflow-floating-selectors.txt`: PASS workflow floating selectors e2e.
- `e2e-workflow-llm-resources.txt`: PASS workflow LLM resource context e2e.
- `e2e-workflow-llm-callable-skills-after-stabilize.txt`: PASS workflow LLM callable skills e2e.
- `e2e-chatflow-llm-selector-prompt-hardening.txt`: PASS 025.4a LLM selector and prompt hardening e2e.
- `e2e-chatflow-llm-panel-parity.txt`: PASS 025.4 chatflow llm panel parity e2e.

## Product Notes

- Browser E2E verifies UI and persistence; live/fake LLM runtime behavior is owned by backend integration tests.
- The normal LLM config panel intentionally hides old tool policy controls. They remain config/runtime values and are covered by integration tests.
