# Plan 095

## 095.1 Runtime Event Detail Rows

- Capture RED frontend test for missing runtime node event formatter.
- Add a formatter that converts `node.events` into safe evidence rows.
- Render event rows in the workflow node detail panel.
- Extend browser UAT by injecting runtime-v2 event evidence into debug detail.

## Gates

- RED frontend test before implementation.
- Green focused workflow debug frontend tests.
- Green frontend rem gate, full frontend unit, and build.
- Green browser UAT with screenshot evidence.
