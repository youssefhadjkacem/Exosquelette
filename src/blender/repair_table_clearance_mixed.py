"""Rig backward translation + residual garment correction for table clearance.

Applies a rigid +Y translation to Human.rig (moving the operator backward
from the table), then runs the exact same reversible garment shape-key
correction as repair_suit_table_intersection.py on whatever intersection
remains after that translation. Splitting the fix this way keeps the garment
deformation small: most of the original 23.30cm penetration is resolved by
the rig shift (which the wrist-on-board constraint limits to 15.56cm max),
and only the residual is corrected via the shape key.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TORSO_GROUPS = {
    "pelvis.L", "pelvis.R", "spine01", "spine02", "spine03", "spine04",
    "spine05", "breast.L", "breast.R",
}
SHAPE_NAME = "Presentation_Table_Clearance"
FRAMES = (1, 181, 541, 1081)


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--rig-shift-m", type=float, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(values)


def world_bvh(obj, depsgraph, groups=None):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ v.co for v in mesh.vertices]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    if groups is not None:
        allowed = {g.index for g in obj.vertex_groups if g.name in groups}
        polygons = [
            tuple(p.vertices) for p in mesh.polygons
            if sum(
                sum(a.weight for a in mesh.vertices[i].groups if a.group in allowed) >= 0.25
                for i in p.vertices
            ) >= 2
        ]
    tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=1e-7)
    evaluated.to_mesh_clear()
    return tree


def overlap_counts(scene, board):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    board_tree = world_bvh(board, depsgraph)
    return {
        name: len(world_bvh(bpy.data.objects[name], depsgraph, TORSO_GROUPS).overlap(board_tree))
        for name in ("Human", "Human.female_elegantsuit01")
    }


def main():
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    suit = bpy.data.objects["Human.female_elegantsuit01"]
    board = bpy.data.objects["White_desk"]

    scene.frame_set(1)
    before_samples = []
    for frame in FRAMES:
        scene.frame_set(frame)
        before_samples.append({"frame": frame, "pairs": overlap_counts(scene, board)})

    rig_before = rig.location.copy()
    rig.location = rig_before + Vector((0.0, args.rig_shift_m, 0.0))
    bpy.context.view_layer.update()

    scene.frame_set(1)
    after_shift_samples = []
    for frame in FRAMES:
        scene.frame_set(frame)
        after_shift_samples.append({"frame": frame, "pairs": overlap_counts(scene, board)})

    # --- identical garment-correction algorithm to repair_suit_table_intersection.py ---
    board_y_max = max((board.matrix_world @ Vector(c)).y for c in board.bound_box)
    target_y = board_y_max + 0.025  # 25 mm safety gap before subdivision.

    if suit.data.shape_keys is None:
        suit.shape_key_add(name="Basis")
    if SHAPE_NAME in suit.data.shape_keys.key_blocks:
        correction = suit.data.shape_keys.key_blocks[SHAPE_NAME]
    else:
        correction = suit.shape_key_add(name=SHAPE_NAME)
    correction.value = 1.0

    subdivision_states = []
    for modifier in suit.modifiers:
        if modifier.type == "SUBSURF":
            subdivision_states.append((modifier, modifier.show_viewport, modifier.show_render))
            modifier.show_viewport = False
            modifier.show_render = False

    allowed = {g.index for g in suit.vertex_groups if g.name in TORSO_GROUPS}
    adjusted = set()
    maximum_shift = 0.0
    scene.frame_set(1)
    for _ in range(8):
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = suit.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        for vertex in mesh.vertices:
            torso_weight = sum(a.weight for a in suit.data.vertices[vertex.index].groups if a.group in allowed)
            world = evaluated.matrix_world @ vertex.co
            if torso_weight < 0.10 or not (0.60 <= world.z <= 1.30) or world.y >= target_y:
                continue
            delta_world = Vector((0.0, target_y - world.y, 0.0))
            delta_local = suit.matrix_world.to_3x3().inverted() @ delta_world
            correction.data[vertex.index].co += delta_local
            adjusted.add(vertex.index)
            maximum_shift = max(maximum_shift, delta_world.y)
        evaluated.to_mesh_clear()

    for modifier, viewport, render in subdivision_states:
        modifier.show_viewport = viewport
        modifier.show_render = render
    bpy.context.view_layer.update()

    final_samples = []
    for frame in FRAMES:
        scene.frame_set(frame)
        final_samples.append({"frame": frame, "pairs": overlap_counts(scene, board)})

    # wrist coverage check at the same 4 frames (full-trajectory check is a separate script)
    wrist = rig.pose.bones["wrist.R"]
    board_min = Vector(tuple(min((board.matrix_world @ Vector(c))[i] for c in board.bound_box) for i in range(3)))
    board_max = Vector(tuple(max((board.matrix_world @ Vector(c))[i] for c in board.bound_box) for i in range(3)))
    wrist_checks = []
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        position = rig.matrix_world @ wrist.head
        inside = (board_min.x <= position.x <= board_max.x) and (board_min.y <= position.y <= board_max.y)
        wrist_checks.append({"frame": frame, "x": position.x, "y": position.y, "inside_board_xy": inside})

    scene.frame_set(1)
    suit["presentation_table_clearance_note"] = (
        f"Rig shifted +Y {args.rig_shift_m * 100:.2f}cm; residual garment correction on top."
    )

    report = {
        "method": "rig backward translation + residual reversible garment shape key",
        "rig_shift_y_m": args.rig_shift_m,
        "rig_shift_y_cm": args.rig_shift_m * 100.0,
        "rig_location_before": list(rig_before),
        "rig_location_after": list(rig.location),
        "before_shift_pairs": before_samples,
        "after_shift_pairs": after_shift_samples,
        "final_pairs_after_garment_fix": final_samples,
        "garment_correction": {
            "shape_key": SHAPE_NAME,
            "adjusted_vertex_count": len(adjusted),
            "maximum_single_iteration_shift_cm": maximum_shift * 100.0,
            "clearance_target_y_m": target_y,
        },
        "wrist_checks": wrist_checks,
        "status": "PASS" if all(
            sum(s["pairs"].values()) == 0 for s in final_samples
        ) and all(w["inside_board_xy"] for w in wrist_checks) else "FAIL",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
