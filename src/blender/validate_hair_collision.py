"""Check for mesh interpenetration between the hair object and clothing/body.

Builds BVH trees from the depsgraph-evaluated (world-space, modifiers
applied -- i.e. actually deformed by the armature) hair and clothes meshes
at each requested frame, and reports any overlapping triangle pairs via
mathutils.bvhtree.BVHTree.overlap. This is a real geometric intersection
test, not a bounding-box or distance proxy.

Run headless, e.g.:

    "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background \
        "C:\\Users\\youss\\mpfb-data\\femme.blend" --python \
        src/blender/validate_hair_collision.py -- \
        --hair Human.ponytail01 --clothes Human.female_casualsuit01 --body Human \
        --frames 1,181,541,1081 --output data/presentation_assets/avatar_makehuman/hair_collision_report.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils.bvhtree import BVHTree


def parse_args(argv: list[str]) -> dict:
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    args = {"hair": "Human.ponytail01", "clothes": "Human.female_casualsuit01", "body": "Human",
             "frames": [1, 181, 541, 1081], "output": None}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--hair":
            args["hair"] = argv[i + 1]
            i += 2
        elif token == "--clothes":
            args["clothes"] = argv[i + 1]
            i += 2
        elif token == "--body":
            args["body"] = argv[i + 1]
            i += 2
        elif token == "--frames":
            args["frames"] = [int(v) for v in argv[i + 1].split(",")]
            i += 2
        elif token == "--output":
            args["output"] = argv[i + 1]
            i += 2
        else:
            raise ValueError(f"Argument inconnu: {token}")
    return args


def bvh_from_evaluated(obj_name: str, depsgraph) -> BVHTree:
    obj = bpy.data.objects[obj_name]
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.transform(eval_obj.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    eval_obj.to_mesh_clear()
    return bvh


def main() -> None:
    args = parse_args(sys.argv)
    scene = bpy.context.scene

    for name in (args["hair"], args["clothes"], args["body"]):
        if name not in bpy.data.objects:
            raise ValueError(f"Objet introuvable: {name}")

    results = []
    for frame in args["frames"]:
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()

        hair_bvh = bvh_from_evaluated(args["hair"], depsgraph)
        clothes_bvh = bvh_from_evaluated(args["clothes"], depsgraph)
        body_bvh = bvh_from_evaluated(args["body"], depsgraph)

        overlap_clothes = hair_bvh.overlap(clothes_bvh)
        overlap_body = hair_bvh.overlap(body_bvh)

        entry = {
            "frame": frame,
            "hair_vs_clothes_overlapping_triangle_pairs": len(overlap_clothes),
            "hair_vs_body_overlapping_triangle_pairs": len(overlap_body),
        }
        results.append(entry)
        print(f"Frame {frame}: hair/clothes overlaps={len(overlap_clothes)}, hair/body overlaps={len(overlap_body)}")

    report = {
        "hair_object": args["hair"],
        "clothes_object": args["clothes"],
        "body_object": args["body"],
        "frames": results,
        "any_overlap": any(r["hair_vs_clothes_overlapping_triangle_pairs"] > 0 or r["hair_vs_body_overlapping_triangle_pairs"] > 0 for r in results),
    }

    if args["output"]:
        out_path = Path(args["output"]).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Report saved: {out_path}")

    print(f"any_overlap: {report['any_overlap']}")


if __name__ == "__main__":
    main()
