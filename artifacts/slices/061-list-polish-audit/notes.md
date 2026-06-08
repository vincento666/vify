# 061 List Polish Audit

Scope:
- Fixed workflow/chatflow list table columns that collapsed when Element Plus parsed rem strings as tiny pixel integers.
- Kept user-facing list copy Chinese: 工作流 / 对话流 tabs, 新建工作流 / 新建对话流, 查看 / 画布 / 删除.
- Hardened the E2E to seed its own workflow/chatflow rows and assert compact row height plus visible action buttons.

Red:
- `red-visual-diagnosis.txt` records the initial UAT failure: row height 362 and narrow columns 6/11/14.

Gates:
- `HIFY_E2E_SCREENSHOT=artifacts/slices/061-list-polish-audit/screenshots/workflow-chatflow-list-polish.png rtk node frontend/e2e/workflow-chatflow-list-polish.mjs` -> `e2e-workflow-chatflow-list-polish.txt`
- `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` -> `rem.txt`
- `rtk npm --prefix frontend run test:unit` -> `unit-full.txt`
- `rtk npm --prefix frontend run build` -> `build.txt`
