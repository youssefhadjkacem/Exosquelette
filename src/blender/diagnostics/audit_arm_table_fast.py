"""Fast per-frame audit of right-arm/body intersections with White_desk."""

import csv
import json
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree


OUTPUT = Path("C:/Users/youss/exosquelette/data/scenarios/pipeline_principal/arm_table_fast_audit.json")
CSV = OUTPUT.with_suffix(".csv")
ARM_GROUPS = {"upperarm01.R", "upperarm02.R", "lowerarm01.R", "lowerarm02.R", "wrist.R"}


def is_right_arm_group(name):
    return name in ARM_GROUPS or (name.endswith(".R") and name.startswith(("finger", "metacarpal")))


def evaluated(obj, depsgraph, filtered=False):
    ev = obj.evaluated_get(depsgraph)
    mesh = ev.to_mesh()
    vertices = [ev.matrix_world @ v.co for v in mesh.vertices]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    if filtered:
        names = {g.index: g.name for g in obj.vertex_groups}
        polygons = [
            tuple(p.vertices) for p in mesh.polygons
            if sum(
                sum(a.weight for a in mesh.vertices[i].groups
                    if is_right_arm_group(names.get(a.group, ""))) >= 0.25
                for i in p.vertices
            ) >= 2
        ]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=1e-7)


scene = bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()
board = evaluated(bpy.data.objects["White_desk"], bpy.context.evaluated_depsgraph_get())
rows = []
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    arm = evaluated(bpy.data.objects["Human"], bpy.context.evaluated_depsgraph_get(), True)
    rows.append({"frame": frame, "triangle_pairs": len(arm.overlap(board))})
maximum = max(row["triangle_pairs"] for row in rows)
contact_frames = [row["frame"] for row in rows if row["triangle_pairs"] > 0]
report = {
    "maximum_triangle_pairs": maximum,
    "maximum_frames": [row["frame"] for row in rows if row["triangle_pairs"] == maximum],
    "contact_frames": contact_frames,
    "contact_frame_count": len(contact_frames),
}
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
with CSV.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=("frame", "triangle_pairs"))
    writer.writeheader()
    writer.writerows(rows)
print(json.dumps(report, indent=2))
