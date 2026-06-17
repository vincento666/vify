from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.runtime import router as runtime_router
from app.core.config import get_settings
from app.core.database import check_database_schema, initialise_database
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.modules.agent.web.router import router as agent_router
from app.modules.ai_assistant.web.router import router as ai_assistant_router
from app.modules.audit.web.router import router as audit_router
from app.modules.chat.web.router import router as chat_router
from app.modules.customer_assistant.web.router import router as customer_assistant_router
from app.modules.evaluation.web.router import case_router as eval_case_router
from app.modules.evaluation.web.router import evaluator_router
from app.modules.evaluation.web.router import experiment_router
from app.modules.evaluation.web.router import run_router as evaluation_run_router
from app.modules.evaluation.web.router import router as evaluation_router
from app.modules.handoff.web.router import router as handoff_router
from app.modules.knowledge.web.router import document_router, faq_router, router as knowledge_router
from app.modules.mcp.web.router import router as mcp_router
from app.modules.observe.web.router import router as observe_router
from app.modules.provider.web.router import router as provider_router
from app.modules.runtime_lab.web.router import router as runtime_lab_router
from app.modules.runtime_policy.web.router import router as runtime_policy_router
from app.modules.workflow.web.api_resource_router import router as api_resource_router
from app.modules.workflow.web.api_resource_router import tool_router
from app.modules.workflow.web.router import (
    chatflow_router,
    resource_router as workflow_resource_router,
    router as workflow_router,
    runtime_v2_router,
)

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    current_settings = settings
    if should_initialise_database_on_startup(current_settings):
        initialise_database()
    elif should_check_database_schema_on_startup(current_settings):
        check_database_schema()
    yield


def should_initialise_database_on_startup(current_settings: object) -> bool:
    mode = str(getattr(current_settings, "persistence_mode", "local") or "local").strip().lower()
    return mode in {"local", "test"}


def should_check_database_schema_on_startup(current_settings: object) -> bool:
    mode = str(getattr(current_settings, "persistence_mode", "local") or "local").strip().lower()
    return mode == "check"


app = FastAPI(title=settings.app_name, version="0.0.1", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(runtime_router)
app.include_router(provider_router)
app.include_router(agent_router)
app.include_router(ai_assistant_router)
app.include_router(mcp_router)
app.include_router(knowledge_router)
app.include_router(document_router)
app.include_router(faq_router)
app.include_router(workflow_router)
app.include_router(chatflow_router)
app.include_router(runtime_v2_router)
app.include_router(workflow_resource_router)
app.include_router(api_resource_router)
app.include_router(tool_router)
app.include_router(evaluation_router)
app.include_router(eval_case_router)
app.include_router(evaluator_router)
app.include_router(experiment_router)
app.include_router(evaluation_run_router)
app.include_router(chat_router)
app.include_router(customer_assistant_router)
app.include_router(handoff_router)
app.include_router(observe_router)
app.include_router(audit_router)
app.include_router(runtime_lab_router)
app.include_router(runtime_policy_router)
