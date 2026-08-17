from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from create_mujoco_target import map_angles


class MujocoTargetTests(unittest.TestCase):
    def test_camera_vertical_maps_to_zero_shoulder_elevation(self):
        mapping = {
            "shoulder": {
                "source_column": "shoulder", "reference_axis_deg": -90,
                "scale": -1, "target_coordinate": "r_shoulder_elev",
            },
            "elbow": {
                "source_column": "elbow", "offset_deg": 0,
                "scale": 1, "target_coordinate": "r_elbow_flex",
            },
        }
        result = map_angles({"shoulder": "-90", "elbow": "65"}, mapping)
        self.assertAlmostEqual(result["r_shoulder_elev"], 0.0)
        self.assertAlmostEqual(result["r_elbow_flex"], 65.0)


if __name__ == "__main__":
    unittest.main()
