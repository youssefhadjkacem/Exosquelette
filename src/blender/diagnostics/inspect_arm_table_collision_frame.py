"""Inspect right-arm/table BVH contact region at one frame."""

import json
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree


FRAME = 159
ARM_GROUPS = {"upperarm01.R", "upperarm02.R", "lowerarm01.R", "lowerarm02.R", "wrist.R"}


def is_right_arm_group(name):
    return name in ARM_GROUPS or (name.endswith(".R") and name.startswith(("finger", "metacarpal")))


def geometry(obj, depsgraph, filtered=False):
    ev = obj.evaluated_get(depsgraph)
    mesh = ev.to_mesh()
    vertices = [ev.matrix_world @ v.co for v in mesh.vertices]
    polys = []
    if filtered:
        names = {g.index: g.name for g in obj.vertex_groups}
        for polygon in mesh.polygons:
            influenced = sum(
                sum(a.weight for a in mesh.vertices[i].groups
                    if is_right_arm_group(names.get(a.group, ""))) >= 0.25
                for i in polygon.vertices
            )
            if influenced >= 2:
                polys.append(tuple(polygon.vertices))
    else:
        polys = [tuple(p.vertices) for p in mesh.polygons]
    ev.to_mesh_clear()
    return vertices, polys


scene = bpy.context.scene
scene.frame_set(FRAME)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
av, ap = geometry(bpy.data.objects["Human"], depsgraph, True)
bv, bp = geometry(bpy.data.objects["White_desk"], depsgraph, False)
at = BVHTree.FromPolygons(av, ap, all_triangles=False, epsilon=1e-7)
bt = BVHTree.FromPolygons(bv, bp, all_triangles=False, epsilon=1e-7)
pairs = at.overlap(bt)
arm_points = [av[i] for ai, _ in pairs for i in ap[ai]]
board_points = [bv[i] for _, bi in pairs for i in bp[bi]]


def bounds(points):
    return {axis: [min(getattr(p, axis) for p in points), max(getattr(p, axis) for p in points)]
            for axis in ("x", "y", "z")}


rig = bpy.data.objects["Human.rig"]
report = {
    "frame": FRAME,
    "pairs": len(pairs),
    "arm_contact_bounds_m": bounds(arm_points),
    "board_contact_bounds_m": bounds(board_points),
    "joints": {
        name: list(rig.matrix_world @ rig.pose.bones[name].head)
        for name in ("upperarm01.R", "lowerarm01.R", "wrist.R", "metacarpal3.R")
    },
}
output = Path("C:/Users/youss/exosquelette/data/scenarios/pipeline_principal/arm_table_collision_frame159.json")
output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
