from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "acquisition"))

from validate_v3_session import analyze


class AcquisitionV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads(
            (ROOT / "config" / "acquisition" / "v3_protocol.json").read_text(encoding="utf-8")
        )
        cls.template = json.loads(
            (ROOT / "config" / "acquisition" / "v3_session.example.json").read_text(encoding="utf-8")
        )

    def test_empty_template_is_prepared_but_not_ready(self):
        report = analyze(self.protocol, self.template)
        self.assertEqual(report["status"], "PREPARED_AWAITING_CAPTURE")
        self.assertFalse(report["ready_for_3d_reconstruction"])
        self.assertFalse(report["rl_scientific_allowed"])

    def test_complete_consistent_session_is_ready_for_reconstruction_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            videos = [root / "camera_1.mp4", root / "camera_2.mp4"]
            calibration = root / "calibration.json"
            for video in videos:
                video.write_bytes(b"fixture")
            calibration.write_text("{}", encoding="utf-8")
            session = json.loads(json.dumps(self.template))
            session["participant"].update({
                "stature_m": 1.70, "mass_kg": 65.0,
                "right_upper_arm_length_m": 0.30, "right_forearm_length_m": 0.25,
            })
            session["task"].update({
                "iron_mass_kg": 1.2, "table_height_m": 0.90, "complete_cycles_recorded": 12,
            })
            for index, camera in enumerate(session["cameras"]):
                camera.update({
                    "video": str(videos[index]), "calibration_file": str(calibration), "fps": 30.0,
                    "resolution": [1280, 720], "duration_s": 20.0,
                    "sync_event_start_frame": 5, "sync_event_end_frame": 595,
                    "all_required_landmarks_visible": True,
                })
            session["checklist"] = {key: True for key in session["checklist"]}
            report = analyze(self.protocol, session)
            self.assertEqual(report["status"], "READY_FOR_3D_RECONSTRUCTION")
            self.assertFalse(report["opensim_allowed"])
            self.assertFalse(report["rl_scientific_allowed"])


if __name__ == "__main__":
    unittest.main()
