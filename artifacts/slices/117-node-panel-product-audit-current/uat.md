## 117 Intent Recognition Branch Node UAT

- RED: `red-intent-branch-node.txt` captured the old card rendering generic input/output rows instead of semantic intent branches.
- Unit: `unit-node-config-canvas.txt` passed node config, canvas control, and rem governance assertions.
- Integration: `integration-intent.txt` passed backend intent-recognition branch routing tests.
- E2E:
  - `e2e-intent-recognition.txt` passed chatflow intent run, node run, card branch rendering, and config panel assertions.
  - `e2e-condition-branch-endpoints.txt` passed condition branch endpoint regression.
- Browser UAT: in-app browser opened a created chatflow canvas and verified:
  - card branches: `意图/退款`, `意图/物流`, `兜底/其他意图`;
  - source handles: `退款`, `物流`, `其他意图`;
  - config panel intent table only exposes `名称 / 描述 / 示例`;
  - raw `默认意图` is not exposed as a business form field.
- Screenshot: `screenshots/in-app-uat-intent-branch-node.png`.
