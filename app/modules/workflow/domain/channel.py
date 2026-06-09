from __future__ import annotations

from dataclasses import dataclass, field
from time import time_ns
from typing import Any


@dataclass(frozen=True)
class ChannelInboundRequest:
    message: str
    conversation_id: str = ""
    user_id: str = ""
    channel_id: str = ""
    files: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ChannelAdapter:
    channel_id: str
    display_name: str
    runnable: bool = True
    unavailable_reason: str = ""
    config_schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    delivery_capabilities: dict[str, bool] = {
        "sync": True,
        "streaming": False,
        "files": False,
        "cards": False,
    }
    normalized_input_fields: tuple[str, ...] = (
        "sys.query",
        "sys.channel",
        "sys.channel_id",
        "sys.conversation_id",
        "sys.user_id",
        "sys.files",
        "channel.metadata",
    )

    def to_runtime_input(self, request: ChannelInboundRequest) -> dict[str, Any]:
        raise NotImplementedError


class ApiChannelAdapter(ChannelAdapter):
    channel_id = "api"
    display_name = "REST API"
    config_schema = {
        "type": "object",
        "properties": {
            "channelId": {"type": "string", "title": "Channel ID"},
            "defaultUserId": {"type": "string", "title": "Default User ID"},
        },
        "required": [],
    }
    delivery_capabilities = {
        "sync": True,
        "streaming": True,
        "files": True,
        "cards": False,
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    def to_runtime_input(self, request: ChannelInboundRequest) -> dict[str, Any]:
        return _base_runtime_input(
            channel="api",
            default_channel_id=str(self._config.get("channelId") or "api"),
            default_user_id=str(self._config.get("defaultUserId") or "api-user"),
            request=request,
        )


class WebChannelAdapter(ChannelAdapter):
    channel_id = "web"
    display_name = "Web Chat"
    config_schema = {
        "type": "object",
        "properties": {
            "channelId": {"type": "string", "title": "Channel ID"},
            "defaultUserId": {"type": "string", "title": "Default User ID"},
        },
        "required": [],
    }
    delivery_capabilities = {
        "sync": True,
        "streaming": True,
        "files": True,
        "cards": False,
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    def to_runtime_input(self, request: ChannelInboundRequest) -> dict[str, Any]:
        return _base_runtime_input(
            channel="web",
            default_channel_id=str(self._config.get("channelId") or "web-preview"),
            default_user_id=str(self._config.get("defaultUserId") or "guest"),
            request=request,
        )


class DisabledChannelAdapter(ChannelAdapter):
    runnable = False
    config_schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    delivery_capabilities = {
        "sync": False,
        "streaming": False,
        "files": False,
        "cards": False,
    }

    def __init__(self, channel_id: str, display_name: str, unavailable_reason: str) -> None:
        self.channel_id = channel_id
        self.display_name = display_name
        self.unavailable_reason = unavailable_reason

    def to_runtime_input(self, request: ChannelInboundRequest) -> dict[str, Any]:
        raise ValueError(f"Channel {self.channel_id} is not available: {self.unavailable_reason}")


def runnable_channel_adapter(channel_id: str, config: dict[str, Any] | None = None) -> ChannelAdapter | None:
    normalized = channel_id.strip().lower()
    if normalized == "api":
        return ApiChannelAdapter(config)
    if normalized == "web":
        return WebChannelAdapter(config)
    return None


def channel_shells() -> list[ChannelAdapter]:
    return [
        ApiChannelAdapter(),
        WebChannelAdapter(),
        DisabledChannelAdapter("feishu", "Feishu", "缺少 webhook 验签和凭据配置"),
        DisabledChannelAdapter("dingtalk", "DingTalk", "缺少回调验签和机器人凭据配置"),
        DisabledChannelAdapter("wecom", "WeCom", "缺少企业微信应用凭据配置"),
        DisabledChannelAdapter("wechat", "WeChat", "缺少公众号/小程序凭据配置"),
    ]


def _base_runtime_input(
    *,
    channel: str,
    default_channel_id: str,
    default_user_id: str,
    request: ChannelInboundRequest,
) -> dict[str, Any]:
    conversation_id = request.conversation_id or f"{channel}-{time_ns()}"
    user_id = request.user_id or default_user_id
    channel_id = request.channel_id or default_channel_id
    return {
        "userMessage": request.message,
        "USER_INPUT": request.message,
        "sys.query": request.message,
        "sys.channel": channel,
        "sys.channel_id": channel_id,
        "sys.conversation_id": conversation_id,
        "sys.user_id": user_id,
        "sys.files": request.files,
        "channel.metadata": request.metadata,
    }
