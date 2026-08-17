from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "rl"))

from exploratory_assist_env import ExploratoryAssistEnv
from generate_synthetic_target import generate, write_mot


class ExploratoryRLSandboxTests(unittest.TestCase):
    def test_synthetic_target_stays_inside_configured_joint_ranges(self):
        config = json.loads(
            (ROOT / "config" / "rl" / "exploratory_sandbox_v1.json").read_text(encoding="utf-8")
        )
        _, shoulder, elbow = generate(config["target_generator"])
        self.assertGreater(float(np.min(shoulder)), -68.0)
        self.assertLess(float(np.max(shoulder)), 85.0)
        self.assertGreater(float(np.min(elbow)), 3.0)
        self.assertLess(float(np.max(elbow)), 128.0)

    def test_environment_exposes_only_two_normalized_exo_actions(self):
        base = json.loads(
            (ROOT / "config" / "rl" / "exploratory_sandbox_v1.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            time, shoulder, elbow = generate(base["target_generator"])
            target = root / "target.mot"
            write_mot(target, time, shoulder, elbow)
            base["model"] = str((ROOT / base["model"]).resolve())
            base["target"] = str(target)
            config = root / "config.json"
            config.write_text(json.dumps(base), encoding="utf-8")
            env = ExploratoryAssistEnv(config)
            observation, info = env.reset(seed=1)
            self.assertEqual(env.action_space.shape, (2,))
            self.assertEqual(observation.shape, env.observation_space.shape)
            self.assertEqual(info["scientific_status"], "SOFTWARE_EXPLORATION_ONLY")
            _, reward, _, _, step_info = env.step(np.zeros(2, dtype=np.float32))
            self.assertTrue(np.isfinite(reward))
            self.assertEqual(step_info["scientific_status"], "SOFTWARE_EXPLORATION_ONLY")
            env.close()


if __name__ == "__main__":
    unittest.main()
