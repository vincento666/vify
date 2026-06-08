# 016.2 Browser UAT

Route: `http://127.0.0.1:5173/provider`; action: open provider dialog.

| Width | Root | Component size | Dialog var | Sidebar | Nav icon | Table gap | Dialog visible | Dialog width | Overflow X | Screenshot |
|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1280 | 14px | 2rem | 32.5rem | 192.5px | 14.875px | 14px | true | 520px | 0 | artifacts/slices/016-frontend-rem-scale-governance/016.2-shared-shell-element-bridge/screenshots/provider-dialog-1280.png |
| 1920 | 16px | 2rem | 32.5rem | 220px | 17px | 16px | true | 520px | 0 | artifacts/slices/016-frontend-rem-scale-governance/016.2-shared-shell-element-bridge/screenshots/provider-dialog-1920.png |

Note: provider route still passes dialog width/label-width px overrides; page-level migration belongs to 016.3.
Result: PASS
