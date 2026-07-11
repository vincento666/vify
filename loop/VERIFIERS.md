# Loop Verifiers: Spec 190.5

## Focused

    cd frontend && rtk npm run test:unit -- --run src/views/aiAssistant/aiAssistantUsageViewModel.test.ts src/views/aiAssistant/aiAssistantUsageDashboard.test.ts src/views/aiAssistant/aiAssistantUsageDashboard.behavior.test.ts src/router/ai-assistant-routes.test.ts src/api/aiAssistant.test.ts

## Required Proof

- route and AI Assistant Token 用量 entry;
- four cards, recent-year heatmap, default 30-day detail range;
- Token/Cost toggle, session ranking/detail, dimensions/composition;
- loading, empty, partial, unknown, and error states;
- no false zero price and no arbitrary scope selector;
- repeatable Browser UAT screenshot and DOM evidence.

## Static

    cd frontend && rtk npm run test:unit -- --run src/remScaleClosure.test.ts
    cd frontend && rtk npm run build
    cd frontend && rtk npm run dev -- --host 127.0.0.1 --port 5174
    cd frontend && rtk node e2e/ai-assistant-usage-uat.mjs
    rtk git diff --check

## Broad

    cd frontend && rtk npm run test:unit
