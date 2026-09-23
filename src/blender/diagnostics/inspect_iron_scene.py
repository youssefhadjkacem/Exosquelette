"""Inspect Iron attachment, candidate hand bones, and key-frame transforms."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


def parse_output() -> Path | None:
    if "--" not in sys.argv:
        return None
    args = sys.argv[sys.argv.index("--") + 1 :]
    if "--output" not in args:
        return None
    return Path(args[args.index("--output") + 1])


def vector(value) -> list[float]:
    return [round(float(component), 6) for component in value]


def object_constraints(obj) -> list[dict]:
    return [
        {
            "name": constraint.name,
            "type": constraint.type,
            "target": constraint.target.name if getattr(constraint, "target", None) else None,
            "subtarget": getattr(constraint, "subtarget", None),
        }
        for constraint in obj.constraints
    ]


def world_bounds(obj) -> dict | None:
    if not getattr(obj, "bound_box", None):
        return None
    corners = [obj.matrix_world @ type(obj.matrix_world.translation)(corner) for corner in obj.bound_box]
    return {
        "minimum": vector([min(point[i] for point in corners) for i in range(3)]),
        "maximum": vector([max(point[i] for point in corners) for i in range(3)]),
    }


def mesh_components(obj) -> list[dict]:
    if obj.type != "MESH":
        return []
    adjacency = [set() for _ in obj.data.vertices]
    for edge in obj.data.edges:
        first, second = edge.vertices
        adjacency[first].add(second)
        adjacency[second].add(first)
    unseen = set(range(len(adjacency)))
    components = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        indices = [seed]
        while stack:
            current = stack.pop()
            neighbours = adjacency[current] & unseen
            unseen.difference_update(neighbours)
            stack.extend(neighbours)
            indices.extend(neighbours)
        points = [obj.matrix_world @ obj.data.vertices[index].co for index in indices]
        components.append({
            "vertices": len(indices),
            "minimum": vector([min(point[i] for point in points) for i in range(3)]),
            "maximum": vector([max(point[i] for point in points) for i in range(3)]),
            "center": vector([sum(point[i] for point in points) / len(points) for i in range(3)]),
        })
    return sorted(components, key=lambda item: item["vertices"], reverse=True)


def elevated_vertex_regions(obj) -> list[dict]:
    if obj.type != "MESH":
        return []
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    minimum_z = min(point.z for point in points)
    maximum_z = max(point.z for point in points)
    regions = []
    for fraction in (0.55, 0.65, 0.75, 0.85):
        threshold = minimum_z + fraction * (maximum_z - minimum_z)
        selected = [point for point in points if point.z >= threshold]
        regions.append({
            "height_fraction": fraction,
            "vertices": len(selected),
            "minimum": vector([min(point[i] for point in selected) for i in range(3)]),
            "maximum": vector([max(point[i] for point in selected) for i in range(3)]),
            "center": vector([sum(point[i] for point in selected) / len(selected) for i in range(3)]),
        })
    return regions


def main() -> None:
    scene = bpy.context.scene
    iron = next((obj for obj in bpy.data.objects if obj.name.lower() == "iron"), None)
    if iron is None:
        raise ValueError("Objet 'Iron' introuvable")

    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    candidate_tokens = ("wrist", "hand", "palm", "lowerarm", "forearm", "finger", "metacarpal")
    rigs = []
    for rig in armatures:
        candidates = [
            bone.name for bone in rig.pose.bones
            if any(token in bone.name.lower() for token in candidate_tokens)
        ]
        rigs.append({"name": rig.name, "candidate_bones": candidates})

    related_objects = [
        obj.name for obj in bpy.data.objects
        if any(token in obj.name.lower() for token in ("board", "planche", "table", "iron"))
    ]
    constraints = object_constraints(iron)
    frame_start, frame_end = scene.frame_start, scene.frame_end
    frames = sorted(set((frame_start, (frame_start + frame_end) // 2, frame_end)))
    samples = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        sample = {
            "frame": frame,
            "iron_location_world": vector(iron.matrix_world.translation),
            "iron_rotation_world": vector(iron.matrix_world.to_euler("XYZ")),
        }
        for rig in armatures:
            for bone_name in rigs[armatures.index(rig)]["candidate_bones"]:
                bone = rig.pose.bones[bone_name]
                sample[f"{rig.name}/{bone_name}"] = {
                    "head_world": vector(rig.matrix_world @ bone.head),
                    "tail_world": vector(rig.matrix_world @ bone.tail),
                }
        samples.append(sample)

    report = {
        "blend_file": bpy.data.filepath,
        "scene": {
            "frame_start": frame_start,
            "frame_end": frame_end,
            "fps": scene.render.fps,
            "camera": scene.camera.name if scene.camera else None,
        },
        "iron": {
            "name": iron.name,
            "type": iron.type,
            "parent": iron.parent.name if iron.parent else None,
            "parent_type": iron.parent_type,
            "parent_bone": iron.parent_bone,
            "constraints": constraints,
            "location_local": vector(iron.location),
            "rotation_local": vector(iron.rotation_euler),
            "dimensions": vector(iron.dimensions),
            "animation_data": bool(iron.animation_data),
            "mesh_components": mesh_components(iron),
            "elevated_vertex_regions": elevated_vertex_regions(iron),
        },
        "armatures": rigs,
        "wrist_descendants": {
            rig.name: [
                bone.name for bone in rig.pose.bones
                if bone.parent and (bone.parent.name == "wrist.R" or bone.parent.parent and bone.parent.parent.name == "wrist.R")
            ]
            for rig in armatures
        },
        "related_objects": related_objects,
        "objects": [
            {
                "name": obj.name,
                "type": obj.type,
                "parent": obj.parent.name if obj.parent else None,
                "parent_type": obj.parent_type,
                "parent_bone": obj.parent_bone,
                "children": [child.name for child in obj.children],
                "constraints": object_constraints(obj),
                "location_world": vector(obj.matrix_world.translation),
                "bounds_world": world_bounds(obj),
            }
            for obj in bpy.data.objects
        ],
        "samples": samples,
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print("IRON_SCENE_REPORT_BEGIN")
    print(text)
    print("IRON_SCENE_REPORT_END")
    output = parse_output()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
