import unittest

import reproduce


class CommandRunnerAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = reproduce.run_audit()

    def test_all_documented_assertions(self):
        reproduce.assert_report(self.report)
        self.assertEqual(len(self.report["assertions"]), 18)

    def test_scope_count(self):
        self.assertEqual(
            self.report["scope"],
            {"affected_tasks": 7, "affected_commands": 9, "benchmark_tasks": 104},
        )

    def test_parse_race_is_observed_before_shell_exit(self):
        trace = self.report["parse_race"]["prime"]["trace"]
        self.assertIn("pytest_seen_editable=0", trace)
        self.assertTrue(self.report["parse_race"]["prime"]["editable_finished_at_shell_exit"])


if __name__ == "__main__":
    unittest.main()
