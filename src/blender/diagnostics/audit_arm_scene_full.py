"""Audit arm proportions, board intersections, clothing, and iron on all frames."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


RIGHT_ARM_GROUPS = {
    "upperarm01.R", "upperarm02.R", "lowerarm01.R", "lowerarm02.R", "wrist.R",
}


def is_right_arm_group(name):
    return name in RIGHT_ARM_GROUPS or (
        name.endswith(".R") and name.startswith(("finger", "metacarpal"))
    )


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(values)


def geometry(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    group_names = {group.index: group.name for group in obj.vertex_groups}
    arm_polygons = []
    for polygon in mesh.polygons:
        influenced = 0
        for vertex_index in polygon.vertices:
            weight = sum(
                assignment.weight for assignment in mesh.vertices[vertex_index].groups
                if is_right_arm_group(group_names.get(assignment.group, ""))
            )
            influenced += weight >= 0.25
        if influenced >= 2:
            arm_polygons.append(tuple(polygon.vertices))
    evaluated.to_mesh_clear()
    return vertices, polygons, arm_polygons


def tree(vertices, polygons):
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=1e-7)


def handle_center(iron):
    points = [iron.matrix_world @ vertex.co for vertex in iron.data.vertices]
    minimum_z = min(point.z for point in points)
    maximum_z = max(point.z for point in points)
    selected = [p for p in points if p.z >= minimum_z + 0.75 * (maximum_z - minimum_z)]
    return sum(selected, Vector()) / len(selected)


def main():
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    body = bpy.data.objects["Human"]
    suit = bpy.data.objects["Human.female_elegantsuit01"]
    board = bpy.data.objects["White_desk"]
    iron = bpy.data.objects["Iron"]
    scene.frame_set(1)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    board_vertices, board_polygons, _ = geometry(board, depsgraph)
    board_tree = tree(board_vertices, board_polygons)

    samples = []
    maxima = {
        "body_board": 0, "suit_board": 0, "right_arm_body_board": 0,
        "right_arm_suit_board": 0, "right_arm_body_suit": 0,
    }
    frames_with = {key: 0 for key in maxima}
    upper_values = []
    lower_values = []
    grip_values = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        bv, bp, bap = geometry(body, depsgraph)
        sv, sp, sap = geometry(suit, depsgraph)
        body_tree = tree(bv, bp)
        suit_tree = tree(sv, sp)
        body_arm_tree = tree(bv, bap)
        suit_arm_tree = tree(sv, sap)
        counts = {
            "body_board": len(body_tree.overlap(board_tree)),
            "suit_board": len(suit_tree.overlap(board_tree)),
            "right_arm_body_board": len(body_arm_tree.overlap(board_tree)),
            "right_arm_suit_board": len(suit_arm_tree.overlap(board_tree)),
            "right_arm_body_suit": len(body_arm_tree.overlap(suit_arm_tree)),
        }
        for key, value in counts.items():
            maxima[key] = max(maxima[key], value)
            frames_with[key] += value > 0
        upper = float(((rig.matrix_world @ rig.pose.bones["upperarm01.R"].head) -
                       (rig.matrix_world @ rig.pose.bones["lowerarm01.R"].head)).length)
        lower = float(((rig.matrix_world @ rig.pose.bones["lowerarm01.R"].head) -
                       (rig.matrix_world @ rig.pose.bones["wrist.R"].head)).length)
        hand = rig.matrix_world @ ((rig.pose.bones["metacarpal3.R"].head +
                                    rig.pose.bones["metacarpal3.R"].tail) * 0.5)
        grip = float((hand - handle_center(iron)).length)
        upper_values.append(upper)
        lower_values.append(lower)
        grip_values.append(grip)
        if frame in (1, 181, 541, 1081):
            samples.append({"frame": frame, **counts, "upper_m": upper, "lower_m": lower, "grip_m": grip})

    constraint = bpy.data.objects["Old Iron"].constraints.get("Iron follows right hand")
    report = {
        "blend_file": bpy.data.filepath,
        "frames_checked": scene.frame_end - scene.frame_start + 1,
        "segment_ranges_m": {
            "upper": [min(upper_values), max(upper_values)],
            "lower": [min(lower_values), max(lower_values)],
        },
        "maximum_triangle_pairs_per_frame": maxima,
        "frames_with_triangle_pairs": frames_with,
        "grip_distance_range_m": [min(grip_values), max(grip_values)],
        "iron_constraint": {
            "exists": constraint is not None,
            "target": constraint.target.name if constraint and constraint.target else None,
            "subtarget": constraint.subtarget if constraint else None,
        },
        "samples": samples,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
