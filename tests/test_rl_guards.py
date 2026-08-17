import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@unittest.skipUnless(importlib.util.find_spec("mujoco") and importlib.util.find_spec("gymnasium"), "MuJoCo/Gymnasium absents")
class ReinforcementLearningGuardTests(unittest.TestCase):
    def test_human_muscle_only_model_is_rejected(self):
        from exo_env import BrasOuvriereEnv

        with self.assertRaisesRegex(ValueError, "Aucun actionneur 'exo_\\*'"):
            BrasOuvriereEnv(
                PROJECT_ROOT / "models/mujoco/v2/mujoco_models_v2/arm26_scaled_cvt3_mujoco36.xml",
                PROJECT_ROOT / "data/opensim/ik_results.mot",
            )


if __name__ == "__main__":
    unittest.main()
