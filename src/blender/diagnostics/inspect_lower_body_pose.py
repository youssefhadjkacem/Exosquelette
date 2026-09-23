"""Check whether lower-body bones or vertices move during the animation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


LOWER_BONES = (
    "pelvis.L", "upperleg01.L", "upperleg02.L", "lowerleg01.L",
    "lowerleg02.L", "foot.L", "toe1-1.L", "pelvis.R", "upperleg01.R",
    "upperleg02.R", "lowerleg01.R", "lowerleg02.R", "foot.R", "toe1-1.R",
)


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(values)


def flattened_matrix(matrix) -> list[float]:
    return [float(value) for row in matrix for value in row]


def evaluated_vertices(obj: bpy.types.Object) -> list[tuple[float, float, float]]:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [tuple(evaluated.matrix_world @ vertex.co) for vertex in evaluated.data.vertices]


def main() -> None:
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    human = bpy.data.objects["Human"]
    frames = [scene.frame_start, (scene.frame_start + scene.frame_end) // 2, scene.frame_end]
    samples: dict[str, dict] = {}
    lower_vertices: dict[str, list] = {}

    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        samples[str(frame)] = {
            name: {
                "matrix_basis": flattened_matrix(rig.pose.bones[name].matrix_basis),
                "head_world": list(rig.matrix_world @ rig.pose.bones[name].head),
                "tail_world": list(rig.matrix_world @ rig.pose.bones[name].tail),
            }
            for name in LOWER_BONES
        }
        lower_vertices[str(frame)] = evaluated_vertices(human)

    reference_frame = str(frames[0])
    reference_vertices = lower_vertices[reference_frame]
    lower_indices = [index for index, point in enumerate(reference_vertices) if point[2] < 0.75]
    vertex_displacements = {}
    for frame in frames[1:]:
        current = lower_vertices[str(frame)]
        vertex_displacements[str(frame)] = max(
            sum((current[index][axis] - reference_vertices[index][axis]) ** 2 for axis in range(3)) ** 0.5
            for index in lower_indices
        )

    bone_differences = {}
    for frame in frames[1:]:
        bone_differences[str(frame)] = {}
        for name in LOWER_BONES:
            first = samples[reference_frame][name]["matrix_basis"]
            current = samples[str(frame)][name]["matrix_basis"]
            bone_differences[str(frame)][name] = max(abs(a - b) for a, b in zip(first, current))

    maximum_bone_difference = max(
        difference
        for per_frame in bone_differences.values()
        for difference in per_frame.values()
    )
    maximum_vertex_displacement = max(vertex_displacements.values())
    report = {
        "blend_file": bpy.data.filepath,
        "frames": frames,
        "lower_body_bones": list(LOWER_BONES),
        "maximum_bone_matrix_difference": maximum_bone_difference,
        "lower_body_vertex_count": len(lower_indices),
        "maximum_lower_body_vertex_displacement_m": maximum_vertex_displacement,
        "classification": (
            "STATIC_LOWER_BODY_CAMERA_OR_OCCLUSION_EFFECT"
            if maximum_bone_difference < 1e-8 and maximum_vertex_displacement < 1e-8
            else "LOWER_BODY_ANIMATION_OR_DEFORMATION_DETECTED"
        ),
        "bone_differences": bone_differences,
        "vertex_displacements_m": vertex_displacements,
        "samples": samples,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "frames", "maximum_bone_matrix_difference",
        "maximum_lower_body_vertex_displacement_m", "classification",
    )}, indent=2))


if __name__ == "__main__":
    main()
