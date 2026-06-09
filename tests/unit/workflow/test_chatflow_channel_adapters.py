import pytest

from app.modules.workflow.domain.channel import (
    ApiChannelAdapter,
    ChannelInboundRequest,
    DisabledChannelAdapter,
    WebChannelAdapter,
)


def test_api_channel_adapter_maps_identity_files_and_message_to_sys_scope() -> None:
    adapter = ApiChannelAdapter({"channelId": "api-prod", "defaultUserId": "svc-default"})

    mapped = adapter.to_runtime_input(
        ChannelInboundRequest(
            message="hello",
            conversation_id="conv-1",
            user_id="user-1",
            channel_id="api-request",
            files=[{"name": "a.txt"}],
            metadata={"trace": "t-1"},
        )
    )

    assert mapped["sys.channel"] == "api"
    assert mapped["sys.channel_id"] == "api-request"
    assert mapped["sys.conversation_id"] == "conv-1"
    assert mapped["sys.user_id"] == "user-1"
    assert mapped["sys.files"] == [{"name": "a.txt"}]
    assert mapped["sys.query"] == "hello"
    assert mapped["channel.metadata"] == {"trace": "t-1"}


def test_web_channel_adapter_uses_preview_defaults_when_identity_is_missing() -> None:
    adapter = WebChannelAdapter({"channelId": "web-preview", "defaultUserId": "guest"})

    mapped = adapter.to_runtime_input(ChannelInboundRequest(message="hi"))

    assert mapped["sys.channel"] == "web"
    assert mapped["sys.channel_id"] == "web-preview"
    assert mapped["sys.conversation_id"].startswith("web-")
    assert mapped["sys.user_id"] == "guest"
    assert mapped["sys.query"] == "hi"


def test_disabled_channel_adapter_cannot_build_runtime_input() -> None:
    adapter = DisabledChannelAdapter("feishu", "Feishu", "缺少 webhook 验签和凭据配置")

    with pytest.raises(ValueError, match="not available"):
        adapter.to_runtime_input(ChannelInboundRequest(message="hello"))
