# Frontend Integration Packaging

This document records frontend packaging expectations for host integration.

## Runtime Dependencies

Migrated production modules require:

```text
vue
vue-router
ant-design-vue
@ant-design/icons-vue
lucide-vue-next
axios
marked
```

`ant-design-vue/dist/reset.css` is imported once by
`frontend/src/app/ant-design.ts`; host packaging should not import it again for
Hify modules.

## UI Platform Rule

Host-integrated Hify modules should assume Ant Design Vue runtime conventions.
Feature code uses Ant components directly, while global install/theme setup
stays in `frontend/src/app/ant-design.ts`.

Do not export a generic `shared/ui` wrapper package as the integration surface.
The integration surface is module pages/routes/API adapters plus the app seam.

## Workflow Scope

Spec044 migration is complete for workflow/chatflow list, API Resource,
canvas/create, observe redirect, and legacy Chatflow create surfaces.

Standalone Hify packaging no longer includes:

```text
element-plus
@element-plus/icons-vue
element-plus/dist/index.css
frontend/src/styles/element-override.css
```

Host packaging should install Ant Design Vue and load Hify through
`frontend/src/app/ant-design.ts`; no legacy Element Plus seam remains.

## Test And Artifact Exclusion

Integration exports should exclude:

```text
**/*.test.ts
artifacts/**
dist/**
node_modules/**
```

Keep browser UAT screenshots and command evidence in the repository artifact
tree for acceptance, but do not ship them in host module bundles.

## MySQL8 + Weaviate Demo Backend

Spec060 demo packaging can run the same frontend API adapters against a
MySQL8-backed FastAPI service with Weaviate semantic retrieval. The frontend API
surface stays `/api/v1/...` and keeps the `{code, message, data}` envelope.

Backend startup, environment variables, migration, and known limits are tracked
in [mysql8-weaviate-demo.md](mysql8-weaviate-demo.md).
