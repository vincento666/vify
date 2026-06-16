from app.core.host.context import request_context_from_headers


def test_request_context_from_headers_parses_host_identity() -> None:
    context = request_context_from_headers({
        "X-Hify-Actor-Id": "u-1",
        "X-Hify-Actor-Name": "User One",
        "X-Hify-Tenant-Id": "tenant-a",
        "X-Hify-Org-Id": "org-a",
        "X-Hify-Roles": "admin, editor",
        "X-Hify-Permissions": "workflow:run, evaluation:run",
        "X-Request-Id": "req-1",
        "X-Hify-Source": "host",
        "Accept-Language": "zh-CN,en;q=0.9",
    })

    assert context.actor_id == "u-1"
    assert context.actor_name == "User One"
    assert context.tenant_id == "tenant-a"
    assert context.org_id == "org-a"
    assert context.roles == ("admin", "editor")
    assert context.permissions == ("workflow:run", "evaluation:run")
    assert context.request_id == "req-1"
    assert context.source == "host"
    assert context.locale == "zh-CN"


def test_request_context_defaults_to_local_dev_identity() -> None:
    context = request_context_from_headers({})

    assert context.actor_id == "local-user"
    assert context.tenant_id == "local"
    assert context.org_id == "local"
    assert context.source == "local"
