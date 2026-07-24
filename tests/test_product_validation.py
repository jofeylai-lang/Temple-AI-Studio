from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.product_validation import (
    analyze_failures,
    build_acceptance_results,
    build_cases,
    build_reliability_report,
    determine_readiness,
    run_validation,
)


class ProductValidationTests(unittest.TestCase):
    def test_build_cases_covers_required_edge_modes(self) -> None:
        cases = build_cases(100)
        self.assertEqual(len(cases), 100)
        modes = {case.asset_mode for case in cases}
        self.assertIn("valid", modes)
        self.assertIn("long_subtitle", modes)
        self.assertIn("multilingual", modes)
        self.assertIn("missing_assets", modes)
        self.assertIn("invalid_assets", modes)
        self.assertIn("empty_assets", modes)

    def test_reliability_and_readiness_for_passing_results(self) -> None:
        results = [
            {"caseId": "A", "status": "PASS", "expected": "production_export", "accepted": True, "failure": None, "quality": {"overall": "PASS"}, "timings": {"scriptSeconds": 0.1, "totalSeconds": 1.0}, "disk": {"exportBytes": 1}, "memory": {"tracemallocPeakBytes": 1}},
            {"caseId": "B", "status": "HANDLED_EXPECTED_FAILURE", "expected": "handled_input_failure", "accepted": True, "failure": {"category": "input-validation", "severity": "major"}, "timings": {"scriptSeconds": 0.1, "totalSeconds": 0.5}, "disk": {"exportBytes": 0}, "memory": {"tracemallocPeakBytes": 1}},
        ]
        concurrent = {"overall": "PASS"}
        acceptance = build_acceptance_results(results, concurrent)
        failures = analyze_failures(results)
        reliability = build_reliability_report(results)
        performance = {"singleProjectAverageSeconds": 1.0}
        readiness = determine_readiness(acceptance, reliability, failures, performance)
        self.assertEqual(acceptance["overall"], "PASS")
        self.assertEqual(reliability["validProductionSuccessRate"], 1.0)
        self.assertEqual(readiness["level"], "PRODUCTION READY")

    def test_mini_validation_handles_missing_assets_without_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary = run_validation(
                6,
                artifact_root=root / "artifacts",
                report_root=root / "reports",
                skip_concurrent_probe=True,
            )
            self.assertIn("readiness", summary)
            self.assertTrue(Path(summary["reportDir"]).exists())
            self.assertTrue((Path(summary["reportDir"]) / "acceptance-dashboard.md").exists())


if __name__ == "__main__":
    unittest.main()
