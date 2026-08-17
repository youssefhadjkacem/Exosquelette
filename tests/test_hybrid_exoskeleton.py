from __future__ import annotations

import json
import unittest
from pathlib import Path

import mujoco


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "mujoco" / "exoskeleton" / "hybrid_active_v1.xml"
OPTIMIZED_MODEL = ROOT / "models" / "mujoco" / "exoskeleton" / "hybrid_optimized_v2.xml"
CONFIG = ROOT / "config" / "exoskeleton" / "hybrid_active_v1.json"


class HybridExoskeletonTests(unittest.TestCase):
    def setUp(self):
        self.model = mujoco.MjModel.from_xml_path(str(MODEL))
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_exoskeleton_motors_are_independent_and_limited(self):
        names = [
            mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, index)
            for index in range(self.model.nu)
        ]
        for name in ("exo_shoulder_motor", "exo_elbow_motor"):
            index = names.index(name)
            self.assertTrue(self.model.actuator_ctrllimited[index])
            self.assertTrue(self.model.actuator_forcelimited[index])

    def test_passive_springs_and_added_components_exist(self):
        body_names = {
            mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, index)
            for index in range(self.model.nbody)
        }
        self.assertTrue({"exo_harness", "exo_upper_arm_rail", "exo_forearm_rail"} <= body_names)
        for joint_name, expected in self.config["joints"].items():
            index = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            self.assertAlmostEqual(self.model.jnt_stiffness[index], expected["spring_stiffness_nm_per_rad"])

    def test_model_steps_with_zero_motor_command(self):
        data = mujoco.MjData(self.model)
        for _ in range(20):
            mujoco.mj_step(self.model, data)
        self.assertGreater(data.time, 0.0)

    def test_optimized_model_loads_with_expected_springs(self):
        model = mujoco.MjModel.from_xml_path(str(OPTIMIZED_MODEL))
        shoulder = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "r_shoulder_elev")
        elbow = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "r_elbow_flex")
        self.assertAlmostEqual(model.jnt_stiffness[shoulder], 2.25)
        self.assertAlmostEqual(model.jnt_stiffness[elbow], 1.75)


if __name__ == "__main__":
    unittest.main()
