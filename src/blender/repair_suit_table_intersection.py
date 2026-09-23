"""Create a reversible garment correction that clears the table edge.

Only the presentation suit shape is adjusted.  The rig transform, animation,
bones, wrist trajectory, and iron constraint are left untouched.
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


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(values)


def world_bvh(obj, depsgraph, groups=None):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
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


def overlap_count(suit, board):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return len(world_bvh(suit, depsgraph, TORSO_GROUPS).overlap(world_bvh(board, depsgraph)))


def main():
    args = arguments()
    scene = bpy.context.scene
    scene.frame_set(1)
    suit = bpy.data.objects["Human.female_elegantsuit01"]
    board = bpy.data.objects["White_desk"]
    rig = bpy.data.objects["Human.rig"]
    rig_before = rig.location.copy()
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
    # Iterate because the armature skinning slightly changes the requested
    # world-space displacement when mapped back to the shape key.
    for _ in range(8):
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = suit.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        for vertex in mesh.vertices:
            torso_weight = sum(a.weight for a in suit.data.vertices[vertex.index].groups if a.group in allowed)
            world = evaluated.matrix_world @ vertex.co
            near_torso_core = (
                abs(world.x - rig.matrix_world.translation.x) <= 0.20
                and 0.50 <= world.z <= 1.20
            )
            if ((torso_weight < 0.10 and not near_torso_core)
                    or not (0.50 <= world.z <= 1.30)
                    or world.y >= target_y):
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

    samples = []
    for frame in (1, 181, 541, 1081):
        scene.frame_set(frame)
        samples.append({"frame": frame, "torso_suit_table_triangle_pairs": overlap_count(suit, board)})

    report = {
        "status": "PASS" if all(s["torso_suit_table_triangle_pairs"] == 0 for s in samples) else "FAIL",
        "method": "reversible garment shape key; rig and animation unchanged",
        "shape_key": SHAPE_NAME,
        "adjusted_vertex_count": len(adjusted),
        "maximum_single_iteration_shift_cm": maximum_shift * 100.0,
        "clearance_target_y_m": target_y,
        "rig_location_unchanged": all(abs(rig.location[i] - rig_before[i]) < 1e-9 for i in range(3)),
        "samples": samples,
    }
    scene.frame_set(1)
    suit["presentation_table_clearance_note"] = (
        "Local reversible garment correction; no source kinematics changed."
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
