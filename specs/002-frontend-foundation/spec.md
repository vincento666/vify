# Spec 002: Frontend Foundation

## Goal

Prepare the existing Vue frontend to run against the Python backend without
changing user-visible routes or the API envelope.

## Slices

| Slice | User/Developer Value | Acceptance Gates |
|------|----------------------|------------------|
| 002.1 Frontend dependency hygiene | Developer can install/build frontend without committed artifacts | RED: build/e2e setup test fails; Unit: N/A; Integration: `npm build`; E2E: home smoke; UAT: browser opens app |
| 002.2 API client compatibility | Axios client still unwraps `{code,message,data}` | RED: client contract test fails; Unit: request helper tests; Integration: mock API; E2E: health page/API smoke; UAT: visible success/error toast |
| 002.3 One-command local startup | Frontend and backend run together for UAT | RED: smoke script fails; Unit: N/A; Integration: dev script; E2E: browser reaches app; UAT: start/stop instructions verified |

## Browser UAT

Open the frontend root, navigate to provider/agent/chat pages, and confirm no
blank screen or API base-path mismatch.
