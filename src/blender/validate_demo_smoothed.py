"""Full 1081-frame validation for the presentation-only smoothed demo copy.

Checks the same three criteria used throughout this project's Blender work:
wrist-on-board coverage, torso/garment-table collision, and iron-grip
stability -- run here on femme_demo_smoothed.blend after the Butterworth
smoothing pass, to confirm the cosmetic change did not reintroduce any of
the previously-fixed defects.
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


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
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


def main():
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    human = bpy.data.objects["Human"]
    suit = bpy.data.objects["Human.female_casualsuit01"]
    board = bpy.data.objects["White_desk"]
    iron = bpy.data.objects["Iron"]
    wrist = rig.pose.bones["wrist.R"]
    hand = rig.pose.bones["metacarpal3.R"]

    board_min = Vector(tuple(min((board.matrix_world @ Vector(c))[i] for c in board.bound_box) for i in range(3)))
    board_max = Vector(tuple(max((board.matrix_world @ Vector(c))[i] for c in board.bound_box) for i in range(3)))

    wrist_outside = 0
    max_pairs = 0
    max_pairs_frame = None
    iron_distances = []
    total_frames = scene.frame_end - scene.frame_start + 1

    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()

        wrist_pos = rig.matrix_world @ wrist.head
        inside = (board_min.x <= wrist_pos.x <= board_max.x) and (board_min.y <= wrist_pos.y <= board_max.y)
        if not inside:
            wrist_outside += 1

        depsgraph = bpy.context.evaluated_depsgraph_get()
        board_tree = world_bvh(board, depsgraph)
        pairs = (
            len(world_bvh(human, depsgraph, TORSO_GROUPS).overlap(board_tree))
            + len(world_bvh(suit, depsgraph, TORSO_GROUPS).overlap(board_tree))
        )
        if pairs > max_pairs:
            max_pairs = pairs
            max_pairs_frame = frame

        hand_pos = rig.matrix_world @ hand.head
        iron_distances.append((hand_pos - iron.matrix_world.translation).length)

    report = {
        "total_frames": total_frames,
        "wrist_outside_board_count": wrist_outside,
        "wrist_outside_board_percentage": 100.0 * wrist_outside / total_frames,
        "max_collision_pairs_seen": max_pairs,
        "max_collision_pairs_frame": max_pairs_frame,
        "iron_hand_distance_m": {
            "min": min(iron_distances),
            "max": max(iron_distances),
            "mean": sum(iron_distances) / len(iron_distances),
            "range": max(iron_distances) - min(iron_distances),
        },
        "status": "PASS" if wrist_outside == 0 and max_pairs == 0 else "FAIL",
    }

    scene.frame_set(1)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
