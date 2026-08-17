from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "mujoco"))

from run_closed_loop_controller import interpolate, target_kinematics


class ClosedLoopControllerTests(unittest.TestCase):
    def test_target_angles_are_converted_to_radians(self):
        columns = ["time", "joint_a", "joint_b"]
        motion = np.asarray([[0.0, 0.0, 90.0], [1.0, 180.0, 90.0], [2.0, 180.0, 0.0]])
        times, qpos, qvel, qacc = target_kinematics(columns, motion, ["joint_a", "joint_b"])
        self.assertAlmostEqual(qpos[1, 0], np.pi)
        self.assertAlmostEqual(qpos[0, 1], np.pi / 2)
        self.assertEqual(qvel.shape, qpos.shape)
        self.assertEqual(qacc.shape, qpos.shape)

    def test_interpolation_uses_simulation_time(self):
        times = np.asarray([0.0, 1.0])
        values = np.asarray([[0.0, 2.0], [2.0, 4.0]])
        np.testing.assert_allclose(interpolate(0.5, times, values), [1.0, 3.0])


if __name__ == "__main__":
    unittest.main()
