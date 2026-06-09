## 118 Endpoint Original Size UAT

- RED: `red-unit.txt` confirmed the spec failed while CSS still used `--node-port-dot-size: 0.75rem`.
- Unit: `unit.txt` passed endpoint constants and rem governance assertions.
- E2E: `e2e-endpoint-affordances.txt` and `e2e-endpoint-radius.txt` passed.
- Browser UAT: in-app browser inspected `http://127.0.0.1:5173/chatflows/8121/canvas`.
  - Root font size: `14px`.
  - Static endpoint dot: `0.875rem = 12.25px`, restoring the old 12px visual baseline.
  - Hitbox: `2.625rem = 36.75px`, derived from 3x of the restored baseline.
  - Source port center delta to node right edge: `0.73px`, so line anchoring stays aligned.
- Screenshot: `screenshots/in-app-endpoint-size.png`.
