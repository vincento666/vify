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


MYSQL8_TEST_DATABASE_URL = os.getenv("HIFY_MYSQL8_TEST_DATABASE_URL")


class Mysql8RuntimeV2DemoPersistenceContractTest(unittest.TestCase):
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

        self.assertIn("JSON", compiled_tables["customer_assistant_worker_profile"])
        self.assertIn("JSON", compiled_tables["customer_assistant_session"])
        self.assertNotIn("VECTOR", "\n".join(compiled_tables.values()).upper())

    def test_demo_anchor_profile_and_text_payloads_round_trip_locally(self) -> None:
        register_baseline_tables()
        register_runtime_lab_tables()
        register_customer_assistant_tables()
        engine = sa.create_engine("sqlite:///:memory:", future=True)
        now = datetime.now(UTC).replace(tzinfo=None)

        try:
            Base.metadata.create_all(
                bind=engine,
                tables=_tables(
                    [
                        "customer_assistant_session",
                        "customer_assistant_worker_profile",
                        "runtime_lab_session",
                        "runtime_lab_task",
                        "runtime_lab_checkpoint",
                    ]
                ),
            )
            with engine.begin() as connection:
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
                    current_step="collect_order_no",
                    resume_summary="等待订单号后继续退票并同步行李额说明",
                    business_refs={"customerAssistantSessionId": session_id, "storyId": "refund_baggage_parallel"},
                    created_at=now,
                    updated_at=now,
                )
                checkpoint_id = _insert(
                    connection,
                    "runtime_lab_checkpoint",
                    session_id=runtime_session_id,
                    task_id=task_id,
                    sop_id="refund-ticket",
                    current_step="collect_order_no",
                    pending_prompt="请补充订单号，系统会继续处理退票。",
                    collected={"ticket": {"orderNo": "TK-111"}},
                    scoped_variables={"profileId": "refund-ticket-runtime-v2"},
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )

            with engine.connect() as connection:
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
                    "等待订单号后继续退票并同步行李额说明",
                    _read_json(connection, "runtime_lab_task", task_id, "resume_summary"),
                )
                self.assertEqual(
                    "TK-111",
                    _read_json(connection, "runtime_lab_checkpoint", checkpoint_id, "collected")[
                        "ticket"
                    ]["orderNo"],
                )
        finally:
            engine.dispose()


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
                current_step="collect_order_no",
                resume_summary="等待订单号后继续退票",
                business_refs={"ticketNo": "TK-087", "parallel": ["baggage"]},
                created_at=now,
                updated_at=now,
            )
            ids["runtime_lab_checkpoint"] = _insert(
                connection,
                "runtime_lab_checkpoint",
                session_id=ids["runtime_lab_session"],
                task_id=ids["runtime_lab_task"],
                sop_id=f"refund-{token}",
                current_step="collect_order_no",
                pending_prompt="请提供订单号",
                collected={"passenger": {"name": "Demo User"}, "ticket": {"orderNo": "TK-087"}},
                scoped_variables={"chatflow": {"sessionId": token, "node": "collect_order"}},
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
            ids["runtime_lab_event"] = _insert(
                connection,
                "runtime_lab_event",
                session_id=ids["runtime_lab_session"],
                sequence=1,
                event_type="TASK_SUSPENDED",
                payload={"checkpointId": ids["runtime_lab_checkpoint"], "reason": "missing_order"},
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
                _read_json(connection, "runtime_lab_checkpoint", ids["runtime_lab_checkpoint"], "collected")[
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


_TABLE_NAMES = [
    "workflow",
    "workflow_published_version",
    "chatflow_session",
    "chatflow_event",
    "chatflow_checkpoint",
    "chatflow_channel_config",
    "runtime_lab_session",
    "runtime_lab_task",
    "runtime_lab_checkpoint",
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


def _tables(names: list[str]) -> list[sa.Table]:
    return [Base.metadata.tables[name] for name in names]


def _insert(connection: Connection, table_name: str, **values: Any) -> int:
    result = connection.execute(Base.metadata.tables[table_name].insert().values(**values))
    return int(result.inserted_primary_key[0])


def _read_json(connection: Connection, table_name: str, row_id: int, column_name: str) -> Any:
    table = Base.metadata.tables[table_name]
    return connection.execute(sa.select(table.c[column_name]).where(table.c.id == row_id)).scalar_one()


if __name__ == "__main__":
    unittest.main()
