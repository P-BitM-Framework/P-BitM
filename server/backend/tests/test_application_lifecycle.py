import os
import unittest
from unittest.mock import MagicMock, patch

import main


class SchedulerConfigurationTests(unittest.TestCase):
    def test_registers_expected_idempotent_jobs(self):
        scheduler = MagicMock()

        main.configure_scheduler(scheduler)

        self.assertEqual(scheduler.add_job.call_count, 2)
        jobs = {
            call.kwargs["id"]: call.kwargs
            for call in scheduler.add_job.call_args_list
        }
        self.assertEqual(set(jobs), {"email_sender", "runtime_reconciler"})
        self.assertTrue(jobs["email_sender"]["replace_existing"])
        self.assertTrue(jobs["runtime_reconciler"]["replace_existing"])


class SeedConfigurationTests(unittest.TestCase):
    def test_does_not_import_seed_module_when_disabled(self):
        with (
            patch.dict(os.environ, {"SEED_DATA": "false"}),
            patch.dict("sys.modules", {"seed_data": None}),
        ):
            main.seed_initial_data()

    def test_seed_failure_is_not_silenced(self):
        with (
            patch.dict(os.environ, {"SEED_DATA": "true"}),
            patch("seed_data.seed_all", side_effect=RuntimeError("invalid seed")),
            self.assertRaisesRegex(RuntimeError, "invalid seed"),
        ):
            main.seed_initial_data()


if __name__ == "__main__":
    unittest.main()
