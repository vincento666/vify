import unittest
import threading
from concurrent.futures import ThreadPoolExecutor

import sqlalchemy as sa
from tests.support.mysql import mysql8_unittest_database


class AiAssistantResourceLockTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_resource_lock_unit",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory

    def tearDown(self) -> None:
        self._engine.dispose()

    def test_read_read_compatible_write_contention_and_expired_lease_reacquire(self) -> None:
        from app.modules.ai_assistant.domain.resource_lock import ResourceLockManager, ResourceLockMode
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with self._factory() as session:
            manager = ResourceLockManager(AiAssistantRepository(session))

            read1 = manager.acquire(
                resource_key="file:shared.txt",
                mode=ResourceLockMode.READ,
                owner_session_id=1,
                owner_run_id=10,
                ttl_seconds=60,
            )
            read2 = manager.acquire(
                resource_key="file:shared.txt",
                mode=ResourceLockMode.READ,
                owner_session_id=2,
                owner_run_id=20,
                ttl_seconds=60,
            )
            write_blocked = manager.acquire(
                resource_key="file:shared.txt",
                mode=ResourceLockMode.WRITE,
                owner_session_id=3,
                owner_run_id=30,
                ttl_seconds=60,
            )
            expired = manager.acquire(
                resource_key="file:expired.txt",
                mode=ResourceLockMode.WRITE,
                owner_session_id=4,
                owner_run_id=40,
                ttl_seconds=-1,
            )
            reacquired = manager.acquire(
                resource_key="file:expired.txt",
                mode=ResourceLockMode.WRITE,
                owner_session_id=5,
                owner_run_id=50,
                ttl_seconds=60,
            )

        self.assertEqual(read1.status, "ACQUIRED")
        self.assertEqual(read2.status, "ACQUIRED")
        self.assertEqual(write_blocked.status, "CONTENDED")
        self.assertEqual(write_blocked.observation["error"]["code"], "RESOURCE_LOCK_CONTENDED")
        self.assertEqual(expired.status, "ACQUIRED")
        self.assertEqual(reacquired.status, "ACQUIRED")
        self.assertGreater(reacquired.fencing_token, expired.fencing_token)
        self.assertEqual(reacquired.events[0]["type"], "resource_lock.acquire_requested")
        self.assertEqual(reacquired.events[1]["type"], "resource_lock.acquired")

    def test_stale_owner_cannot_release_or_renew_active_lease(self) -> None:
        from app.modules.ai_assistant.domain.resource_lock import ResourceLockManager, ResourceLockMode
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with self._factory() as session:
            manager = ResourceLockManager(AiAssistantRepository(session))
            acquired = manager.acquire(
                resource_key="file:owned.txt",
                mode=ResourceLockMode.WRITE,
                owner_session_id=7,
                owner_run_id=70,
                ttl_seconds=60,
            )
            stale_release = manager.release(
                resource_key="file:owned.txt",
                owner_session_id=8,
                owner_run_id=80,
                fencing_token=acquired.fencing_token,
            )
            stale_renew = manager.renew(
                resource_key="file:owned.txt",
                owner_session_id=8,
                owner_run_id=80,
                fencing_token=acquired.fencing_token,
                ttl_seconds=60,
            )
            released = manager.release(
                resource_key="file:owned.txt",
                owner_session_id=7,
                owner_run_id=70,
                fencing_token=acquired.fencing_token,
            )

        self.assertFalse(stale_release)
        self.assertFalse(stale_renew)
        self.assertTrue(released)

    def test_concurrent_write_acquire_allows_only_one_active_writer(self) -> None:
        from app.modules.ai_assistant.domain.resource_lock import ResourceLockManager, ResourceLockMode
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        barrier = threading.Barrier(2)

        def pause_before_insert(
            _conn: object,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: bool,
        ) -> None:
            if "INSERT INTO ai_assistant_resource_lock" not in statement:
                return
            try:
                barrier.wait(timeout=2)
            except threading.BrokenBarrierError:
                return

        sa.event.listen(self._engine, "before_cursor_execute", pause_before_insert)
        try:
            def acquire(owner_run_id: int) -> str:
                with self._factory() as session:
                    result = ResourceLockManager(AiAssistantRepository(session)).acquire(
                        resource_key="file:concurrent.txt",
                        mode=ResourceLockMode.WRITE,
                        owner_session_id=owner_run_id,
                        owner_run_id=owner_run_id,
                        ttl_seconds=60,
                    )
                    return result.status

            with ThreadPoolExecutor(max_workers=2) as executor:
                statuses = list(executor.map(acquire, [101, 202]))
        finally:
            sa.event.remove(self._engine, "before_cursor_execute", pause_before_insert)

        self.assertEqual(statuses.count("ACQUIRED"), 1)
        self.assertEqual(statuses.count("CONTENDED"), 1)


if __name__ == "__main__":
    unittest.main()
