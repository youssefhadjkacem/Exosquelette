"""Find the smallest XY rig translation clearing torso/table intersection.

The search is constrained so the complete wrist trajectory remains inside the
world-space XY bounds of White_desk.
"""

from __future__ import annotations

import argparse
import json
import math
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
    parser.add_argument("--output", required=True)
    return parser.parse_args(values)


def evaluated_geometry(obj, depsgraph, groups=None):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
    if groups is not None:
        allowed = {group.index for group in obj.vertex_groups if group.name in groups}
        polygons = [
            tuple(polygon.vertices)
            for polygon in mesh.polygons
            if sum(
                sum(a.weight for a in mesh.vertices[index].groups if a.group in allowed) >= 0.25
                for index in polygon.vertices
            ) >= 2
        ]
    evaluated.to_mesh_clear()
    return vertices, polygons


def tree(vertices, polygons, dx=0.0, dy=0.0):
    moved = [Vector((v.x + dx, v.y + dy, v.z)) for v in vertices]
    return BVHTree.FromPolygons(moved, polygons, all_triangles=False, epsilon=1e-7)


def bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[i] for point in points) for i in range(3))),
        Vector(tuple(max(point[i] for point in points) for i in range(3))),
    )


def main():
    args = arguments()
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rig = bpy.data.objects["Human.rig"]
    board_min, board_max = bounds(bpy.data.objects["White_desk"])
    wrist = rig.pose.bones["wrist.R"]
    wrists = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        wrists.append(rig.matrix_world @ wrist.head)
    wrist_min = Vector(tuple(min(p[i] for p in wrists) for i in range(3)))
    wrist_max = Vector(tuple(max(p[i] for p in wrists) for i in range(3)))
    dx_range = (board_min.x - wrist_min.x, board_max.x - wrist_max.x)
    dy_range = (board_min.y - wrist_min.y, board_max.y - wrist_max.y)

    scene.frame_set(1)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    board_vertices, board_polygons = evaluated_geometry(bpy.data.objects["White_desk"], depsgraph)
    board_tree = tree(board_vertices, board_polygons)
    parts = [evaluated_geometry(bpy.data.objects[name], depsgraph, TORSO_GROUPS) for name in ("Human", "Human.female_elegantsuit01")]

    def collisions(dx, dy):
        return sum(len(tree(v, p, dx, dy).overlap(board_tree)) for v, p in parts)

    feasible = []
    samples = 121
    for index in range(samples):
        dx = dx_range[0] + (dx_range[1] - dx_range[0]) * index / (samples - 1)
        high = dy_range[1]
        if high < 0.0 or collisions(dx, high) != 0:
            continue
        low = max(0.0, dy_range[0])
        if collisions(dx, low) == 0:
            high = low
        else:
            for _ in range(22):
                middle = (low + high) * 0.5
                if collisions(dx, middle) == 0:
                    high = middle
                else:
                    low = middle
        feasible.append({"dx_m": dx, "dy_m": high, "distance_m": math.hypot(dx, high)})

    feasible.sort(key=lambda item: item["distance_m"])
    report = {
        "wrist_safe_adjustment_ranges_m": {"dx": list(dx_range), "dy": list(dy_range)},
        "searched_dx_samples": samples,
        "feasible_count": len(feasible),
        "best": feasible[0] if feasible else None,
        "best_candidates": feasible[:10],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
