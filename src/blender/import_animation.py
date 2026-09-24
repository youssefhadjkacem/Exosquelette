"""Import an arm26-style .mot trajectory onto the MPFB2 rig's right arm.

Run headless from the project root, e.g.:

    "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background \
        "C:\\Users\\youss\\mpfb-data\\femme.blend" --python src/blender/import_animation.py -- \
        --mot data/scenarios/pipeline_principal/target_arm26_exploratory.mot

Only the right shoulder (upperarm01.R) and right elbow (lowerarm01.R) are
keyframed. Everything else on the armature is reset to its rest pose and left
alone: arm26 has no data for the rest of the body, so nothing else should move.

Axis/sign mapping (verified empirically against the actual femme.blend rig,
not assumed from convention):
  - r_shoulder_elev -> upperarm01.R local Z rotation, NEGATED. The bone's
    local Z axis is the one that sweeps the arm in the vertical plane (world Y
    stays ~constant while rotating); the raw (unnegated) sign lowers the arm
    as the angle increases, so it must be flipped for elevation to mean "up".
  - r_elbow_flex -> lowerarm01.R local X rotation, unchanged sign. This axis
    already matched the true elbow hinge axis (computed as the cross product
    of the upper-arm and forearm rest directions).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

RIG_NAME = "Human.rig"
SHOULDER_BONE = "upperarm01.R"
ELBOW_BONE = "lowerarm01.R"


def parse_args(argv: list[str]) -> dict:
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    args = {"mot": None, "fps": None, "save": True}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--mot":
            args["mot"] = argv[i + 1]
            i += 2
        elif token == "--fps":
            args["fps"] = float(argv[i + 1])
            i += 2
        elif token == "--no-save":
            args["save"] = False
            i += 1
        else:
            raise ValueError(f"Argument inconnu: {token}")
    if args["mot"] is None:
        raise ValueError("--mot <chemin vers un .mot arm26 (time, r_shoulder_elev, r_elbow_flex)> est requis")
    return args


def read_mot(path: Path) -> tuple[list[str], list[list[float]], bool, float]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    end = next(i for i, line in enumerate(lines) if line.strip().lower() == "endheader")
    header = lines[: end + 1]
    columns = lines[end + 1].split()
    rows = [[float(v) for v in line.split()] for line in lines[end + 2 :] if line.strip()]
    in_degrees = any(line.strip().lower() == "indegrees=yes" for line in header)
    fps_line = next((line for line in header if line.strip().lower().startswith("fps=")), None)
    fps = float(fps_line.split("=")[1]) if fps_line else None
    return columns, rows, in_degrees, fps


def reset_armature_to_rest(rig) -> None:
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)


def main() -> None:
    args = parse_args(sys.argv)
    mot_path = Path(args["mot"])
    if not mot_path.is_absolute():
        mot_path = Path(bpy.path.abspath("//")) / mot_path
    columns, rows, in_degrees, mot_fps = read_mot(mot_path)
    if not in_degrees:
        raise ValueError(f"{mot_path} n'est pas en degres (inDegrees=yes attendu)")
    for required in ("time", "r_shoulder_elev", "r_elbow_flex"):
        if required not in columns:
            raise ValueError(f"Colonne manquante dans {mot_path}: {required}")
    time_i = columns.index("time")
    shoulder_i = columns.index("r_shoulder_elev")
    elbow_i = columns.index("r_elbow_flex")

    rig = bpy.data.objects.get(RIG_NAME)
    if rig is None:
        raise ValueError(f"Rig '{RIG_NAME}' introuvable dans la scene")

    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")

    # Whole rig starts from a known, clean rest pose. arm26 only has data for
    # the right shoulder and elbow, so nothing else is touched afterwards.
    reset_armature_to_rest(rig)

    shoulder_bone = rig.pose.bones[SHOULDER_BONE]
    elbow_bone = rig.pose.bones[ELBOW_BONE]
    shoulder_bone.rotation_mode = "XYZ"
    elbow_bone.rotation_mode = "XYZ"

    scene = bpy.context.scene
    fps = args["fps"] or mot_fps
    if fps is None:
        dt = rows[1][time_i] - rows[0][time_i]
        fps = 1.0 / dt
    scene.render.fps = round(fps)
    scene.frame_start = 1
    scene.frame_end = len(rows)

    for index, row in enumerate(rows):
        frame = index + 1
        scene.frame_set(frame)

        shoulder_bone.rotation_euler = (0.0, 0.0, 0.0)
        elbow_bone.rotation_euler = (0.0, 0.0, 0.0)
        shoulder_bone.rotation_euler[2] = -math.radians(row[shoulder_i])
        elbow_bone.rotation_euler[0] = math.radians(row[elbow_i])

        shoulder_bone.keyframe_insert(data_path="rotation_euler", index=2, frame=frame)
        elbow_bone.keyframe_insert(data_path="rotation_euler", index=0, frame=frame)

    bpy.context.view_layer.update()
    scene.frame_set(1)

    print(f"Animation importee: {len(rows)} frames a {scene.render.fps} fps depuis {mot_path}")

    if args["save"]:
        bpy.ops.wm.save_mainfile()
        print(f"Fichier sauvegarde: {bpy.data.filepath}")


if __name__ == "__main__":
    main()
