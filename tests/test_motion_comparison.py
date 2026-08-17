from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compare_motion_v2 import estimate_cycles, longest_finite_run


class MotionComparisonTests(unittest.TestCase):
    def test_longest_finite_run_keeps_largest_contiguous_segment(self):
        import numpy as np

        values = np.asarray([math.nan, 1.0, 2.0, math.nan, 3.0, 4.0, 5.0, math.nan])
        self.assertEqual(longest_finite_run(values), (4, 6))

    def test_cycles_are_not_estimated_when_coverage_is_low(self):
        rows = [{"shoulder_planar_angle_deg": str(index)} for index in range(100)]
        result = estimate_cycles(rows, fps=25.0, coverage=0.2)
        self.assertEqual(result["status"], "NOT_ESTIMATED")
        self.assertIsNone(result["count"])


if __name__ == "__main__":
    unittest.main()
