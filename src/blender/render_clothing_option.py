"""Render one MPFB2 clothing option on the project avatar in a neutral pose.

This script is intended for Blender background mode.  It never saves the
opened blend file, so generating previews cannot modify the working scene.

Usage after ``--``::

    blender -b femme.blend -P render_clothing_option.py -- asset.mhclo out.png
"""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector


def script_arguments() -> tuple[str, str]:
    try:
        separator = sys.argv.index("--")
        mhclo_path, output_path = sys.argv[separator + 1 : separator + 3]
    except (ValueError, IndexError) as exc:
        raise RuntimeError("Expected: -- <asset.mhclo> <preview.png>") from exc
    return os.path.abspath(mhclo_path), os.path.abspath(output_path)


def import_mpfb_services():
    try:
        from bl_ext.blender_org.mpfb.services import HumanService
    except ImportError:
        from bl_ext.user_default.mpfb.services import HumanService
    return HumanService


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def evaluated_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    corners: list[Vector] = []
    for obj in objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        corners.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
    if not corners:
        raise RuntimeError("No visible avatar mesh found for camera framing")
    minimum = Vector(tuple(min(point[i] for point in corners) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in corners) for i in range(3)))
    return minimum, maximum


def main() -> None:
    mhclo_path, output_path = script_arguments()
    if not os.path.isfile(mhclo_path):
        raise FileNotFoundError(mhclo_path)

    basemesh = bpy.data.objects.get("Human")
    rig = bpy.data.objects.get("Human.rig")
    old_clothes = bpy.data.objects.get("Human.female_elegantsuit01")
    if basemesh is None or rig is None:
        raise RuntimeError("Expected Human and Human.rig in the source scene")

    # Rest pose gives every candidate the same neutral comparison pose.
    rig.data.pose_position = "REST"
    bpy.context.scene.frame_set(1)
    if old_clothes is not None:
        old_clothes.hide_render = True
        old_clothes.hide_viewport = True

    # The source garment owns body MASK modifiers.  Hiding only its mesh would
    # otherwise leave holes shaped like its long sleeves in every candidate.
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.name.startswith("Human"):
            for modifier in obj.modifiers:
                if modifier.type == "MASK" and modifier.name.startswith("Delete."):
                    modifier.show_render = False
                    modifier.show_viewport = False

    # Isolate the avatar and its MPFB body parts from the demonstration set.
    for obj in bpy.context.scene.objects:
        if obj == rig or obj.name == "Human" or obj.name.startswith("Human."):
            continue
        obj.hide_render = True
        obj.hide_viewport = True

    bpy.context.view_layer.objects.active = basemesh
    basemesh.select_set(True)
    HumanService = import_mpfb_services()
    clothes = HumanService.add_mhclo_asset(
        mhclo_path,
        basemesh,
        asset_type="Clothes",
        subdiv_levels=1,
        material_type="MAKESKIN",
        set_up_rigging=True,
        interpolate_weights=True,
        import_subrig=True,
        import_weights=True,
    )
    clothes.hide_render = False
    clothes.hide_viewport = False

    visible_meshes = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.name.startswith("Human") and not obj.hide_render
    ]
    minimum, maximum = evaluated_bounds(visible_meshes)
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    print(f"VISIBLE_MESHES={[obj.name for obj in visible_meshes]}")
    print(f"BOUNDS_MIN={tuple(minimum)}")
    print(f"BOUNDS_MAX={tuple(maximum)}")

    camera_data = bpy.data.cameras.new("Clothing preview camera")
    camera = bpy.data.objects.new("Clothing preview camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    # Front three-quarter view, framed independently of the scene camera.
    camera.location = center + Vector((height * 0.82, -height * 1.75, height * 0.10))
    point_camera(camera, center + Vector((0.0, 0.0, height * 0.02)))
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = height * 1.12
    bpy.context.scene.camera = camera

    key = bpy.data.lights.new("Clothing preview key", "AREA")
    key.energy = 1100
    key.shape = "DISK"
    key.size = height * 1.4
    key_obj = bpy.data.objects.new("Clothing preview key", key)
    bpy.context.scene.collection.objects.link(key_obj)
    key_obj.location = center + Vector((-height, -height * 1.4, height * 1.25))
    point_camera(key_obj, center)

    fill = bpy.data.lights.new("Clothing preview fill", "AREA")
    fill.energy = 650
    fill.size = height
    fill_obj = bpy.data.objects.new("Clothing preview fill", fill)
    bpy.context.scene.collection.objects.link(fill_obj)
    fill_obj.location = center + Vector((height * 1.3, -height * 0.5, height * 0.55))
    point_camera(fill_obj, center)

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("Clothing preview world")
        bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.055, 0.065, 0.08, 1.0)
    background.inputs["Strength"].default_value = 0.45

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.055, 0.065, 0.08)
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = output_path
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"CAMERA_LOCATION={tuple(camera.location)}")
    print(f"CAMERA_ORTHO_SCALE={camera_data.ortho_scale}")
    bpy.ops.render.render(write_still=True)
    print(f"CLOTHING_OPTION={os.path.basename(mhclo_path)}")
    print(f"CLOTHING_OBJECT={clothes.name}")
    print(f"PREVIEW={output_path}")


if __name__ == "__main__":
    main()
