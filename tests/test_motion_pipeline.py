import csv
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import convert_to_trc
import smooth_motion
import validate_motion


class MotionPipelineTests(unittest.TestCase):
    def test_short_gap_is_interpolated_but_long_gap_is_not(self):
        import numpy as np

        values = np.asarray([0.0, 1.0, math.nan, 3.0, math.nan, math.nan, 6.0])
        result, flags = smooth_motion.interpolate_short_gaps(values, max_gap=1)
        self.assertEqual(result[2], 2.0)
        self.assertTrue(flags[2])
        self.assertTrue(math.isnan(result[4]))
        self.assertTrue(math.isnan(result[5]))

    def test_smoothing_restores_missing_frame_and_time(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.csv"
            output = Path(directory) / "smooth.csv"
            with source.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["frame", "time_s", "r_shoulder_x", "r_shoulder_y", "r_shoulder_z"])
                writer.writeheader()
                for frame in (0, 1, 3, 4):
                    writer.writerow({"frame": frame, "time_s": frame / 10, "r_shoulder_x": frame, "r_shoulder_y": 0, "r_shoulder_z": 0})
            result = smooth_motion.main([
                "--input", str(source), "--output", str(output),
                "--cutoff-hz", "2", "--max-gap-frames", "1",
            ])
            self.assertEqual(result, 0)
            with output.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([int(row["frame"]) for row in rows], [0, 1, 2, 3, 4])
            self.assertAlmostEqual(float(rows[2]["time_s"]), 0.2)
            self.assertEqual(rows[2]["interpolated"], "1")

    def test_quality_gate_passes_constant_segments(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "motion.csv"
            fields = [
                "frame", "time_s",
                "r_shoulder_x", "r_shoulder_y", "r_shoulder_z",
                "r_elbow_x", "r_elbow_y", "r_elbow_z",
                "r_wrist_x", "r_wrist_y", "r_wrist_z",
            ]
            with source.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for frame in range(20):
                    writer.writerow({
                        "frame": frame, "time_s": frame / 30,
                        "r_shoulder_x": 0, "r_shoulder_y": 0, "r_shoulder_z": 0,
                        "r_elbow_x": 0.3, "r_elbow_y": 0, "r_elbow_z": 0,
                        "r_wrist_x": 0.57, "r_wrist_y": 0, "r_wrist_z": 0,
                    })
            report = validate_motion.analyze(source, 0.02, 0.10, 0)
            self.assertEqual(report["status"], "PASS")
            self.assertAlmostEqual(report["segments"]["r_shoulder->r_elbow"]["cv"], 0)

    def test_trc_uses_original_time_and_explicit_calibration(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source, calibration, output = directory / "motion.csv", directory / "calibration.json", directory / "motion.trc"
            fields = [
                "frame", "time_s",
                "r_shoulder_x", "r_shoulder_y", "r_shoulder_z",
                "r_elbow_x", "r_elbow_y", "r_elbow_z",
                "r_wrist_x", "r_wrist_y", "r_wrist_z",
            ]
            with source.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for frame in range(3):
                    writer.writerow({
                        "frame": frame, "time_s": frame * 0.1,
                        "r_shoulder_x": 0, "r_shoulder_y": 0, "r_shoulder_z": 0,
                        "r_elbow_x": 0.3, "r_elbow_y": 0, "r_elbow_z": 0,
                        "r_wrist_x": 0.57, "r_wrist_y": 0, "r_wrist_z": 0,
                    })
            calibration.write_text(json.dumps({
                "analysis_valid": True, "scale_mm_per_unit": 1000,
                "transform_4x4": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
            }), encoding="utf-8")
            result = convert_to_trc.main([
                "--input", str(source), "--calibration", str(calibration), "--output", str(output),
            ])
            self.assertEqual(result, 0)
            text = output.read_text(encoding="utf-8")
            self.assertIn("10\t10\t3\t3\tmm", text)
            self.assertIn("2\t0.10000000", text)
            self.assertIn("300.000000", text)


if __name__ == "__main__":
    unittest.main()
