"""Measure minimum +Z rig shift clearing the right arm from the board."""

import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


FRAMES = range(150, 167)
ARM_GROUPS = {"upperarm01.R", "upperarm02.R", "lowerarm01.R", "lowerarm02.R", "wrist.R"}


def is_arm(name):
    return name in ARM_GROUPS or (name.endswith(".R") and name.startswith(("finger", "metacarpal")))


def bvh(obj, depsgraph, filtered=False):
    ev = obj.evaluated_get(depsgraph)
    mesh = ev.to_mesh()
    vertices = [ev.matrix_world @ v.co for v in mesh.vertices]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    if filtered:
        names = {g.index: g.name for g in obj.vertex_groups}
        polygons = [
            tuple(p.vertices) for p in mesh.polygons
            if sum(sum(a.weight for a in mesh.vertices[i].groups if is_arm(names.get(a.group, ""))) >= 0.25
                   for i in p.vertices) >= 2
        ]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=1e-7)


scene = bpy.context.scene
rig = bpy.data.objects["Human.rig"]
original = rig.location.copy()
scene.frame_set(1)
bpy.context.view_layer.update()
board = bvh(bpy.data.objects["White_desk"], bpy.context.evaluated_depsgraph_get())


def count(frame, dz):
    rig.location = original + Vector((0.0, 0.0, dz))
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    arm = bvh(bpy.data.objects["Human"], bpy.context.evaluated_depsgraph_get(), True)
    return len(arm.overlap(board))


rows = []
for frame in FRAMES:
    initial = count(frame, 0.0)
    if initial == 0:
        rows.append({"frame": frame, "initial_pairs": 0, "clearance_z_m": 0.0})
        continue
    low, high = 0.0, 0.08
    for _ in range(24):
        middle = (low + high) * 0.5
        if count(frame, middle) == 0:
            high = middle
        else:
            low = middle
    rows.append({"frame": frame, "initial_pairs": initial, "clearance_z_m": high})
rig.location = original
required = max(row["clearance_z_m"] for row in rows)
report = {"samples": rows, "required_z_m": required, "required_z_cm": required * 100.0}
output = Path("C:/Users/youss/exosquelette/data/scenarios/video1_v2/arm_table_vertical_clearance.json")
output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
