import os
import time
import unittest
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable

from app.core.database import Base, _ensure_compatible_schema
from app.core.schema import register_baseline_tables
from app.modules.customer_assistant.infra.schema import register_customer_assistant_tables
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import Mysql8TestDatabase


MYSQL8_TEST_DATABASE_URL = os.getenv("HIFY_MYSQL8_TEST_DATABASE_URL")


class Mysql8RuntimeV2DemoPersistenceContractTest(unittest.TestCase):
    def test_local_gate_declares_all_required_mvp_persistence_surfaces(self) -> None:
        register_baseline_tables()
        register_runtime_lab_tables()
        register_customer_assistant_tables()

        covered_tables = set(_TABLE_NAMES)
        required_tables = set(_REQUIRED_MVP_SURFACE_COLUMNS)

        self.assertEqual([], sorted(required_tables - covered_tables))
        for table_name, column_names in _REQUIRED_MVP_SURFACE_COLUMNS.items():
            table = Base.metadata.tables[table_name]
            missing_columns = [column_name for column_name in column_names if column_name not in table.c]
            self.assertEqual([], missing_columns, table_name)

    def test_mvp_demo_table_set_includes_worker_profile_overrides_and_compiles_for_mysql8(self) -> None:
        register_baseline_tables()
        register_runtime_lab_tables()
        register_customer_assistant_tables()

        self.assertIn("customer_assistant_worker_profile", set(_TABLE_NAMES))

        dialect = mysql.dialect()
        compiled_tables = {
            table.name: str(CreateTable(table).compile(dialect=dialect))
            for table in _tables(_TABLE_NAMES)
        }
        compiled_column_types = {
            table.name: {
                column.name: column.type.compile(dialect=dialect).upper()
                for column in table.columns
            }
            for table in _tables(_TABLE_NAMES)
        }

        self.assertIn("JSON", compiled_tables["customer_assistant_worker_profile"])
        self.assertIn("JSON", compiled_tables["customer_assistant_session"])
        self.assertNotIn("VECTOR", "\n".join(compiled_tables.values()).upper())
        for table_name, column_names in _MYSQL8_JSON_COLUMNS.items():
            for column_name in column_names:
                self.assertEqual("JSON", compiled_column_types[table_name][column_name])
        for table_name, column_names in _MYSQL8_DATETIME_COLUMNS.items():
            for column_name in column_names:
                self.assertEqual("DATETIME", compiled_column_types[table_name][column_name])
        for table_name, column_names in _MYSQL8_TEXT_COLUMNS.items():
            for column_name in column_names:
                self.assertIn("TEXT", compiled_column_types[table_name][column_name])
        for table_name, column_names in _MYSQL8_BOOLEAN_COLUMNS.items():
            for column_name in column_names:
                self.assertIn(compiled_column_types[table_name][column_name], {"BOOL", "BOOLEAN"})

    def test_demo_anchor_profile_and_text_payloads_round_trip_locally(self) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)

        with Mysql8TestDatabase("mysql8_runtime_v2_demo_anchor") as database:
            database.create_all(tables=_tables(_TABLE_NAMES), register=_register_mvp_surface_tables)
            engine = database.engine
            self.assertIsNotNone(engine)
            with engine.begin() as connection:
                workflow_id = _insert(
                    connection,
                    "workflow",
                    name="local-runtime-v2-demo",
                    description="local mysql8 compatibility gate",
                    flow_type="CHATFLOW",
                    status="PUBLISHED",
                    created_at=now,
                    updated_at=now,
                )
                workflow_run_id = _insert(
                    connection,
                    "workflow_run",
                    workflow_id=workflow_id,
                    status="COMPLETED",
                    input={"customerMessage": "我要退票，也想查行李额"},
                    output={"route": "customer_assistant", "taskCount": 2},
                    error="",
                    elapsed_ms=42,
                    finished_at=now,
                    created_at=now,
                    updated_at=now,
                )
                node_run_id = _insert(
                    connection,
                    "workflow_node_run",
                    workflow_run_id=workflow_run_id,
                    node_key="collect_order",
                    node_type="FORM",
                    status="WAITING",
                    inputs={"required": ["orderNo"]},
                    outputs={"prompt": "请补充订单号"},
                    error="",
                    elapsed_ms=7,
                    finished_at=None,
                    created_at=now,
                    updated_at=now,
                )
                published_version_id = _insert(
                    connection,
                    "workflow_published_version",
                    workflow_id=workflow_id,
                    flow_type="CHATFLOW",
                    version=1,
                    snapshot={
                        "nodes": [
                            {
                                "nodeKey": "knowledge_1",
                                "type": "KNOWLEDGE",
                                "config": {"query": "行李额"},
                            }
                        ],
                        "edges": [],
                    },
                    validation={"warnings": [], "nodeCount": 1},
                    active=True,
                    created_at=now,
                    updated_at=now,
                )
                chatflow_session_id = _insert(
                    connection,
                    "chatflow_session",
                    session_id="local-mysql8-demo",
                    chatflow_id=workflow_id,
                    conversation_id="conv-local-mysql8-demo",
                    user_id="operator-demo",
                    channel="web",
                    channel_id="workbench",
                    status="waiting",
                    current_run_id=workflow_run_id,
                    variables={
                        "customer": {"phone": "138****0000", "orderNo": "TK-111"},
                        "ledger": [{"task": "refund", "status": "waiting"}],
                    },
                    expires_at=now,
                    created_at=now,
                    updated_at=now,
                )
                chatflow_event_id = _insert(
                    connection,
                    "chatflow_event",
                    session_id="local-mysql8-demo",
                    chatflow_id=workflow_id,
                    run_id=workflow_run_id,
                    sequence=1,
                    event_type="NODE_BLOCKED",
                    node_key="collect_order",
                    payload={"resume": {"required": ["orderNo"], "prompt": "请提供订单号"}},
                    created_at=now,
                    updated_at=now,
                )
                chatflow_checkpoint_id = _insert(
                    connection,
                    "chatflow_checkpoint",
                    session_id="local-mysql8-demo",
                    chatflow_id=workflow_id,
                    run_id=workflow_run_id,
                    event_id=chatflow_event_id,
                    pending_node_key="collect_order",
                    execution_context={"trace": [{"node": "start"}, {"node": "collect_order"}]},
                    node_outputs={"start": {"ok": True}},
                    variable_scopes={"session": {"customerTier": "gold"}},
                    resume_schema={"type": "object", "required": ["orderNo"]},
                    status="waiting",
                    expires_at=now,
                    created_at=now,
                    updated_at=now,
                )
                channel_config_id = _insert(
                    connection,
                    "chatflow_channel_config",
                    chatflow_id=workflow_id,
                    channel_id="workbench",
                    display_name="MVP Workbench",
                    enabled=True,
                    config={"entry": {"story": "refund-baggage"}, "riskPolicy": {"writes": "confirm"}},
                    created_at=now,
                    updated_at=now,
                )
                session_id = _insert(
                    connection,
                    "customer_assistant_session",
                    status="ACTIVE",
                    context_json={
                        "demoSeed": "073",
                        "demoSeedKey": "refund_baggage_parallel",
                        "storyId": "refund_baggage_parallel",
                        "storyTitle": "退票 + 行李额并行处理",
                        "hostContext": {"tenantId": "demo-airline", "orgId": "ops-cn"},
                    },
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                run_id = _insert(
                    connection,
                    "customer_assistant_run",
                    session_id=session_id,
                    idempotency_key="run:local-mysql8-demo",
                    request_hash="hash-run-local-mysql8-demo",
                    status="COMPLETED",
                    input_payload={"customerMessage": "我要退票，也想查行李额"},
                    response_payload={"tasksCreated": ["refund", "baggage"]},
                    warnings_json=[{"code": "REQUIRES_CONFIRMATION"}],
                    started_at=now,
                    completed_at=now,
                    created_at=now,
                    updated_at=now,
                )
                customer_task_id = _insert(
                    connection,
                    "customer_assistant_task",
                    session_id=session_id,
                    task_key="refund:local-mysql8-demo",
                    task_type="refund_ticket",
                    business_key="TK-111",
                    short_id="RF111",
                    status="PENDING_CONFIRMATION",
                    worker_type="react",
                    worker_ref="refund-react-worker",
                    checkpoint_json={"pendingTool": "submit_refund", "attempt": 1},
                    input_snapshot_json={"ticket": {"orderNo": "TK-111"}},
                    last_result_json={"recommendation": {"script": "建议先核验退票规则"}},
                    proposed_actions_json=[{"actionKey": "submit:local-mysql8-demo", "risk": "write"}],
                    completed_at=None,
                    created_at=now,
                    updated_at=now,
                )
                customer_event_id = _insert(
                    connection,
                    "customer_assistant_event",
                    session_id=session_id,
                    run_id=run_id,
                    sequence=1,
                    type="TASK_PROPOSED",
                    visibility="operator",
                    source="customer_assistant",
                    actor="system",
                    task_id=customer_task_id,
                    parent_span_id="span-parent",
                    span_id="span-task",
                    payload={"taskKey": "refund:local-mysql8-demo", "risk": {"level": "medium"}},
                    created_at=now,
                    updated_at=now,
                )
                worker_run_id = _insert(
                    connection,
                    "customer_assistant_worker_run",
                    session_id=session_id,
                    parent_run_id=run_id,
                    task_id=customer_task_id,
                    worker_type="react",
                    worker_ref="refund-react-worker",
                    idempotency_key="worker:local-mysql8-demo",
                    request_hash="hash-worker-local-mysql8-demo",
                    status="SUCCEEDED",
                    input_payload={"taskKey": "refund:local-mysql8-demo", "tools": ["refund_policy"]},
                    result_payload={"toolCalls": [{"name": "refund_policy", "ok": True}]},
                    error_json=None,
                    queued_at=now,
                    started_at=now,
                    completed_at=now,
                    created_at=now,
                    updated_at=now,
                )
                worker_event_id = _insert(
                    connection,
                    "customer_assistant_worker_event",
                    worker_run_id=worker_run_id,
                    sequence=1,
                    type="TOOL_CALL",
                    visibility="debug",
                    source="customer_assistant_worker",
                    actor="system",
                    payload={"tool": {"name": "refund_policy", "arguments": {"orderNo": "TK-111"}}},
                    created_at=now,
                    updated_at=now,
                )
                proposed_action_id = _insert(
                    connection,
                    "customer_assistant_proposed_action",
                    session_id=session_id,
                    run_id=run_id,
                    task_id=customer_task_id,
                    action_key="submit:local-mysql8-demo",
                    action_type="submit_refund",
                    title="提交退票申请",
                    payload={"orderNo": "TK-111", "amount": {"currency": "CNY", "value": 1280}},
                    status="PENDING",
                    result_json={"audit": {"pending": True}},
                    created_at=now,
                    updated_at=now,
                )
                profile_id = _insert(
                    connection,
                    "customer_assistant_worker_profile",
                    tenant_id="demo-airline",
                    org_id="ops-cn",
                    profile_id="refund-ticket-runtime-v2",
                    task_key="refund_ticket",
                    task_type="refund_ticket",
                    worker_type="chatflow",
                    worker_ref="runtime-v2-chatflow",
                    model_policy_ref="mvp-demo-qwen",
                    prompt_ref="refund-policy-v2",
                    tool_refs=["refund_policy", "submit_refund"],
                    risk_policy_ref="manual_confirm",
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
                runtime_session_id = _insert(
                    connection,
                    "runtime_lab_session",
                    status="ACTIVE",
                    active_task_id=None,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                task_id = _insert(
                    connection,
                    "runtime_lab_task",
                    session_id=runtime_session_id,
                    sop_id="refund-ticket",
                    status="SUSPENDED",
                    resume_summary="等待订单号后继续退票并同步行李额说明",
                    created_at=now,
                    updated_at=now,
                )
                runtime_event_id = _insert(
                    connection,
                    "runtime_lab_event",
                    session_id=runtime_session_id,
                    sequence=1,
                    event_type="TASK_SUSPENDED",
                    payload={
                        "taskId": task_id,
                        "currentStep": "collect_order_no",
                        "ticket": {"orderNo": "TK-111"},
                        "reason": "missing_order",
                    },
                    created_at=now,
                    updated_at=now,
                )
                command_id = _insert(
                    connection,
                    "runtime_lab_command",
                    session_id=runtime_session_id,
                    idempotency_key="resume:local-mysql8-demo",
                    request_hash="hash-local-mysql8-demo",
                    response_payload={"routeDecision": {"action": "RESUME_TASK"}, "taskId": task_id},
                    created_at=now,
                )

            with engine.connect() as connection:
                self.assertEqual(
                    "customer_assistant",
                    _read_json(connection, "workflow_run", workflow_run_id, "output")["route"],
                )
                self.assertEqual(
                    "请补充订单号",
                    _read_json(connection, "workflow_node_run", node_run_id, "outputs")["prompt"],
                )
                self.assertEqual(
                    "KNOWLEDGE",
                    _read_json(connection, "workflow_published_version", published_version_id, "snapshot")[
                        "nodes"
                    ][0]["type"],
                )
                self.assertEqual(
                    "138****0000",
                    _read_json(connection, "chatflow_session", chatflow_session_id, "variables")["customer"][
                        "phone"
                    ],
                )
                self.assertEqual(
                    ["orderNo"],
                    _read_json(connection, "chatflow_checkpoint", chatflow_checkpoint_id, "resume_schema")[
                        "required"
                    ],
                )
                self.assertEqual(
                    "orderNo",
                    _read_json(connection, "chatflow_event", chatflow_event_id, "payload")["resume"][
                        "required"
                    ][0],
                )
                self.assertEqual(
                    "confirm",
                    _read_json(connection, "chatflow_channel_config", channel_config_id, "config")[
                        "riskPolicy"
                    ]["writes"],
                )
                self.assertEqual(
                    "refund_baggage_parallel",
                    _read_json(connection, "customer_assistant_session", session_id, "context_json")[
                        "demoSeedKey"
                    ],
                )
                self.assertEqual(
                    ["refund_policy", "submit_refund"],
                    _read_json(connection, "customer_assistant_worker_profile", profile_id, "tool_refs"),
                )
                self.assertEqual(
                    ["refund", "baggage"],
                    _read_json(connection, "customer_assistant_run", run_id, "response_payload")[
                        "tasksCreated"
                    ],
                )
                self.assertEqual(
                    "submit:local-mysql8-demo",
                    _read_json(
                        connection,
                        "customer_assistant_task",
                        customer_task_id,
                        "proposed_actions_json",
                    )[0]["actionKey"],
                )
                self.assertEqual(
                    "medium",
                    _read_json(connection, "customer_assistant_event", customer_event_id, "payload")[
                        "risk"
                    ]["level"],
                )
                self.assertEqual(
                    "refund_policy",
                    _read_json(connection, "customer_assistant_worker_run", worker_run_id, "result_payload")[
                        "toolCalls"
                    ][0]["name"],
                )
                self.assertEqual(
                    "refund_policy",
                    _read_json(connection, "customer_assistant_worker_event", worker_event_id, "payload")[
                        "tool"
                    ]["name"],
                )
                self.assertEqual(
                    1280,
                    _read_json(connection, "customer_assistant_proposed_action", proposed_action_id, "payload")[
                        "amount"
                    ]["value"],
                )
                self.assertEqual(
                    "等待订单号后继续退票并同步行李额说明",
                    _read_json(connection, "runtime_lab_task", task_id, "resume_summary"),
                )
                self.assertEqual(
                    "TK-111",
                    _read_json(connection, "runtime_lab_event", runtime_event_id, "payload")[
                        "ticket"
                    ]["orderNo"],
                )
                self.assertEqual(
                    "missing_order",
                    _read_json(connection, "runtime_lab_event", runtime_event_id, "payload")["reason"],
                )
                self.assertEqual(
                    "RESUME_TASK",
                    _read_json(connection, "runtime_lab_command", command_id, "response_payload")[
                        "routeDecision"
                    ]["action"],
                )


@unittest.skipUnless(MYSQL8_TEST_DATABASE_URL, "set HIFY_MYSQL8_TEST_DATABASE_URL for MySQL8 integration")
class Mysql8RuntimeV2CustomerAssistantPersistenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        register_baseline_tables()
        register_runtime_lab_tables()
        register_customer_assistant_tables()
        cls.engine = sa.create_engine(MYSQL8_TEST_DATABASE_URL, future=True)
        Base.metadata.create_all(bind=cls.engine, tables=_tables(_TABLE_NAMES))
        _ensure_compatible_schema(cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def test_runtime_v2_and_customer_assistant_json_roundtrip_and_unique_guards(self) -> None:
        token = f"mysql8-runtime-demo-{time.time_ns()}"
        run_id = time.time_ns()
        now = datetime.now(UTC).replace(tzinfo=None)
        ids: dict[str, int] = {}

        with self.engine.begin() as connection:
            ids["workflow"] = _insert(
                connection,
                "workflow",
                name=token,
                description="runtime v2 mysql8 persistence smoke",
                flow_type="CHATFLOW",
                status="PUBLISHED",
                created_at=now,
                updated_at=now,
            )
            ids["workflow_run"] = _insert(
                connection,
                "workflow_run",
                workflow_id=ids["workflow"],
                status="COMPLETED",
                input={"customerMessage": "我要退票，也想查行李额"},
                output={"route": "customer_assistant", "taskCount": 2},
                error="",
                elapsed_ms=42,
                finished_at=now,
                created_at=now,
                updated_at=now,
            )
            ids["workflow_node_run"] = _insert(
                connection,
                "workflow_node_run",
                workflow_run_id=ids["workflow_run"],
                node_key="collect_order",
                node_type="FORM",
                status="WAITING",
                inputs={"required": ["orderNo"]},
                outputs={"prompt": "请补充订单号"},
                error="",
                elapsed_ms=7,
                finished_at=None,
                created_at=now,
                updated_at=now,
            )
            ids["workflow_published_version"] = _insert(
                connection,
                "workflow_published_version",
                workflow_id=ids["workflow"],
                flow_type="CHATFLOW",
                version=1,
                snapshot={
                    "nodes": [
                        {
                            "nodeKey": "knowledge_1",
                            "type": "KNOWLEDGE",
                            "config": {"query": "行李额", "filters": {"customerTier": "gold"}},
                        }
                    ],
                    "edges": [],
                    "demo": {"token": token, "parallelTasks": ["refund", "baggage"]},
                },
                validation={"warnings": [], "nodeCount": 1},
                active=True,
                created_at=now,
                updated_at=now,
            )
            ids["chatflow_session"] = _insert(
                connection,
                "chatflow_session",
                session_id=token,
                chatflow_id=ids["workflow"],
                conversation_id=f"conv-{token}",
                user_id="operator-demo",
                channel="web",
                channel_id="workbench",
                status="waiting",
                current_run_id=run_id,
                variables={
                    "customer": {"phone": "138****0000", "orderNo": "TK-087"},
                    "ledger": [{"task": "refund", "status": "waiting"}],
                },
                created_at=now,
                updated_at=now,
            )
            ids["chatflow_event"] = _insert(
                connection,
                "chatflow_event",
                session_id=token,
                chatflow_id=ids["workflow"],
                run_id=run_id,
                sequence=1,
                event_type="NODE_BLOCKED",
                node_key="collect_order",
                payload={"resume": {"required": ["orderNo"], "prompt": "请提供订单号"}},
                created_at=now,
                updated_at=now,
            )
            ids["chatflow_checkpoint"] = _insert(
                connection,
                "chatflow_checkpoint",
                session_id=token,
                chatflow_id=ids["workflow"],
                run_id=run_id,
                event_id=ids["chatflow_event"],
                pending_node_key="collect_order",
                execution_context={"trace": [{"node": "start"}, {"node": "collect_order"}]},
                node_outputs={"start": {"ok": True}},
                variable_scopes={"session": {"customerTier": "gold"}},
                resume_schema={"type": "object", "required": ["orderNo"]},
                status="waiting",
                created_at=now,
                updated_at=now,
            )
            ids["chatflow_channel_config"] = _insert(
                connection,
                "chatflow_channel_config",
                chatflow_id=ids["workflow"],
                channel_id=f"workbench-{token}",
                display_name="MVP Workbench",
                enabled=True,
                config={"entry": {"story": "refund-baggage"}, "riskPolicy": {"writes": "confirm"}},
                created_at=now,
                updated_at=now,
            )

            ids["runtime_lab_session"] = _insert(
                connection,
                "runtime_lab_session",
                status="ACTIVE",
                active_task_id=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
            ids["runtime_lab_task"] = _insert(
                connection,
                "runtime_lab_task",
                session_id=ids["runtime_lab_session"],
                sop_id=f"refund-{token}",
                status="SUSPENDED",
                resume_summary="等待订单号后继续退票",
                created_at=now,
                updated_at=now,
            )
            ids["runtime_lab_event"] = _insert(
                connection,
                "runtime_lab_event",
                session_id=ids["runtime_lab_session"],
                sequence=1,
                event_type="TASK_SUSPENDED",
                payload={
                    "taskId": ids["runtime_lab_task"],
                    "currentStep": "collect_order_no",
                    "passenger": {"name": "Demo User"},
                    "ticket": {"orderNo": "TK-087"},
                    "reason": "missing_order",
                },
                created_at=now,
                updated_at=now,
            )
            ids["runtime_lab_command"] = _insert(
                connection,
                "runtime_lab_command",
                session_id=ids["runtime_lab_session"],
                idempotency_key=f"resume:{token}",
                request_hash=f"hash-{token}",
                response_payload={"routeDecision": {"action": "RESUME_TASK"}, "taskId": ids["runtime_lab_task"]},
                created_at=now,
            )

            ids["customer_assistant_session"] = _insert(
                connection,
                "customer_assistant_session",
                status="ACTIVE",
                context_json={
                    "demoSeed": "mvp-productized-demo",
                    "customer": {"phone": "138****0000", "orderNo": "TK-087"},
                    "stories": ["refund-baggage"],
                },
                version=1,
                created_at=now,
                updated_at=now,
            )
            ids["customer_assistant_run"] = _insert(
                connection,
                "customer_assistant_run",
                session_id=ids["customer_assistant_session"],
                idempotency_key=f"run:{token}",
                request_hash=f"hash-run-{token}",
                status="COMPLETED",
                input_payload={"customerMessage": "我要退票，也想查行李额"},
                response_payload={"tasksCreated": ["refund", "baggage"], "recommendations": ["先确认票号"]},
                warnings_json=[{"code": "REQUIRES_CONFIRMATION"}],
                started_at=now,
                completed_at=now,
                created_at=now,
                updated_at=now,
            )
            ids["customer_assistant_task"] = _insert(
                connection,
                "customer_assistant_task",
                session_id=ids["customer_assistant_session"],
                task_key=f"refund:{token}",
                task_type="refund_ticket",
                business_key="TK-087",
                short_id="RF087",
                status="PENDING_CONFIRMATION",
                worker_type="react",
                worker_ref="refund-react-worker",
                checkpoint_json={"pendingTool": "submit_refund", "attempt": 1},
                input_snapshot_json={"ticket": {"orderNo": "TK-087"}},
                last_result_json={"recommendation": {"script": "建议先核验退票规则"}},
                proposed_actions_json=[{"actionKey": f"submit:{token}", "risk": "write"}],
                version=1,
                created_at=now,
                updated_at=now,
            )
            ids["customer_assistant_event"] = _insert(
                connection,
                "customer_assistant_event",
                session_id=ids["customer_assistant_session"],
                run_id=ids["customer_assistant_run"],
                sequence=1,
                type="TASK_PROPOSED",
                visibility="operator",
                source="customer_assistant",
                actor="system",
                task_id=ids["customer_assistant_task"],
                parent_span_id="span-parent",
                span_id="span-task",
                payload={"taskKey": f"refund:{token}", "risk": {"level": "medium"}},
                created_at=now,
                updated_at=now,
            )
            ids["customer_assistant_worker_run"] = _insert(
                connection,
                "customer_assistant_worker_run",
                session_id=ids["customer_assistant_session"],
                parent_run_id=ids["customer_assistant_run"],
                task_id=ids["customer_assistant_task"],
                worker_type="react",
                worker_ref="refund-react-worker",
                idempotency_key=f"worker:{token}",
                request_hash=f"hash-worker-{token}",
                status="SUCCEEDED",
                input_payload={"taskKey": f"refund:{token}", "tools": ["refund_policy", "submit_refund"]},
                result_payload={"toolCalls": [{"name": "refund_policy", "ok": True}]},
                error_json=None,
                queued_at=now,
                started_at=now,
                completed_at=now,
                created_at=now,
                updated_at=now,
            )
            ids["customer_assistant_worker_event"] = _insert(
                connection,
                "customer_assistant_worker_event",
                worker_run_id=ids["customer_assistant_worker_run"],
                sequence=1,
                type="TOOL_CALL",
                visibility="debug",
                source="customer_assistant_worker",
                actor="system",
                payload={"tool": {"name": "refund_policy", "arguments": {"orderNo": "TK-087"}}},
                created_at=now,
                updated_at=now,
            )
            ids["customer_assistant_proposed_action"] = _insert(
                connection,
                "customer_assistant_proposed_action",
                session_id=ids["customer_assistant_session"],
                run_id=ids["customer_assistant_run"],
                task_id=ids["customer_assistant_task"],
                action_key=f"submit:{token}",
                action_type="submit_refund",
                title="提交退票申请",
                payload={"orderNo": "TK-087", "amount": {"currency": "CNY", "value": 1280}},
                status="PENDING",
                result_json={"audit": {"pending": True}},
                created_at=now,
                updated_at=now,
            )
            ids["customer_assistant_worker_profile"] = _insert(
                connection,
                "customer_assistant_worker_profile",
                tenant_id="demo-airline",
                org_id="ops-cn",
                profile_id=f"refund-profile:{token}",
                task_key="refund_ticket",
                task_type="refund_ticket",
                worker_type="react",
                worker_ref="refund-react-worker",
                model_policy_ref="mvp-demo-qwen",
                prompt_ref="refund-policy-v2",
                tool_refs=["refund_policy", "submit_refund"],
                risk_policy_ref="manual_confirm",
                enabled=True,
                created_at=now,
                updated_at=now,
            )

        with self.engine.connect() as connection:
            self.assertEqual(
                "customer_assistant",
                _read_json(connection, "workflow_run", ids["workflow_run"], "output")["route"],
            )
            self.assertEqual(
                "请补充订单号",
                _read_json(connection, "workflow_node_run", ids["workflow_node_run"], "outputs")[
                    "prompt"
                ],
            )
            self.assertEqual(
                "138****0000",
                _read_json(connection, "chatflow_session", ids["chatflow_session"], "variables")["customer"]["phone"],
            )
            self.assertEqual(
                ["orderNo"],
                _read_json(connection, "chatflow_checkpoint", ids["chatflow_checkpoint"], "resume_schema")[
                    "required"
                ],
            )
            self.assertEqual(
                "KNOWLEDGE",
                _read_json(connection, "workflow_published_version", ids["workflow_published_version"], "snapshot")[
                    "nodes"
                ][0]["type"],
            )
            self.assertEqual(
                "TK-087",
                _read_json(connection, "runtime_lab_event", ids["runtime_lab_event"], "payload")[
                    "ticket"
                ]["orderNo"],
            )
            self.assertEqual(
                "RESUME_TASK",
                _read_json(connection, "runtime_lab_command", ids["runtime_lab_command"], "response_payload")[
                    "routeDecision"
                ]["action"],
            )
            self.assertEqual(
                "mvp-productized-demo",
                _read_json(
                    connection,
                    "customer_assistant_session",
                    ids["customer_assistant_session"],
                    "context_json",
                )["demoSeed"],
            )
            self.assertEqual(
                "refund_policy",
                _read_json(
                    connection,
                    "customer_assistant_worker_event",
                    ids["customer_assistant_worker_event"],
                    "payload",
                )["tool"]["name"],
            )
            self.assertEqual(
                1280,
                _read_json(
                    connection,
                    "customer_assistant_proposed_action",
                    ids["customer_assistant_proposed_action"],
                    "payload",
                )["amount"]["value"],
            )
            self.assertEqual(
                ["refund_policy", "submit_refund"],
                _read_json(
                    connection,
                    "customer_assistant_worker_profile",
                    ids["customer_assistant_worker_profile"],
                    "tool_refs",
                ),
            )

        self._assert_duplicate_rejected(
            "chatflow_event",
            session_id=token,
            chatflow_id=ids["workflow"],
            run_id=run_id,
            sequence=1,
            event_type="NODE_BLOCKED",
            node_key="collect_order",
            payload={"duplicate": True},
            created_at=now,
            updated_at=now,
        )
        self._assert_duplicate_rejected(
            "runtime_lab_event",
            session_id=ids["runtime_lab_session"],
            sequence=1,
            event_type="DUPLICATE",
            payload={"duplicate": True},
            created_at=now,
            updated_at=now,
        )
        self._assert_duplicate_rejected(
            "customer_assistant_event",
            session_id=ids["customer_assistant_session"],
            run_id=ids["customer_assistant_run"],
            sequence=1,
            type="DUPLICATE",
            payload={"duplicate": True},
            created_at=now,
            updated_at=now,
        )
        self._assert_duplicate_rejected(
            "customer_assistant_worker_run",
            session_id=ids["customer_assistant_session"],
            parent_run_id=ids["customer_assistant_run"],
            task_id=ids["customer_assistant_task"],
            worker_type="react",
            worker_ref="refund-react-worker",
            idempotency_key=f"worker:{token}",
            request_hash=f"hash-worker-duplicate-{token}",
            input_payload={"duplicate": True},
            status="QUEUED",
            created_at=now,
            updated_at=now,
        )
        self._assert_duplicate_rejected(
            "customer_assistant_worker_profile",
            tenant_id="demo-airline",
            org_id="ops-cn",
            profile_id=f"refund-profile:{token}",
            task_key="refund_ticket",
            task_type="refund_ticket",
            worker_type="react",
            worker_ref="refund-react-worker",
            model_policy_ref="mvp-demo-qwen",
            prompt_ref="refund-policy-v2",
            tool_refs=["duplicate"],
            risk_policy_ref="manual_confirm",
            enabled=True,
            created_at=now,
            updated_at=now,
        )

    def _assert_duplicate_rejected(self, table_name: str, **values: Any) -> None:
        table = Base.metadata.tables[table_name]
        connection = self.engine.connect()
        transaction = connection.begin()
        try:
            with self.assertRaises(IntegrityError):
                connection.execute(table.insert().values(**values))
        finally:
            transaction.rollback()
            connection.close()


register_baseline_tables()
register_runtime_lab_tables()
register_customer_assistant_tables()

_TABLE_NAMES = [
    "workflow",
    "workflow_run",
    "workflow_node_run",
    "workflow_published_version",
    "chatflow_session",
    "chatflow_event",
    "chatflow_checkpoint",
    "chatflow_channel_config",
    "runtime_lab_session",
    "runtime_lab_task",
    "runtime_lab_event",
    "runtime_lab_command",
    "customer_assistant_session",
    "customer_assistant_run",
    "customer_assistant_task",
    "customer_assistant_event",
    "customer_assistant_worker_run",
    "customer_assistant_worker_event",
    "customer_assistant_proposed_action",
    "customer_assistant_worker_profile",
]

_REQUIRED_MVP_SURFACE_COLUMNS = {
    "workflow": ["flow_type", "status", "created_at", "updated_at"],
    "workflow_run": ["input", "output", "error", "finished_at"],
    "workflow_node_run": ["inputs", "outputs", "error", "finished_at"],
    "workflow_published_version": ["snapshot", "validation", "active"],
    "chatflow_session": ["current_run_id", "variables", "expires_at"],
    "chatflow_event": ["run_id", "sequence", "payload", "checkpoint_id"],
    "chatflow_checkpoint": [
        "execution_context",
        "node_outputs",
        "variable_scopes",
        "resume_schema",
    ],
    "chatflow_channel_config": ["config", "enabled"],
    "runtime_lab_session": ["status", "active_task_id", "version"],
    "runtime_lab_task": ["resume_summary", "suspended_at", "completed_at"],
    "runtime_lab_event": ["sequence", "payload"],
    "runtime_lab_command": ["response_payload", "created_at"],
    "customer_assistant_session": ["context_json", "version"],
    "customer_assistant_run": ["input_payload", "response_payload", "warnings_json"],
    "customer_assistant_task": [
        "checkpoint_json",
        "input_snapshot_json",
        "last_result_json",
        "proposed_actions_json",
    ],
    "customer_assistant_event": ["run_id", "sequence", "payload", "actor"],
    "customer_assistant_worker_run": ["input_payload", "result_payload", "error_json"],
    "customer_assistant_worker_event": ["sequence", "payload"],
    "customer_assistant_proposed_action": ["payload", "result_json"],
    "customer_assistant_worker_profile": ["tool_refs", "tool_policy_ref", "output_schema_ref", "enabled"],
}

_MYSQL8_JSON_COLUMNS = {
    table_name: [
        column_name
        for column_name in column_names
        if isinstance(Base.metadata.tables[table_name].c[column_name].type, sa.JSON)
    ]
    for table_name, column_names in _REQUIRED_MVP_SURFACE_COLUMNS.items()
}

_MYSQL8_DATETIME_COLUMNS = {
    table_name: [
        column_name
        for column_name in column_names
        if isinstance(Base.metadata.tables[table_name].c[column_name].type, sa.DateTime)
    ]
    for table_name, column_names in _REQUIRED_MVP_SURFACE_COLUMNS.items()
}

_MYSQL8_TEXT_COLUMNS = {
    table_name: [
        column_name
        for column_name in column_names
        if isinstance(Base.metadata.tables[table_name].c[column_name].type, sa.Text)
    ]
    for table_name, column_names in _REQUIRED_MVP_SURFACE_COLUMNS.items()
}

_MYSQL8_BOOLEAN_COLUMNS = {
    table_name: [
        column_name
        for column_name in column_names
        if isinstance(Base.metadata.tables[table_name].c[column_name].type, sa.Boolean)
    ]
    for table_name, column_names in _REQUIRED_MVP_SURFACE_COLUMNS.items()
}


def _tables(names: list[str]) -> list[sa.Table]:
    return [Base.metadata.tables[name] for name in names]


def _register_mvp_surface_tables() -> None:
    register_baseline_tables()
    register_runtime_lab_tables()
    register_customer_assistant_tables()


def _insert(connection: Connection, table_name: str, **values: Any) -> int:
    result = connection.execute(Base.metadata.tables[table_name].insert().values(**values))
    return int(result.inserted_primary_key[0])


def _read_json(connection: Connection, table_name: str, row_id: int, column_name: str) -> Any:
    table = Base.metadata.tables[table_name]
    return connection.execute(sa.select(table.c[column_name]).where(table.c.id == row_id)).scalar_one()


if __name__ == "__main__":
    unittest.main()
