"""Search a collision-minimizing rigid avatar translation with wrist coverage."""

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
BOARD_MESHES = ("White_desk",)
RACK_MESHES = ("Cube.019", "Plane.009")


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(values)


def world_bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[i] for point in points) for i in range(3))),
        Vector(tuple(max(point[i] for point in points) for i in range(3))),
    )


def world_bvh(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
    tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=1e-6)
    evaluated.to_mesh_clear()
    return tree


def main() -> None:
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    wrist = rig.pose.bones["wrist.R"]
    board_min, board_max = world_bounds(bpy.data.objects["White_desk"])
    original_location = rig.location.copy()

    wrist_positions = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        wrist_positions.append(rig.matrix_world @ wrist.head)
    wrist_min = Vector(tuple(min(point[i] for point in wrist_positions) for i in range(3)))
    wrist_max = Vector(tuple(max(point[i] for point in wrist_positions) for i in range(3)))
    dx_limits = (board_min.x - wrist_min.x, board_max.x - wrist_max.x)
    dy_limits = (board_min.y - wrist_min.y, board_max.y - wrist_max.y)

    dx_values = [dx_limits[0] + i * (dx_limits[1] - dx_limits[0]) / 8 for i in range(9)]
    dy_values = [dy_limits[0] + i * (dy_limits[1] - dy_limits[0]) / 8 for i in range(9)]
    candidates = []
    for dx in dx_values:
        for dy in dy_values:
            rig.location = original_location + Vector((dx, dy, 0.0))
            bpy.context.view_layer.update()
            board_overlap = 0
            rack_overlap = 0
            for frame in FRAMES:
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                depsgraph = bpy.context.evaluated_depsgraph_get()
                trees = {
                    name: world_bvh(bpy.data.objects[name], depsgraph)
                    for name in AVATAR_MESHES + BOARD_MESHES + RACK_MESHES
                }
                for avatar in AVATAR_MESHES:
                    board_overlap += sum(len(trees[avatar].overlap(trees[name])) for name in BOARD_MESHES)
                    rack_overlap += sum(len(trees[avatar].overlap(trees[name])) for name in RACK_MESHES)
            candidates.append({
                "dx_m": dx,
                "dy_m": dy,
                "board_triangle_overlaps": board_overlap,
                "rack_triangle_overlaps": rack_overlap,
                "distance_from_centered_solution_m": ((dx + 0.098989472) ** 2 + (dy + 0.316179156) ** 2) ** 0.5,
            })

    candidates.sort(key=lambda row: (
        row["rack_triangle_overlaps"] > 0,
        row["board_triangle_overlaps"],
        row["distance_from_centered_solution_m"],
    ))
    report = {
        "coverage_translation_limits_m": {"dx": list(dx_limits), "dy": list(dy_limits)},
        "best_candidates": candidates[:15],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
