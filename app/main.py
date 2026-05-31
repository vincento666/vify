from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.runtime import router as runtime_router
from app.core.config import get_settings
from app.core.database import initialise_database
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.modules.agent.web.router import router as agent_router
from app.modules.chat.web.router import router as chat_router
from app.modules.knowledge.web.router import document_router, router as knowledge_router
from app.modules.mcp.web.router import router as mcp_router
from app.modules.provider.web.router import router as provider_router
from app.modules.workflow.web.router import router as workflow_router

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    initialise_database()
    yield


app = FastAPI(title=settings.app_name, version="0.0.1", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(runtime_router)
app.include_router(provider_router)
app.include_router(agent_router)
app.include_router(mcp_router)
app.include_router(knowledge_router)
app.include_router(document_router)
app.include_router(workflow_router)
app.include_router(chat_router)
