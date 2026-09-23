"""Measure directional avatar/table penetration and wrist-safe clearance.

The reported penetration is the minimum rigid translation along world +Y
required to make the evaluated avatar and White_desk meshes disjoint.  This
direction corresponds to moving the operator backward from the work surface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


FRAMES = (1, 181, 541, 1081)
AVATAR_MESHES = ("Human", "Human.female_elegantsuit01")
TORSO_GROUPS = {
    "pelvis.L", "pelvis.R",
    "spine01", "spine02", "spine03", "spine04", "spine05",
    "breast.L", "breast.R",
}


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(values)


def world_bvh(obj: bpy.types.Object, depsgraph, group_names: set[str] | None = None) -> BVHTree:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
    if group_names is not None:
        allowed = {group.index for group in obj.vertex_groups if group.name in group_names}
        selected = []
        for polygon in mesh.polygons:
            influenced = 0
            for vertex_index in polygon.vertices:
                weight = sum(
                    assignment.weight
                    for assignment in mesh.vertices[vertex_index].groups
                    if assignment.group in allowed
                )
                influenced += weight >= 0.25
            if influenced >= 2:
                selected.append(tuple(polygon.vertices))
        polygons = selected
    tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=1e-7)
    evaluated.to_mesh_clear()
    return tree


def overlap_counts(scene: bpy.types.Scene) -> dict[str, int]:
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    board = world_bvh(bpy.data.objects["White_desk"], depsgraph)
    return {
        name: len(world_bvh(bpy.data.objects[name], depsgraph, TORSO_GROUPS).overlap(board))
        for name in AVATAR_MESHES
    }


def wrist_y_limits(scene: bpy.types.Scene, rig: bpy.types.Object) -> tuple[float, float]:
    wrist = rig.pose.bones["wrist.R"]
    values = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        values.append(float((rig.matrix_world @ wrist.head).y))
    return min(values), max(values)


def clearance_at_frame(scene: bpy.types.Scene, rig: bpy.types.Object, frame: int) -> dict:
    scene.frame_set(frame)
    original = rig.location.copy()
    initial = overlap_counts(scene)
    if sum(initial.values()) == 0:
        return {"frame": frame, "initial_triangle_pairs": initial, "clearance_y_m": 0.0}

    low, high = 0.0, 0.01
    while high <= 1.0:
        rig.location = original + Vector((0.0, high, 0.0))
        if sum(overlap_counts(scene).values()) == 0:
            break
        high *= 2.0
    if high > 1.0:
        rig.location = original
        return {"frame": frame, "initial_triangle_pairs": initial, "clearance_y_m": None}

    for _ in range(24):
        middle = (low + high) * 0.5
        rig.location = original + Vector((0.0, middle, 0.0))
        if sum(overlap_counts(scene).values()) == 0:
            high = middle
        else:
            low = middle
    rig.location = original
    bpy.context.view_layer.update()
    return {
        "frame": frame,
        "initial_triangle_pairs": initial,
        "clearance_y_m": high,
        "clearance_y_cm": high * 100.0,
    }


def main() -> None:
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    original_frame = scene.frame_current
    original_location = rig.location.copy()
    wrist_min_y, wrist_max_y = wrist_y_limits(scene, rig)
    board = bpy.data.objects["White_desk"]
    board_y_max = max((board.matrix_world @ Vector(corner)).y for corner in board.bound_box)
    maximum_backward_translation = board_y_max - wrist_max_y
    samples = [clearance_at_frame(scene, rig, frame) for frame in FRAMES]
    required = max(sample["clearance_y_m"] or 0.0 for sample in samples)

    rig.location = original_location + Vector((0.0, maximum_backward_translation, 0.0))
    at_coverage_limit = []
    for frame in FRAMES:
        scene.frame_set(frame)
        at_coverage_limit.append({"frame": frame, "triangle_pairs": overlap_counts(scene)})
    rig.location = original_location
    scene.frame_set(original_frame)
    bpy.context.view_layer.update()

    report = {
        "definition": "minimum rigid +Y translation until torso/pelvis BVH mesh intersection is zero",
        "torso_vertex_groups": sorted(TORSO_GROUPS),
        "frames": samples,
        "maximum_required_clearance_y_m": required,
        "maximum_required_clearance_y_cm": required * 100.0,
        "wrist_y_range_m": [wrist_min_y, wrist_max_y],
        "board_y_max_m": board_y_max,
        "maximum_backward_translation_preserving_zero_percent_m": maximum_backward_translation,
        "intersection_at_wrist_coverage_limit": at_coverage_limit,
        "simultaneously_feasible": required <= maximum_backward_translation,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
