"""Render tight, dedicated camera views of the right-hand/iron grip."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--frames", default="1,541,1081")
    parser.add_argument("--resolution", type=int, default=1000)
    parser.add_argument("--distance", type=float, default=0.70)
    parser.add_argument("--lens", type=float, default=60.0)
    return parser.parse_args(values)


def handle_center(iron: bpy.types.Object) -> Vector:
    points = [iron.matrix_world @ vertex.co for vertex in iron.data.vertices]
    minimum_z = min(point.z for point in points)
    maximum_z = max(point.z for point in points)
    threshold = minimum_z + 0.75 * (maximum_z - minimum_z)
    selected = [point for point in points if point.z >= threshold]
    return sum(selected, Vector()) / len(selected)


def main() -> None:
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    hand_bone = rig.pose.bones["metacarpal3.R"]
    iron = bpy.data.objects["Iron"]
    original_camera = bpy.data.objects["Camera"]

    camera_data = bpy.data.cameras.new("Iron grip close-up camera")
    camera_data.lens = args.lens
    camera_data.sensor_width = 36.0
    camera_data.clip_start = 0.01
    camera = bpy.data.objects.new("Iron grip close-up camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = [int(value) for value in args.frames.split(",")]

    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        hand_center = rig.matrix_world @ ((hand_bone.head + hand_bone.tail) * 0.5)
        grip_center = (hand_center + handle_center(iron)) * 0.5

        # Keep the unobstructed review-camera direction but move physically
        # close to the grip. The target bias includes fingers and soleplate.
        view_vector = (original_camera.matrix_world.translation - grip_center).normalized()
        camera.location = grip_center + view_vector * args.distance
        target = grip_center + Vector((0.0, 0.0, -0.015))
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()

        scene.render.filepath = str(output_dir / f"frame_{frame:04d}_grip_closeup.png")
        bpy.ops.render.render(write_still=True)
        distance = (hand_center - handle_center(iron)).length
        print(f"CLOSEUP frame={frame} camera={args.distance:.3f}m grip={distance:.6f}m")


if __name__ == "__main__":
    main()
