from __future__ import annotations

from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.chat.domain.context import ConversationContextStore, MessageContext
from app.modules.chat.domain.llm_request import ChatRequestMessage
from app.modules.chat.domain.mode import ChatModeRouter
from app.modules.chat.domain.orchestrator import ChatOrchestrator
from app.modules.chat.domain.prompt import PromptBuilder
from app.modules.chat.domain.sse import SseEventEncoder
from app.modules.chat.domain.tool_runner import ToolCallRunner
from app.modules.chat.infra.repository import ChatRepository
from app.modules.chat.web.schemas import (
    ChatMessageCreateRequest,
    ChatMessagePageResponse,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionPageResponse,
    ChatSessionResponse,
    ChatTurnResponse,
)
from app.modules.knowledge.api.facade import KnowledgeFacade, KnowledgeSearchResult
from app.modules.mcp.api.facade import McpFacade
from app.modules.workflow.api.facade import WorkflowFacade
from app.modules.workflow.domain.engine import WorkflowExecutionError

_CONTEXT_CACHE: dict[str, list[MessageContext]] = {}


class ChatService:
    def __init__(
        self,
        repository: ChatRepository,
        prompt_builder: PromptBuilder | None = None,
        event_encoder: SseEventEncoder | None = None,
        context_store: ConversationContextStore | None = None,
        mode_router: ChatModeRouter | None = None,
        tool_runner: ToolCallRunner | None = None,
        knowledge_facade: KnowledgeFacade | None = None,
        workflow_facade: WorkflowFacade | None = None,
        mcp_facade: McpFacade | None = None,
        tool_orchestrator: ChatOrchestrator | None = None,
    ) -> None:
        self._repository = repository
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._event_encoder = event_encoder or SseEventEncoder()
        self._context_store = context_store or ConversationContextStore(repository, _CONTEXT_CACHE)
        self._mode_router = mode_router or ChatModeRouter()
        self._tool_runner = tool_runner or ToolCallRunner()
        self._knowledge_facade = knowledge_facade
        self._workflow_facade = workflow_facade
        self._mcp_facade = mcp_facade
        self._tool_orchestrator = tool_orchestrator or ChatOrchestrator()

    def create_session(self, request: ChatSessionCreateRequest) -> dict[str, Any]:
        if not self._repository.agent_exists(request.agent_id):
            raise BizError(ErrorCode.NOT_FOUND, "Agent not found")
        row = self._repository.create_session(request.agent_id)
        return self._session_response(row).model_dump(by_alias=True)

    def list_sessions(
        self,
        page: int,
        page_size: int,
        agent_id: int | None,
    ) -> dict[str, Any]:
        rows, total = self._repository.list_sessions(page, page_size, agent_id)
        response = ChatSessionPageResponse(
            list=[self._session_response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def delete_session(self, session_id: int) -> None:
        if not self._repository.delete_session(session_id):
            raise BizError(ErrorCode.NOT_FOUND, "Chat session not found")
        self._context_store.evict(session_id)

    def list_messages(self, session_id: int, page: int, page_size: int) -> dict[str, Any]:
        if self._repository.get_session(session_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Chat session not found")
        rows, total = self._repository.list_messages(session_id, page, page_size)
        response = ChatMessagePageResponse(
            list=[self._message_response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def send_message(self, session_id: int, request: ChatMessageCreateRequest) -> dict[str, Any]:
        if request.stream:
            raise BizError(ErrorCode.BAD_REQUEST, "Streaming chat is not implemented in this slice")
        return self._create_turn(session_id, request.content).model_dump(by_alias=True)

    def stream_message_events(self, session_id: int, request: ChatMessageCreateRequest) -> list[str]:
        turn = self._create_turn(session_id, request.content)
        content = turn.assistant_message.content
        events = [
            self._event_encoder.encode({"type": "delta", "content": chunk})
            for chunk in self._stream_chunks(content)
        ]
        events.append(
            self._event_encoder.encode(
                {
                    "type": "done",
                    "finishReason": turn.assistant_message.finish_reason,
                    "latencyMs": turn.assistant_message.latency_ms,
                }
            )
        )
        return events

    def _create_turn(self, session_id: int, content: str) -> ChatTurnResponse:
        chat_session = self._repository.get_session(session_id)
        if chat_session is None:
            raise BizError(ErrorCode.NOT_FOUND, "Chat session not found")
        agent = self._repository.get_agent(int(chat_session["agent_id"]))
        if agent is None:
            raise BizError(ErrorCode.NOT_FOUND, "Agent not found")

        max_messages = max(1, int(agent["max_context_turns"]) * 2)
        history = self._context_store.load(session_id, max_messages=max_messages)
        self._prompt_builder.build(
            system_prompt=agent["system_prompt"] or "",
            history=history,
            user_message=content,
        )

        user_row = self._repository.insert_message(
            session_id=session_id,
            role="user",
            content=content,
            tokens=self._count_tokens(content),
        )
        tool_ids = self._repository.list_agent_tool_ids(int(agent["id"]))
        assistant_content = self._assistant_content(agent, tool_ids, content)
        assistant_row = self._repository.insert_message(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            tokens=self._count_tokens(assistant_content),
            finish_reason="stop",
            latency_ms=0,
        )
        self._repository.rename_session_if_default(session_id, content[:30] or "新对话")
        response = ChatTurnResponse(
            userMessage=self._message_response(user_row),
            assistantMessage=self._message_response(assistant_row),
        )
        self._context_store.append(
            session_id,
            [
                {"role": "user", "content": content},
                {"role": "assistant", "content": assistant_content},
            ],
            max_messages=max_messages,
        )
        return response

    def _session_response(self, row: dict[str, Any]) -> ChatSessionResponse:
        return ChatSessionResponse(
            id=int(row["id"]),
            agentId=int(row["agent_id"]),
            title=row["title"] or "",
            status=row["status"],
            createdAt=row["created_at"].isoformat(),
        )

    def _message_response(self, row: dict[str, Any]) -> ChatMessageResponse:
        return ChatMessageResponse(
            id=int(row["id"]),
            sessionId=int(row["session_id"]),
            role=row["role"],
            content=row["content"],
            tokens=int(row["tokens"] or 0),
            finishReason=row["finish_reason"] or "",
            latencyMs=int(row["latency_ms"] or 0),
            createdAt=row["created_at"].isoformat(),
        )

    def _count_tokens(self, content: str) -> int:
        return max(1, len(content.split()))

    def _stream_chunks(self, content: str) -> list[str]:
        parts = content.split(" ")
        chunks: list[str] = []
        for index, part in enumerate(parts):
            suffix = " " if index < len(parts) - 1 else ""
            chunks.append(f"{part}{suffix}")
        return chunks

    def _assistant_content(self, agent: dict[str, Any], tool_ids: list[int], content: str) -> str:
        mode = self._mode_router.resolve(agent)
        if mode == "workflow":
            return self._workflow_content(agent, content)
        if mode == "rag":
            return self._rag_content(agent, content)
        tool_content = self._real_tool_content(agent, tool_ids, content)
        if tool_content is not None:
            return tool_content
        tool_names = self._mcp_facade.tool_names_for_servers(tool_ids) if self._mcp_facade else []
        tool_result = self._tool_runner.run(tool_ids, content, tool_names=tool_names)
        if tool_result is not None:
            return tool_result
        return f"Echo: {content}"

    def _real_tool_content(
        self,
        agent: dict[str, Any],
        tool_ids: list[int],
        content: str,
    ) -> str | None:
        if not tool_ids or self._mcp_facade is None or not self._should_use_real_tool_call(content):
            return None
        tools = self._mcp_facade.tool_definitions_for_servers(tool_ids)
        if not tools:
            return None
        result = self._tool_orchestrator.run(
            model=f"model-config-{agent['model_config_id']}",
            messages=[ChatRequestMessage(role="user", content=content)],
            tools=tools,
            tool_ids=tool_ids,
            mcp_facade=self._mcp_facade,
        )
        return result.final_content or None

    def _should_use_real_tool_call(self, content: str) -> bool:
        normalized = content.lower()
        return "order" in normalized and any(character.isdigit() for character in normalized)

    def _rag_content(self, agent: dict[str, Any], content: str) -> str:
        base_content = f"RAG mock: {content}"
        knowledge_base_id = agent.get("knowledge_base_id")
        if self._knowledge_facade is None or knowledge_base_id is None:
            return base_content
        references = self._knowledge_facade.search_chunks(int(knowledge_base_id), content, top_k=3)
        if not references:
            return base_content
        return f"{base_content}\nReferences:\n{self._format_references(references)}"

    def _format_references(self, references: list[KnowledgeSearchResult]) -> str:
        return "\n".join(f"- [{index + 1}] {reference.content}" for index, reference in enumerate(references))

    def _workflow_content(self, agent: dict[str, Any], content: str) -> str:
        workflow_id = agent.get("workflow_id")
        if self._workflow_facade is not None and workflow_id is not None:
            try:
                output = self._workflow_facade.execute_for_chat(int(workflow_id), content)
            except WorkflowExecutionError as exc:
                return f"Workflow error: {exc}"
            if output:
                return f"Workflow mock: {output}"
        return f"Workflow mock: {content}"
