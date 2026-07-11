import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import multiprocessing
import os
from pathlib import Path
from threading import Barrier
from unittest.mock import patch


def _merge_memory_in_process(
    root: str,
    fact: str,
    barrier: object,
) -> None:
    from app.modules.ai_assistant.domain.markdown_memory import (
        MarkdownMemoryStore,
        MemoryScopeResolver,
    )

    resolver = MemoryScopeResolver(root)
    store = MarkdownMemoryStore(resolver)
    scope = resolver.resolve(
        trusted_user_id="alice",
        trusted_workspace_id="workspace-a",
    )
    getattr(barrier, "wait")()
    store.merge_today(
        scope,
        facts=[fact],
        today=date(2026, 7, 11),
    )


class MarkdownMemoryStoreTest(unittest.TestCase):
    def test_scoped_reader_returns_only_the_inclusive_rolling_30_day_window(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            memory_path = store.memory_path(scope)
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text(
                "# Memory\n\n"
                "## 2026-06-11\n"
                "- expired fact\n\n"
                "## 2026-06-12\n"
                "- boundary fact\n\n"
                "## 2026-07-11\n"
                "- current fact\n",
                encoding="utf-8",
            )

            window = store.read_recent(scope, today=date(2026, 7, 11))

        self.assertEqual(memory_path.name, "MEMORY.md")
        self.assertEqual(window.start_line, 6)
        self.assertNotIn("expired fact", window.content)
        self.assertIn("## 2026-06-12\n- boundary fact", window.content)
        self.assertIn("## 2026-07-11\n- current fact", window.content)

    def test_reader_excludes_malformed_and_future_date_blocks(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            memory_path = store.memory_path(scope)
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text(
                "# Memory\n\n"
                "## 2026-07-10\n"
                "- valid fact\n\n"
                "## not-a-date\n"
                "- malformed fact\n\n"
                "## 2026-99-99\n"
                "- impossible-date fact\n\n"
                "## 2026-07-12\n"
                "- future fact\n",
                encoding="utf-8",
            )

            window = store.read_recent(scope, today=date(2026, 7, 11))

        self.assertIn("valid fact", window.content)
        self.assertNotIn("malformed fact", window.content)
        self.assertNotIn("impossible-date fact", window.content)
        self.assertNotIn("future fact", window.content)
        self.assertEqual(
            window.warnings,
            (
                "invalid date heading: ## not-a-date",
                "invalid date heading: ## 2026-99-99",
            ),
        )

    def test_reader_reports_invalid_utf8_as_memory_format_error(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryFormatError,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            memory_path = store.memory_path(scope)
            memory_path.parent.mkdir(parents=True)
            memory_path.write_bytes(b"# Memory\n\n## 2026-07-11\n- \xff\n")

            with self.assertRaisesRegex(MemoryFormatError, "UTF-8"):
                store.read_recent(scope, today=date(2026, 7, 11))

    def test_reader_reports_duplicate_and_out_of_order_date_headings(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            memory_path = store.memory_path(scope)
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text(
                "# Memory\n\n"
                "## 2026-07-10\n- accepted\n\n"
                "## 2026-07-10\n- duplicate\n\n"
                "## 2026-07-09\n- out of order\n",
                encoding="utf-8",
            )

            window = store.read_recent(scope, today=date(2026, 7, 11))

        self.assertIn("accepted", window.content)
        self.assertNotIn("duplicate", window.content)
        self.assertNotIn("out of order", window.content)
        self.assertEqual(
            window.warnings,
            (
                "duplicate date heading: ## 2026-07-10",
                "out-of-order date heading: ## 2026-07-09",
            ),
        )

    def test_merge_today_preserves_history_and_deduplicates_daily_facts(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            memory_path = store.memory_path(scope)
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text(
                "# Memory\n\n"
                "## 2026-07-10\n"
                "- older fact\n\n"
                "## 2026-07-11\n"
                "- existing fact\n",
                encoding="utf-8",
            )

            result = store.merge_today(
                scope,
                facts=["existing fact", "new fact", "new fact"],
                today=date(2026, 7, 11),
            )

        self.assertIn("## 2026-07-10\n- older fact", result.content)
        self.assertIn("## 2026-07-11\n- existing fact\n- new fact", result.content)
        self.assertEqual(result.content.count("- new fact"), 1)

    def test_merge_today_caps_the_entire_day_and_retains_newest_fact(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )

            result = store.merge_today(
                scope,
                facts=[f"fact-{index:02d}-" + ("x" * 48) for index in range(16)],
                today=date(2026, 7, 11),
            )

        self.assertLessEqual(result.day_tokens, 100)
        self.assertIn("fact-15-", result.content)

    def test_daily_cap_drops_whole_oversized_fact_without_truncation(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        oversized = "oversized-" + ("x" * 500)
        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )

            result = store.merge_today(
                scope,
                facts=["stable fact", oversized],
                today=date(2026, 7, 11),
            )

        self.assertIn("- stable fact", result.content)
        self.assertNotIn("oversized-", result.content)
        self.assertEqual(result.dropped_facts, (oversized,))

    def test_atomic_replace_fsyncs_file_and_scope_directory(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )

            with patch(
                "app.modules.ai_assistant.domain.markdown_memory.os.fsync",
            ) as fsync:
                store.merge_today(
                    scope,
                    facts=["durable fact"],
                    today=date(2026, 7, 11),
                )

        self.assertGreaterEqual(fsync.call_count, 2)

    def test_atomic_replace_failure_keeps_original_and_cleans_temp_file(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            first = store.merge_today(
                scope,
                facts=["original fact"],
                today=date(2026, 7, 11),
            )
            memory_path = store.memory_path(scope)

            with patch(
                "app.modules.ai_assistant.domain.markdown_memory.os.replace",
                side_effect=OSError("replace failed"),
            ):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    store.merge_today(
                        scope,
                        facts=["new fact"],
                        today=date(2026, 7, 11),
                    )

            self.assertEqual(memory_path.read_text(encoding="utf-8"), first.content)
            self.assertEqual(list(memory_path.parent.glob(".MEMORY.md.*.tmp")), [])

    def test_scope_dirfd_prevents_symlink_swap_escape_during_replace(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "memory-root"
            outside = Path(tmp) / "outside"
            outside.mkdir()
            resolver = MemoryScopeResolver(root)
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            store.merge_today(
                scope,
                facts=["original fact"],
                today=date(2026, 7, 11),
            )
            memory_path = store.memory_path(scope)
            workspace_directory = memory_path.parent.parent
            quarantined = root / "quarantined"
            real_replace = os.replace
            swapped = False

            def swap_then_replace(
                source: str,
                target: str,
                *,
                src_dir_fd: int,
                dst_dir_fd: int,
            ) -> None:
                nonlocal swapped
                if not swapped:
                    workspace_directory.rename(quarantined)
                    workspace_directory.symlink_to(outside, target_is_directory=True)
                    swapped = True
                real_replace(
                    source,
                    target,
                    src_dir_fd=src_dir_fd,
                    dst_dir_fd=dst_dir_fd,
                )

            with patch(
                "app.modules.ai_assistant.domain.markdown_memory.os.replace",
                side_effect=swap_then_replace,
            ):
                store.merge_today(
                    scope,
                    facts=["new fact"],
                    today=date(2026, 7, 11),
                )

            quarantined_memory = quarantined / memory_path.parent.name / "MEMORY.md"
            self.assertIn("new fact", quarantined_memory.read_text(encoding="utf-8"))
            self.assertFalse((outside / memory_path.parent.name / "MEMORY.md").exists())

    def test_resolver_root_fd_survives_ancestor_symlink_swap(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            container = Path(tmp)
            trusted_parent = container / "trusted-parent"
            trusted_root = trusted_parent / "memory"
            outside_parent = container / "outside-parent"
            outside_root = outside_parent / "memory"
            trusted_root.mkdir(parents=True)
            outside_root.mkdir(parents=True)
            resolver = MemoryScopeResolver(trusted_root)
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            relative_memory_path = store.memory_path(scope).relative_to(
                resolver.root_path,
            )
            quarantined_parent = container / "trusted-parent-original"

            trusted_parent.rename(quarantined_parent)
            trusted_parent.symlink_to(outside_parent, target_is_directory=True)
            store.merge_today(
                scope,
                facts=["anchored fact"],
                today=date(2026, 7, 11),
            )

            self.assertTrue(
                (quarantined_parent / "memory" / relative_memory_path).exists(),
            )
            self.assertFalse((outside_root / relative_memory_path).exists())

    def test_concurrent_daily_merges_do_not_lose_facts(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            barrier = Barrier(16)

            def merge(index: int) -> None:
                barrier.wait()
                store.merge_today(
                    scope,
                    facts=[f"f{index:02d}"],
                    today=date(2026, 7, 11),
                )

            with ThreadPoolExecutor(max_workers=16) as pool:
                list(pool.map(merge, range(16)))

            window = store.read_recent(scope, today=date(2026, 7, 11))

        for index in range(16):
            self.assertIn(f"- f{index:02d}", window.content)

    def test_scope_paths_are_isolated_and_symlink_escape_is_rejected(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "memory-root"
            outside = Path(tmp) / "outside"
            root.mkdir()
            outside.mkdir()
            resolver = MemoryScopeResolver(root)
            store = MarkdownMemoryStore(resolver)
            alice = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            bob = resolver.resolve(
                trusted_user_id="bob",
                trusted_workspace_id="workspace-a",
            )

            alice_path = store.memory_path(alice)
            bob_path = store.memory_path(bob)

            self.assertNotEqual(alice_path, bob_path)
            self.assertNotIn("alice", str(alice_path))
            self.assertNotIn("bob", str(bob_path))

            workspace_directory = alice_path.parent.parent
            workspace_directory.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "inside configured root"):
                store.memory_path(alice)

    def test_store_accepts_only_scopes_issued_by_its_trusted_resolver(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            alice_workspace_a = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            alice_workspace_b = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-b",
            )
            bob_workspace_a = resolver.resolve(
                trusted_user_id="bob",
                trusted_workspace_id="workspace-a",
            )
            foreign_scope = MemoryScopeResolver(Path(tmp)).resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )

            store.merge_today(
                alice_workspace_a,
                facts=["alice-a fact"],
                today=date(2026, 7, 11),
            )

            self.assertEqual(
                store.read_recent(alice_workspace_b, today=date(2026, 7, 11)).content,
                "",
            )
            self.assertEqual(
                store.read_recent(bob_workspace_a, today=date(2026, 7, 11)).content,
                "",
            )
            with self.assertRaisesRegex(ValueError, "trusted resolver"):
                store.read_recent(foreign_scope, today=date(2026, 7, 11))

    def test_resolver_fails_closed_without_required_filesystem_flags(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MemoryScopeResolver,
            MemorySecurityCapabilityError,
        )

        with tempfile.TemporaryDirectory() as tmp, patch(
            "app.modules.ai_assistant.domain.markdown_memory._NOFOLLOW",
            0,
        ):
            with self.assertRaisesRegex(
                MemorySecurityCapabilityError,
                "O_NOFOLLOW",
            ):
                MemoryScopeResolver(Path(tmp))

    def test_resolver_fails_closed_without_flock_capability(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MemoryScopeResolver,
            MemorySecurityCapabilityError,
        )

        with tempfile.TemporaryDirectory() as tmp, patch(
            "app.modules.ai_assistant.domain.markdown_memory.fcntl.flock",
            None,
        ):
            with self.assertRaisesRegex(
                MemorySecurityCapabilityError,
                "flock",
            ):
                MemoryScopeResolver(Path(tmp))

    def test_reader_reports_malformed_headings_before_start_or_without_dates(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        documents = {
            "before-start": (
                "# Memory\n\n"
                "## invalid-before-start\n- ignored\n\n"
                "## 2026-07-10\n- accepted\n"
            ),
            "malformed-only": (
                "# Memory\n\n"
                "## invalid-only\n- ignored\n"
            ),
        }
        for name, document in documents.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                resolver = MemoryScopeResolver(Path(tmp))
                store = MarkdownMemoryStore(resolver)
                scope = resolver.resolve(
                    trusted_user_id="alice",
                    trusted_workspace_id="workspace-a",
                )
                memory_path = store.memory_path(scope)
                memory_path.parent.mkdir(parents=True)
                memory_path.write_text(document, encoding="utf-8")

                window = store.read_recent(scope, today=date(2026, 7, 11))

                self.assertTrue(window.warnings)
                self.assertIn("invalid date heading", window.warnings[0])

    def test_merge_rejects_noncanonical_history_without_changing_file(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryFormatError,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            resolver = MemoryScopeResolver(Path(tmp))
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            memory_path = store.memory_path(scope)
            memory_path.parent.mkdir(parents=True)
            original = (
                "# Memory\n\n"
                "## 2026-07-10\n"
                "- valid fact\n"
                "human note that must not disappear\n"
            )
            memory_path.write_text(original, encoding="utf-8")

            with self.assertRaisesRegex(MemoryFormatError, "noncanonical"):
                store.merge_today(
                    scope,
                    facts=["new fact"],
                    today=date(2026, 7, 11),
                )

            self.assertEqual(memory_path.read_text(encoding="utf-8"), original)

    def test_merge_rejects_duplicate_out_of_order_and_oversized_history(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryFormatError,
            MemoryScopeResolver,
        )

        invalid_documents = {
            "duplicate": (
                "# Memory\n\n"
                "## 2026-07-10\n- first\n\n"
                "## 2026-07-10\n- duplicate\n"
            ),
            "out-of-order": (
                "# Memory\n\n"
                "## 2026-07-10\n- newer\n\n"
                "## 2026-07-09\n- older\n"
            ),
            "oversized-history": (
                "# Memory\n\n"
                "## 2026-07-10\n- " + ("x" * 500) + "\n"
            ),
            "future": (
                "# Memory\n\n"
                "## 2026-07-12\n- future fact\n"
            ),
        }
        for name, original in invalid_documents.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                resolver = MemoryScopeResolver(Path(tmp))
                store = MarkdownMemoryStore(resolver)
                scope = resolver.resolve(
                    trusted_user_id="alice",
                    trusted_workspace_id="workspace-a",
                )
                memory_path = store.memory_path(scope)
                memory_path.parent.mkdir(parents=True)
                memory_path.write_text(original, encoding="utf-8")

                with self.assertRaises(MemoryFormatError):
                    store.merge_today(
                        scope,
                        facts=["new fact"],
                        today=date(2026, 7, 11),
                    )

                self.assertEqual(memory_path.read_text(encoding="utf-8"), original)

    def test_processes_share_flock_without_losing_daily_facts(self) -> None:
        from app.modules.ai_assistant.domain.markdown_memory import (
            MarkdownMemoryStore,
            MemoryScopeResolver,
        )

        with tempfile.TemporaryDirectory() as tmp:
            context = multiprocessing.get_context("fork")
            barrier = context.Barrier(8)
            processes = [
                context.Process(
                    target=_merge_memory_in_process,
                    args=(tmp, f"p{index:02d}", barrier),
                )
                for index in range(8)
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=10)
                self.assertEqual(process.exitcode, 0)

            resolver = MemoryScopeResolver(tmp)
            store = MarkdownMemoryStore(resolver)
            scope = resolver.resolve(
                trusted_user_id="alice",
                trusted_workspace_id="workspace-a",
            )
            window = store.read_recent(scope, today=date(2026, 7, 11))

        for index in range(8):
            self.assertIn(f"- p{index:02d}", window.content)


if __name__ == "__main__":
    unittest.main()
