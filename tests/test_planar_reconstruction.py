from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reconstruct_planar_arm import reconstruct_row


class PlanarReconstructionTests(unittest.TestCase):
    def test_fixed_lengths_and_image_y_flip(self):
        row = {
            "frame": "12", "time_s": "0.4",
            "r_shoulder_x": "0", "r_shoulder_y": "0",
            "r_elbow_x": "2", "r_elbow_y": "0",
            "r_wrist_x": "2", "r_wrist_y": "3",
        }
        result = reconstruct_row(row, upper_arm_m=0.30, forearm_m=0.25)
        self.assertEqual(result["source_valid"], 1)
        self.assertAlmostEqual(result["r_elbow_x"], 0.30)
        self.assertAlmostEqual(result["r_elbow_y"], 0.0)
        self.assertAlmostEqual(result["r_wrist_x"], 0.30)
        self.assertAlmostEqual(result["r_wrist_y"], -0.25)
        upper = math.hypot(result["r_elbow_x"], result["r_elbow_y"])
        forearm = math.hypot(
            result["r_wrist_x"] - result["r_elbow_x"],
            result["r_wrist_y"] - result["r_elbow_y"],
        )
        self.assertAlmostEqual(upper, 0.30)
        self.assertAlmostEqual(forearm, 0.25)

    def test_missing_source_produces_invalid_row(self):
        row = {
            "frame": "0", "time_s": "0",
            "r_shoulder_x": "", "r_shoulder_y": "",
            "r_elbow_x": "1", "r_elbow_y": "1",
            "r_wrist_x": "2", "r_wrist_y": "2",
        }
        result = reconstruct_row(row, 0.30, 0.25)
        self.assertEqual(result["source_valid"], 0)
        self.assertEqual(result["r_wrist_x"], "")


if __name__ == "__main__":
    unittest.main()
