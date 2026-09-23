"""Apply the selected work outfit and the final restrained demo palette.

The script replaces only the clothing mesh, material assignments and lights.
Transforms of the avatar, table, iron, rack and camera are asserted unchanged.
"""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector


OUTFIT = (
    r"C:\Users\youss\AppData\Roaming\Blender Foundation\Blender\5.1\extensions"
    r"\.user\blender_org\mpfb\data\clothes\female_casualsuit01"
    r"\female_casualsuit01.mhclo"
)
FACE_TEXTURE = (
    r"C:\Users\youss\AppData\Roaming\Blender Foundation\Blender\5.1\extensions"
    r"\.user\blender_org\mpfb\data\skins\young_caucasian_female_special_suit"
    r"\young_caucasian_female_special_suit.png"
)
OLD_CLOTHES = "Human.female_elegantsuit01"
NEW_CLOTHES = "Human.female_casualsuit01"


def import_human_service():
    from bl_ext.blender_org.mpfb.services import HumanService

    return HumanService


def transform_signature(obj: bpy.types.Object) -> tuple[float, ...]:
    return tuple(value for row in obj.matrix_world for value in row)


def principled_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = color
    return material


def set_existing_principled(material: bpy.types.Material, *, roughness: float) -> None:
    if material is None or not material.use_nodes:
        return
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            node.inputs["Roughness"].default_value = roughness
            if "Coat Weight" in node.inputs:
                node.inputs["Coat Weight"].default_value = 0.04


def replace_clothes() -> bpy.types.Object:
    basemesh = bpy.data.objects["Human"]
    old = bpy.data.objects.get(OLD_CLOTHES)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)

    for modifier in list(basemesh.modifiers):
        if modifier.name == "Delete.female_elegantsuit01":
            basemesh.modifiers.remove(modifier)
    old_group = basemesh.vertex_groups.get("Delete.female_elegantsuit01")
    if old_group is not None:
        basemesh.vertex_groups.remove(old_group)

    clothes = bpy.data.objects.get(NEW_CLOTHES)
    if clothes is None:
        bpy.context.view_layer.objects.active = basemesh
        basemesh.select_set(True)
        clothes = import_human_service().add_mhclo_asset(
            OUTFIT,
            basemesh,
            asset_type="Clothes",
            subdiv_levels=1,
            material_type="MAKESKIN",
            set_up_rigging=True,
            interpolate_weights=True,
            import_subrig=True,
            import_weights=True,
        )
    clothes["demo_role"] = "simple industrial work outfit"
    clothes["demo_palette"] = "native blue work shirt and neutral blue denim trousers"
    for material in clothes.data.materials:
        set_existing_principled(material, roughness=0.62)
    return clothes


def configure_skin() -> None:
    human = bpy.data.objects["Human"]
    skin = principled_material(
        "Demo_Natural_Skin",
        (0.36, 0.17, 0.10, 1.0),
        roughness=0.50,
    )
    shader = next(node for node in skin.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    if "Subsurface Weight" in shader.inputs:
        shader.inputs["Subsurface Weight"].default_value = 0.035
        shader.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.25)
    skin["demo_material_note"] = (
        "Uniform natural skin replaces the special-suit texture that darkened exposed arms."
    )
    face = bpy.data.materials.get("Demo_Face_Detail") or bpy.data.materials.new("Demo_Face_Detail")
    face.use_nodes = True
    nodes = face.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(FACE_TEXTURE, check_existing=True)
    shader.inputs["Roughness"].default_value = 0.50
    if "Subsurface Weight" in shader.inputs:
        shader.inputs["Subsurface Weight"].default_value = 0.025
    face.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    face.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    face["demo_material_note"] = "Original detailed skin texture retained on head only."

    human.data.materials.clear()
    human.data.materials.append(skin)
    human.data.materials.append(face)
    # Keep facial features from the source texture while excluding its painted
    # special-suit regions on the arms and torso.
    for polygon in human.data.polygons:
        polygon.material_index = 1 if polygon.center.z >= 1.44 else 0


def configure_iron() -> None:
    iron = bpy.data.objects["Iron"]
    white = principled_material(
        "Demo_Iron_White_Plastic", (0.82, 0.88, 0.89, 1.0), roughness=0.34
    )
    turquoise = principled_material(
        "Demo_Iron_Turquoise_Handle", (0.025, 0.43, 0.48, 1.0), roughness=0.30
    )
    metal = principled_material(
        "Demo_Iron_Brushed_Metal", (0.30, 0.34, 0.37, 1.0), roughness=0.24, metallic=0.88
    )
    iron.data.materials.clear()
    iron.data.materials.append(white)
    iron.data.materials.append(turquoise)
    iron.data.materials.append(metal)
    # The source iron uses local Z for sole/base/handle separation.
    for polygon in iron.data.polygons:
        center_z = polygon.center.z
        if center_z <= 0.0035:
            polygon.material_index = 2
        elif center_z >= 0.025:
            polygon.material_index = 1
        else:
            polygon.material_index = 0
    iron["demo_material_note"] = "White body, turquoise handle and metallic sole."


def configure_table() -> None:
    palette = {
        "Desk_plastic_white": ((0.74, 0.78, 0.80, 1.0), 0.38, 0.0),
        "Desk_metal_white": ((0.20, 0.23, 0.26, 1.0), 0.28, 0.72),
        "Desk_wood_white": ((0.76, 0.66, 0.50, 1.0), 0.48, 0.0),
        "Desk_particleboard": ((0.84, 0.80, 0.72, 1.0), 0.58, 0.0),
    }
    for name, (color, roughness, metallic) in palette.items():
        material = principled_material(name, color, roughness=roughness, metallic=metallic)
        material["demo_material_note"] = "Light neutral work-surface palette."


def configure_rack() -> None:
    rack = bpy.data.objects.get("Cube.019")
    hangers = bpy.data.objects.get("Plane.009")
    frame_material = principled_material(
        "Demo_Rack_Charcoal_Metal", (0.055, 0.070, 0.080, 1.0), roughness=0.30, metallic=0.82
    )
    hanger_material = principled_material(
        "Demo_Hangers_Dark_Metal", (0.10, 0.12, 0.13, 1.0), roughness=0.34, metallic=0.70
    )
    if rack is not None:
        rack.data.materials.clear()
        rack.data.materials.append(frame_material)
    if hangers is not None:
        hangers.data.materials.clear()
        hangers.data.materials.append(hanger_material)


def aim_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_lighting() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)

    target = Vector((-0.15, -0.25, 1.05))
    definitions = (
        ("Demo_Key", (3.6, -4.0, 5.6), 720.0, 4.0, (1.0, 0.92, 0.84)),
        ("Demo_Fill", (-3.2, -2.2, 3.5), 480.0, 4.5, (0.78, 0.88, 1.0)),
        ("Demo_Rim", (0.5, 3.4, 4.4), 560.0, 3.5, (0.88, 0.94, 1.0)),
    )
    for name, location, energy, size, color in definitions:
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light_data.color = color
        light = bpy.data.objects.new(name, light_data)
        bpy.context.scene.collection.objects.link(light)
        light.location = location
        aim_at(light, target)

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("Demo_World")
        bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.035, 0.045, 0.060, 1.0)
    background.inputs["Strength"].default_value = 0.36


def main() -> None:
    protected = {
        obj.name: transform_signature(obj)
        for obj in bpy.data.objects
        if obj.type != "LIGHT" and obj.name != OLD_CLOTHES
    }
    clothes = replace_clothes()
    configure_skin()
    configure_iron()
    configure_table()
    configure_rack()
    configure_lighting()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene["final_demo_palette"] = True
    scene["final_demo_palette_note"] = (
        "Materials and lighting only; existing avatar/prop/camera transforms preserved."
    )

    changed = []
    for name, signature in protected.items():
        obj = bpy.data.objects.get(name)
        if obj is not None and transform_signature(obj) != signature:
            changed.append(name)
    if changed:
        raise RuntimeError(f"Unexpected transform changes: {changed}")
    if clothes.parent != bpy.data.objects["Human.rig"]:
        raise RuntimeError("Selected clothing is not attached to Human.rig")

    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(f"SELECTED_CLOTHES={clothes.name}")
    print("TRANSFORMS_UNCHANGED=true")
    print(f"SAVED={bpy.data.filepath}")


if __name__ == "__main__":
    main()
