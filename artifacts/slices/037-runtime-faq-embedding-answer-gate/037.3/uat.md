# 037 Browser UAT

- Server: http://127.0.0.1:18085
- UI: Swagger UI controlled through the Codex in-app browser
- Seeded FAQ KB: Runtime Semantic FAQ UAT

## Flow

1. Created runtime-lab session through Swagger UI.
2. Posted `儿童 票 怎么 返钱 规则？`. Result: `ANSWER_FAQ`, `sourceLayer=faq_semantic`, `reasonCode=SEMANTIC_HIGH_CONFIDENCE`, `matchType=VECTOR`, `retrievalMode=faq`, `rerankUsed=true`.
3. Added a second nearby FAQ candidate and posted `儿童 票 规则？`. Result: `CLARIFY`, `reasonCode=SEMANTIC_LOW_MARGIN`, with two top FAQ candidates and `mutatesSopState=false`.

## Evidence

- Raw result JSON: `browser-uat-result.json`
- Screenshot: `screenshots/browser-uat-semantic-faq.png`
