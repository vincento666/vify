# 006.2 Document Upload UAT

Date: 2026-05-31

## Scope

- Open the real frontend `/knowledge/1/documents` page.
- Upload a local TXT document through the visible upload dialog.
- Verify the document appears in the table with `待处理` state.
- Verify browser-side API returns the uploaded document.

## Seed Data

- Knowledge base: `UAT KB 0062`
- File: `artifacts/slices/006-knowledge-mock-replica/006.2/guide.txt`

## Result

- Browser UAT: passed.
- Document: `guide.txt`
- Status: `PENDING`
- Screenshot: `output/playwright/0062-document-upload.png`

## Gate Evidence

- RED: `artifacts/slices/006-knowledge-mock-replica/006.2/red.txt`
- Focused backend tests: `artifacts/slices/006-knowledge-mock-replica/006.2/backend.txt`
- Ruff: `artifacts/slices/006-knowledge-mock-replica/006.2/ruff.txt`
- Mypy: `artifacts/slices/006-knowledge-mock-replica/006.2/mypy.txt`
- Frontend unit: `artifacts/slices/006-knowledge-mock-replica/006.2/frontend-unit.txt`
- Frontend build: `artifacts/slices/006-knowledge-mock-replica/006.2/frontend-build.txt`
