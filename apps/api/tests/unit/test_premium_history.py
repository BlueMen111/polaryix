from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import Future
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
from pathlib import Path

from app.core import conversion_history
from app.core.config.settings import settings
from app.core.conversion_queue import QueuedJob
from app.core.premium import get_plan_limits


class PremiumPlanTests(unittest.TestCase):
    def test_basic_plan_limits(self) -> None:
        plan = get_plan_limits("basic", "annual", True)

        self.assertEqual(plan.monthly_credits, 1000)
        self.assertEqual(plan.max_file_size_mb, 300)
        self.assertEqual(plan.max_concurrent_conversions, 30)
        self.assertEqual(plan.priority_level, 50)

    def test_pro_plan_uses_sixty_concurrent_conversions(self) -> None:
        plan = get_plan_limits("pro", "annual", True)

        self.assertEqual(plan.monthly_credits, 3000)
        self.assertEqual(plan.max_file_size_mb, 1024)
        self.assertEqual(plan.max_concurrent_conversions, 60)
        self.assertEqual(plan.priority_level, 100)

    def test_free_plan_is_not_premium(self) -> None:
        plan = get_plan_limits("free", "daily", False)

        self.assertEqual(plan.monthly_credits, 30)
        self.assertFalse(plan.is_premium)


class ConversionHistoryCleanupTests(unittest.TestCase):
    def test_cleanup_deletes_files_and_preserves_history(self) -> None:
        original_storage = settings.storage_path
        original_retention = settings.file_retention_hours

        with tempfile.TemporaryDirectory() as temp_dir:
            settings.storage_path = Path(temp_dir)
            settings.file_retention_hours = 12
            output = settings.storage_path / "processed" / "expired.txt"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("done", encoding="utf-8")
            record = conversion_history.create_conversion_record(
                user_id="user-1",
                original_filename="input.txt",
                original_format="TXT",
                target_format="TXT",
                output_path=str(output),
                status="completed",
                expires_at=(datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            )

            result = conversion_history.cleanup_expired_files()
            records = conversion_history.list_user_records("user-1")

            self.assertEqual(result["deleted_files"], 1)
            self.assertFalse(output.exists())
            self.assertEqual(records[0]["id"], record["id"])
            self.assertEqual(records[0]["status"], "expired")
            self.assertIsNotNone(records[0]["deleted_at"])

            second_result = conversion_history.cleanup_expired_files()
            self.assertEqual(second_result["deleted_files"], 0)
        settings.storage_path = original_storage
        settings.file_retention_hours = original_retention


class ConversionQueueTests(unittest.TestCase):
    def test_priority_sorting_processes_pro_before_basic_and_free(self) -> None:
        free = QueuedJob(sort_key=(0, 1), future=Future(), function=lambda: "free")
        basic = QueuedJob(sort_key=(-50, 2), future=Future(), function=lambda: "basic")
        pro = QueuedJob(sort_key=(-100, 3), future=Future(), function=lambda: "pro")

        self.assertEqual([job.function() for job in sorted([free, pro, basic])], ["pro", "basic", "free"])

    def test_same_priority_keeps_arrival_order(self) -> None:
        first = QueuedJob(sort_key=(-50, 1), future=Future(), function=lambda: "first")
        second = QueuedJob(sort_key=(-50, 2), future=Future(), function=lambda: "second")

        self.assertEqual([job.function() for job in sorted([second, first])], ["first", "second"])


if __name__ == "__main__":
    unittest.main()
