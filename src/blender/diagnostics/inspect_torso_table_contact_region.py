"""Report the spatial region of torso/garment triangles touching White_desk."""

import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_avatar_table_penetration import TORSO_GROUPS, world_bvh


def main():
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    board = world_bvh(bpy.data.objects["White_desk"], depsgraph)
    report = {}
    for name in ("Human", "Human.female_elegantsuit01"):
        obj = bpy.data.objects[name]
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        allowed = {group.index for group in obj.vertex_groups if group.name in TORSO_GROUPS}
        polygons = []
        for polygon in mesh.polygons:
            influenced = sum(
                sum(a.weight for a in mesh.vertices[index].groups if a.group in allowed) >= 0.25
                for index in polygon.vertices
            )
            if influenced >= 2:
                polygons.append(tuple(polygon.vertices))
        avatar = BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=1e-7)
        pairs = avatar.overlap(board)
        points = [vertices[index] for avatar_index, _ in pairs for index in polygons[avatar_index]]
        report[name] = {
            "pairs": len(pairs),
            "contact_vertex_bounds_m": {
                axis: [min(getattr(p, axis) for p in points), max(getattr(p, axis) for p in points)]
                for axis in ("x", "y", "z")
            } if points else None,
        }
        evaluated.to_mesh_clear()
    output = Path("C:/Users/youss/exosquelette/data/scenarios/scenario_principal/torso_table_contact_region.json")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


main()
