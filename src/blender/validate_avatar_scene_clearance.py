"""Validate avatar intersections and foot height after a rigid scene recenter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree


AVATAR_MESHES = ("Human", "Human.female_elegantsuit01")
BOARD_MESHES = ("White_desk",)
RACK_MESHES = ("Cube.019", "Plane.009")
CHECK_FRAMES = (1, 181, 541, 1081)


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(values)


def world_bvh(obj: bpy.types.Object, depsgraph) -> BVHTree:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
    tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=1e-6)
    evaluated.to_mesh_clear()
    return tree


def minimum_world_z(obj: bpy.types.Object, depsgraph) -> float:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    value = min((evaluated.matrix_world @ vertex.co).z for vertex in mesh.vertices)
    evaluated.to_mesh_clear()
    return value


def main() -> None:
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    samples = []
    total_board_overlaps = 0
    total_rack_overlaps = 0

    for frame in CHECK_FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        trees = {
            name: world_bvh(bpy.data.objects[name], depsgraph)
            for name in AVATAR_MESHES + BOARD_MESHES + RACK_MESHES
        }
        board_overlaps = {}
        rack_overlaps = {}
        for avatar_name in AVATAR_MESHES:
            for obstacle_name in BOARD_MESHES:
                count = len(trees[avatar_name].overlap(trees[obstacle_name]))
                board_overlaps[f"{avatar_name}/{obstacle_name}"] = count
                total_board_overlaps += count
            for obstacle_name in RACK_MESHES:
                count = len(trees[avatar_name].overlap(trees[obstacle_name]))
                rack_overlaps[f"{avatar_name}/{obstacle_name}"] = count
                total_rack_overlaps += count

        foot_positions = {}
        for name in ("foot.L", "toe1-1.L", "foot.R", "toe1-1.R"):
            bone = rig.pose.bones[name]
            foot_positions[name] = {
                "head_z_m": float((rig.matrix_world @ bone.head).z),
                "tail_z_m": float((rig.matrix_world @ bone.tail).z),
            }
        samples.append({
            "frame": frame,
            "avatar_minimum_z_m": minimum_world_z(bpy.data.objects["Human"], depsgraph),
            "board_triangle_overlaps": board_overlaps,
            "rack_triangle_overlaps": rack_overlaps,
            "foot_bones": foot_positions,
        })

    minimum_z_values = [sample["avatar_minimum_z_m"] for sample in samples]
    report = {
        "status": "PASS" if total_board_overlaps == 0 and total_rack_overlaps == 0 else "FAIL",
        "frames_checked": list(CHECK_FRAMES),
        "total_avatar_board_triangle_overlaps": total_board_overlaps,
        "total_avatar_rack_triangle_overlaps": total_rack_overlaps,
        "avatar_minimum_z_range_m": [min(minimum_z_values), max(minimum_z_values)],
        "rig_translation_z_m": float(rig.location.z),
        "samples": samples,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
