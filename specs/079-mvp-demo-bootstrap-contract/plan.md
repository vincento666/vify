# Plan 079

## 079.1 Seed Verification Contract

- Add a RED integration test for the product seed command and reusable verifier.
- Add `verify_mvp_demo_topology(session, env_text=None)` to the demo seed module.
- Have `scripts/seed_mvp_demo.py` run the verifier after writing env bindings.
- Emit concise, secret-free stdout with story IDs and verification status.
- Save RED/unit/integration evidence and commit.

## 079.2 Seeded Browser Storyline Gate

- Add a browser UAT script that starts from seeded stories and exercises:
  refund + baggage, invoice interruption, and Chatflow block/resume story cards.
- Save screenshots for each story and record the verifier JSON.

## Gates

- RED before implementation.
- Focused integration for seed/verifier.
- Existing 073 seed integration remains green.
- Browser UAT for 079.2.
- Docs and artifacts updated per slice.
