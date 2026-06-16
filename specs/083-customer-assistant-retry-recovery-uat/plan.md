# Plan 083

## 083.1 Workbench Failed-Task Retry Proposal

- Add a RED browser script with a mocked failed task and no retry proposal
  handler.
- Confirm the RED failure waits for the pending retry action after clicking
  `重试`.
- Add the mocked retry proposal response, refreshed ledger state, and exact API
  body assertions.
- Run node syntax check and browser UAT with screenshot evidence.

## Gates

- RED browser failure before adding the retry proposal mock.
- Green browser UAT.
- Node syntax check.
- No rem gate unless Vue/CSS visual source changes.
