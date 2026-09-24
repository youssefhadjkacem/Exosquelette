"""Inspect the avatar provenance, dimensions, rig, and attached assets."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector


OUTPUT = Path("C:/Users/youss/exosquelette/data/scenarios/pipeline_principal/avatar_metadata.json")
RIG_NAME = "Human.rig"
BODY_NAME = "Human"


def json_value(value):
    try:
        return value.to_list()
    except AttributeError:
        pass
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


def custom_properties(owner):
    return {
        key: json_value(owner[key])
        for key in owner.keys()
        if key != "_RNA_UI"
    }


def evaluated_world_bounds(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    evaluated.to_mesh_clear()
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    return {
        "minimum_xyz_m": minimum,
        "maximum_xyz_m": maximum,
        "dimensions_xyz_m": [maximum[i] - minimum[i] for i in range(3)],
        "height_m": maximum[2] - minimum[2],
    }


def bone_point(armature, bone_name, attribute):
    bone = armature.data.bones[bone_name]
    return armature.matrix_world @ getattr(bone, attribute)


def distance(a, b):
    return float((a - b).length)


def main():
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rig = bpy.data.objects[RIG_NAME]
    body = bpy.data.objects[BODY_NAME]

    shoulder = bone_point(rig, "upperarm01.R", "head_local")
    elbow = bone_point(rig, "lowerarm01.R", "head_local")
    wrist = bone_point(rig, "wrist.R", "head_local")

    object_records = []
    for obj in bpy.data.objects:
        armature_targets = [
            modifier.object.name
            for modifier in obj.modifiers
            if modifier.type == "ARMATURE" and modifier.object
        ]
        constraints = []
        for constraint in obj.constraints:
            constraints.append({
                "name": constraint.name,
                "type": constraint.type,
                "target": constraint.target.name if getattr(constraint, "target", None) else None,
                "subtarget": getattr(constraint, "subtarget", ""),
            })
        if obj.parent == rig or RIG_NAME in armature_targets or constraints:
            object_records.append({
                "name": obj.name,
                "type": obj.type,
                "parent": obj.parent.name if obj.parent else None,
                "parent_type": obj.parent_type,
                "parent_bone": obj.parent_bone,
                "armature_targets": armature_targets,
                "constraints": constraints,
                "custom_properties": custom_properties(obj),
                "library": obj.library.filepath if obj.library else None,
                "data_library": obj.data.library.filepath if obj.data and obj.data.library else None,
            })

    relevant_properties = {
        "scene": custom_properties(scene),
        "rig": custom_properties(rig),
        "rig_data": custom_properties(rig.data),
        "body": custom_properties(body),
        "body_data": custom_properties(body.data),
    }
    report = {
        "blend_file": bpy.data.filepath,
        "blender_version_used_for_inspection": bpy.app.version_string,
        "scene_custom_properties": relevant_properties,
        "body_geometry": evaluated_world_bounds(body, depsgraph),
        "arm_segments_right_rest_pose": {
            "definition": "Euclidean distance between rig joint centers in armature rest pose",
            "shoulder_joint": "upperarm01.R head",
            "elbow_joint": "lowerarm01.R head",
            "wrist_joint": "wrist.R head",
            "shoulder_xyz_m": list(shoulder),
            "elbow_xyz_m": list(elbow),
            "wrist_xyz_m": list(wrist),
            "shoulder_to_elbow_m": distance(shoulder, elbow),
            "elbow_to_wrist_m": distance(elbow, wrist),
        },
        "rig": {
            "object_name": rig.name,
            "data_name": rig.data.name,
            "bone_count": len(rig.data.bones),
            "pose_bone_count": len(rig.pose.bones),
            "identified_standard": "MPFB default_no_toes (exact 137-bone name match)",
            "bone_names": [bone.name for bone in rig.data.bones],
        },
        "attached_or_constrained_objects": object_records,
        "libraries": [library.filepath for library in bpy.data.libraries],
        "text_blocks": [text.name for text in bpy.data.texts],
        "shape_keys": {
            obj.name: [
                {
                    "name": key.name,
                    "value": float(key.value),
                    "slider_min": float(key.slider_min),
                    "slider_max": float(key.slider_max),
                }
                for key in obj.data.shape_keys.key_blocks
            ] if obj.type == "MESH" and obj.data.shape_keys else []
            for obj in bpy.data.objects
            if obj.type == "MESH" and (obj.name == BODY_NAME or obj.parent == rig or RIG_NAME in [m.object.name for m in obj.modifiers if m.type == "ARMATURE" and m.object])
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


main()
