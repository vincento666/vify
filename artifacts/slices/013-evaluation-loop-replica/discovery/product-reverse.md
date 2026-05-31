# 013.0 Product Discovery Baseline

## Deployment Attempt

- Source: `https://github.com/coze-dev/coze-loop`
- Quickstart: `https://github.com/coze-dev/coze-loop/wiki/2.-Quickstart`
- Local prerequisites checked:
  - Docker: available before the compose attempt.
  - Docker Compose: available before the compose attempt.
  - Go: `go1.24.3`, compatible with the Coze Loop quickstart requirement.
- Source clone attempt: `coze-loop-clone.txt`
- Compose config validation: `coze-loop-compose-config.txt`
- Compose start attempt: `coze-loop-compose-up.txt`
- Compose cleanup attempt: `coze-loop-compose-down.txt`

The compose start reached image download but failed before the app became browser-accessible. The recorded blocker was `unexpected EOF` during image pull, followed by local disk pressure (`no space left on device`) when trying to save browser references. Docker/OrbStack was not reliable after the failed pull, so implementation proceeds with the spec-approved fallback: official Coze Loop quickstart/repository evidence plus source-level product structure inspection.

## Browser Evidence

- Official quickstart page screenshot: `coze-loop-quickstart.png`
- Official repository page screenshot: `coze-loop-repo.png`
- Browser capture log: `browser-reference.txt`

## Source-Level Product Signals

The cloned source showed a dedicated evaluation frontend module and backend evaluation module:

- `frontend/apps/cozeloop/src/routes/index.tsx` lazy-loads `@cozeloop/evaluate-pages`.
- `frontend/packages/loop-modules/evaluate/src/pages/experiment/` contains experiment list/detail flows.
- `frontend/packages/loop-modules/evaluate/src/pages/evaluation-set/` contains eval set management flows.
- `frontend/packages/loop-modules/evaluate/src/pages/evaluator/` contains evaluator management flows.
- `backend/modules/evaluation/` contains evaluator, experiment, and evaluation-set services/repositories.

## Hify Product Decisions

- Keep one top-level `评测` entry in the Hify sidebar.
- Keep Experiments, Eval Sets, Evaluators, Run Records, and Compare Analysis as internal tabs.
- Default to Experiments because the user task is validating a target change.
- MVP objects: Eval Set, Eval Case, Evaluator, Experiment, Run, Case Result.
- MVP feedback: score, pass rate, failed count, target output, evaluator reason.
- Hify will copy the task flow and object-action-feedback structure, not Coze Loop branding or pixel styling.
- Hify MVP uses Python 3.12 + FastAPI + SQLAlchemy and synchronous local execution; Coze Loop's Go services, queues, FaaS evaluator runtime, and observability platform remain reference architecture only.

## Page State Adaptation

- Empty state: explain the next action, not raw schema.
- List state: show status, score, pass rate, target, and latest run.
- Create state: order fields by task sequence: target -> eval set -> evaluator -> run.
- Report state: summary first, failed cases next, raw payload last.
- Compare Analysis: visible but unavailable until compare slices are implemented.
