"""Attach the complete iron asset to the animated right hand with a safe offset."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


RIG_NAME = "Human.rig"
IRON_MESH_NAME = "Iron"
IRON_ROOT_NAME = "Old Iron"
HAND_BONE = "metacarpal3.R"
CONSTRAINT_NAME = "Iron follows right hand"
REFERENCE_FRAME = 541
SCALE_FACTOR = Vector((0.65, 0.65, 0.25))
GRIP_YAW_DEGREES = 50.0
PALM_OFFSET_M = Vector((0.0, 0.0, -0.015))
BOARD_NAME = "White_desk"
MINIMUM_BOARD_CLEARANCE_M = 0.006


def parse_args() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--report")
    parser.add_argument("--scale-factor", default=",".join(str(value) for value in SCALE_FACTOR))
    parser.add_argument("--yaw-degrees", type=float, default=GRIP_YAW_DEGREES)
    parser.add_argument("--palm-offset", default=",".join(str(value) for value in PALM_OFFSET_M))
    return parser.parse_args(raw)


def vector_argument(value: str) -> Vector:
    components = [float(component) for component in value.split(",")]
    if len(components) != 3:
        raise ValueError(f"Vecteur attendu sous la forme x,y,z: {value}")
    return Vector(components)


def vec(value) -> list[float]:
    return [round(float(component), 6) for component in value]


def bounds_world(obj) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector([min(point[index] for point in points) for index in range(3)]),
        Vector([max(point[index] for point in points) for index in range(3)]),
    )


def handle_anchor_local(iron) -> Vector:
    vertices = [vertex.co.copy() for vertex in iron.data.vertices]
    minimum_z = min(point.z for point in vertices)
    maximum_z = max(point.z for point in vertices)
    threshold = minimum_z + 0.75 * (maximum_z - minimum_z)
    elevated = [point for point in vertices if point.z >= threshold]
    return sum(elevated, Vector()) / len(elevated)


def bone_head_world(rig, bone_name: str) -> Vector:
    return rig.matrix_world @ rig.pose.bones[bone_name].head


def bone_midpoint_world(rig, bone_name: str) -> Vector:
    bone = rig.pose.bones[bone_name]
    return rig.matrix_world @ ((bone.head + bone.tail) * 0.5)


def main() -> None:
    args = parse_args()
    scale_factor = vector_argument(args.scale_factor)
    palm_offset = vector_argument(args.palm_offset)
    scene = bpy.context.scene
    rig = bpy.data.objects.get(RIG_NAME)
    iron = bpy.data.objects.get(IRON_MESH_NAME)
    root = bpy.data.objects.get(IRON_ROOT_NAME)
    board = bpy.data.objects.get(BOARD_NAME)
    if not rig or rig.type != "ARMATURE":
        raise ValueError(f"Rig '{RIG_NAME}' introuvable")
    if not iron or iron.type != "MESH" or not root or iron.parent != root:
        raise ValueError("La hierarchie Old Iron -> Iron est absente ou inattendue")
    if HAND_BONE not in rig.pose.bones:
        raise ValueError(f"Os de main '{HAND_BONE}' introuvable")
    if not board or board.type != "MESH":
        raise ValueError(f"Plan de travail '{BOARD_NAME}' introuvable")

    scene.frame_set(REFERENCE_FRAME)
    bpy.context.view_layer.update()
    for constraint in list(root.constraints):
        if constraint.name == CONSTRAINT_NAME:
            root.constraints.remove(constraint)
    root.location = (0.0, 0.0, 0.0)
    root.rotation_mode = "XYZ"
    root.rotation_euler = (0.0, 0.0, math.radians(args.yaw_degrees))

    if "iron_attachment_original_scale" not in iron:
        iron["iron_attachment_original_scale"] = list(iron.scale)
    original_scale = Vector(iron["iron_attachment_original_scale"])
    iron.scale = Vector([
        original_scale[index] * scale_factor[index] for index in range(3)
    ])
    bpy.context.view_layer.update()

    anchor_local = handle_anchor_local(iron)
    anchor_without_constraint = iron.matrix_world @ anchor_local
    palm_world = bone_midpoint_world(rig, HAND_BONE)
    required_root_translation = palm_world + palm_offset - anchor_without_constraint
    target_head = bone_head_world(rig, HAND_BONE)

    constraint = root.constraints.new(type="COPY_LOCATION")
    constraint.name = CONSTRAINT_NAME
    constraint.target = rig
    constraint.subtarget = HAND_BONE
    constraint.target_space = "WORLD"
    constraint.owner_space = "WORLD"
    constraint.use_x = True
    constraint.use_y = True
    constraint.use_z = True
    constraint.use_offset = True
    root.location = required_root_translation - target_head
    root["attachment_target"] = f"{RIG_NAME}/{HAND_BONE}"
    root["attachment_reference_frame"] = REFERENCE_FRAME
    root["attachment_method"] = "COPY_LOCATION with fixed world rotation"
    bpy.context.view_layer.update()

    board_top = bounds_world(board)[1].z
    minimum_clearance = float("inf")
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        iron_minimum, _ = bounds_world(iron)
        minimum_clearance = min(minimum_clearance, iron_minimum.z - board_top)
    clearance_correction = max(0.0, MINIMUM_BOARD_CLEARANCE_M - minimum_clearance)
    root.location.z += clearance_correction
    bpy.context.view_layer.update()

    frames = sorted(set((scene.frame_start, REFERENCE_FRAME, scene.frame_end)))
    samples = []
    maximum_grip_distance = 0.0
    minimum_clearance = float("inf")
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        handle_world = iron.matrix_world @ anchor_local
        hand_world = bone_midpoint_world(rig, HAND_BONE)
        distance = (handle_world - hand_world).length
        iron_minimum, iron_maximum = bounds_world(iron)
        clearance = iron_minimum.z - board_top
        maximum_grip_distance = max(maximum_grip_distance, distance)
        minimum_clearance = min(minimum_clearance, clearance)
        if frame in frames:
            samples.append({
                "frame": frame,
                "hand_center_world": vec(hand_world),
                "handle_center_world": vec(handle_world),
                "grip_distance_m": round(distance, 6),
                "iron_bounds_world": {"minimum": vec(iron_minimum), "maximum": vec(iron_maximum)},
                "board_clearance_m": round(clearance, 6),
            })

    scene.frame_set(scene.frame_start)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report = {
        "status": "PASS" if minimum_clearance >= MINIMUM_BOARD_CLEARANCE_M - 1e-5 else "FAIL",
        "output": str(output),
        "iron_mesh": IRON_MESH_NAME,
        "iron_root": IRON_ROOT_NAME,
        "constraint": {
            "name": CONSTRAINT_NAME,
            "type": "COPY_LOCATION",
            "target": RIG_NAME,
            "subtarget": HAND_BONE,
            "fixed_world_rotation": True,
        },
        "scale_factor_xyz": vec(scale_factor),
        "grip_yaw_degrees": args.yaw_degrees,
        "palm_offset_m": vec(palm_offset),
        "reference_frame": REFERENCE_FRAME,
        "minimum_board_clearance_m": round(minimum_clearance, 6),
        "clearance_correction_m": round(clearance_correction, 6),
        "maximum_grip_distance_m": round(maximum_grip_distance, 6),
        "samples": samples,
    }
    report_path = Path(args.report) if args.report else output.with_suffix(".iron_attachment.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
