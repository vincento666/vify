# 046 Condition Card Label Cleanup UAT

Date: 2026-06-08

Target: http://127.0.0.1:5173/workflows/4685/canvas

Checks:

- Reloaded the current in-app browser workflow canvas.
- Verified the selector card only renders branch blocks.
- Verified no visible `condition-source-port-label` elements remain.
- Verified condition source handles still expose branch metadata through `data-branch-label`.
- Verified branch names are not duplicated in the card text.
- Verified each condition source endpoint is vertically centered to its branch block.

Observed card text:

```text
选择器_1如果VIP 客户否则普通客户
```

Observed endpoint alignment:

```text
如果 VIP 客户 delta=0
否则 普通客户 delta=0
```

Screenshot:

- `screenshots/browser-uat-label-cleanup.png`
- `screenshots/browser-uat-alignment.png`
