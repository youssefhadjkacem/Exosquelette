"""Fix casualsuit01/table intersection reintroduced by the wardrobe swap.

The elegantsuit01 garment was previously corrected for table clearance via a
reversible shape key (see repair_suit_table_intersection.py /
repair_table_clearance_mixed.py). Swapping to Human.female_casualsuit01 for
the final presentation dropped that fix, since the new mesh has no shape
keys at all. This reapplies the identical reversible correction algorithm to
the new garment; the rig and animation are left untouched (no further rig
shift needed, since the earlier +15.06cm/+3.37cm rig translation is already
baked into Human.rig.location).
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
CHECK_FRAMES = (1, 181, 541, 1081)


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--full-scan", action="store_true")
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


def overlap_counts(scene, human, suit, board):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    board_tree = world_bvh(board, depsgraph)
    return {
        "Human": len(world_bvh(human, depsgraph, TORSO_GROUPS).overlap(board_tree)),
        "Human.female_casualsuit01": len(world_bvh(suit, depsgraph, TORSO_GROUPS).overlap(board_tree)),
    }


def main():
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    human = bpy.data.objects["Human"]
    suit = bpy.data.objects["Human.female_casualsuit01"]
    board = bpy.data.objects["White_desk"]

    scene.frame_set(1)
    before_samples = []
    for frame in CHECK_FRAMES:
        scene.frame_set(frame)
        before_samples.append({"frame": frame, "pairs": overlap_counts(scene, human, suit, board)})

    board_y_max = max((board.matrix_world @ Vector(c)).y for c in board.bound_box)
    target_y = board_y_max + 0.025

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
    for frame in CHECK_FRAMES:
        scene.frame_set(frame)
        final_samples.append({"frame": frame, "pairs": overlap_counts(scene, human, suit, board)})

    wrist = rig.pose.bones["wrist.R"]
    board_min = Vector(tuple(min((board.matrix_world @ Vector(c))[i] for c in board.bound_box) for i in range(3)))
    board_max = Vector(tuple(max((board.matrix_world @ Vector(c))[i] for c in board.bound_box) for i in range(3)))
    wrist_checks = []
    for frame in CHECK_FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        position = rig.matrix_world @ wrist.head
        inside = (board_min.x <= position.x <= board_max.x) and (board_min.y <= position.y <= board_max.y)
        wrist_checks.append({"frame": frame, "x": position.x, "y": position.y, "inside_board_xy": inside})

    full_scan = None
    if args.full_scan:
        outside_count = 0
        max_pairs_seen = 0
        max_pairs_frame = None
        for frame in range(scene.frame_start, scene.frame_end + 1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            position = rig.matrix_world @ wrist.head
            inside = (board_min.x <= position.x <= board_max.x) and (board_min.y <= position.y <= board_max.y)
            if not inside:
                outside_count += 1
            pairs = overlap_counts(scene, human, suit, board)
            total_pairs = pairs["Human"] + pairs["Human.female_casualsuit01"]
            if total_pairs > max_pairs_seen:
                max_pairs_seen = total_pairs
                max_pairs_frame = frame
        total_frames = scene.frame_end - scene.frame_start + 1
        full_scan = {
            "total_frames": total_frames,
            "wrist_outside_board_count": outside_count,
            "wrist_outside_board_percentage": 100.0 * outside_count / total_frames,
            "max_collision_pairs_seen": max_pairs_seen,
            "max_collision_pairs_frame": max_pairs_frame,
        }

    scene.frame_set(1)
    suit["presentation_table_clearance_note"] = (
        "Reversible garment shape key correcting the table intersection reintroduced "
        "by the casualsuit01 wardrobe swap; rig/animation unchanged."
    )

    report = {
        "method": "reversible garment shape key on Human.female_casualsuit01; rig and animation unchanged",
        "shape_key": SHAPE_NAME,
        "adjusted_vertex_count": len(adjusted),
        "maximum_single_iteration_shift_cm": maximum_shift * 100.0,
        "clearance_target_y_m": target_y,
        "before_samples": before_samples,
        "final_samples": final_samples,
        "wrist_checks": wrist_checks,
        "full_scan": full_scan,
        "status": "PASS" if all(
            sum(s["pairs"].values()) == 0 for s in final_samples
        ) and all(w["inside_board_xy"] for w in wrist_checks) and (
            full_scan is None or (full_scan["wrist_outside_board_count"] == 0 and full_scan["max_collision_pairs_seen"] == 0)
        ) else "FAIL",
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
