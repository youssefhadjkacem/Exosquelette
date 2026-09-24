"""Fit an MPFB2/MakeHuman hair asset (.mhclo) onto the avatar and rig it.

Uses MPFB2's own HumanService.add_mhclo_asset, the same code path the MPFB2
UI panel uses to load clothes/hair -- this fits the mesh to the basemesh
shape and skins it to the existing armature (import_weights=True uses the
asset's own hand-tuned .mhw weights file when one is shipped, e.g.
ponytail01.mhw, instead of a generic interpolation), so the hair follows
head movement through the rig rather than being a static, unparented mesh.

Saves the .blend file in place -- run this only against a backup copy
(femme.before_<change>.blend), never as a first save of unbacked-up work.

Run headless, e.g.:

    "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background \
        "C:\\Users\\youss\\mpfb-data\\femme.blend" --python \
        src/blender/add_hair_asset.py -- \
        --mhclo "C:\\Users\\youss\\AppData\\Local\\makehuman-community\\makehuman\\data\\hair\\ponytail01\\ponytail01.mhclo"
"""

from __future__ import annotations

import sys

import bpy


def parse_args(argv: list[str]) -> dict:
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    args = {"mhclo": None, "basemesh": "Human", "save": True}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--mhclo":
            args["mhclo"] = argv[i + 1]
            i += 2
        elif token == "--basemesh":
            args["basemesh"] = argv[i + 1]
            i += 2
        elif token == "--no-save":
            args["save"] = False
            i += 1
        else:
            raise ValueError(f"Argument inconnu: {token}")
    if not args["mhclo"]:
        raise ValueError("--mhclo est requis")
    return args


def main() -> None:
    args = parse_args(sys.argv)

    from bl_ext.blender_org.mpfb.services import HumanService, ObjectService  # noqa: E402

    basemesh = bpy.data.objects.get(args["basemesh"])
    if basemesh is None:
        raise ValueError(f"Basemesh introuvable: {args['basemesh']}")

    existing = ObjectService.find_object_of_type_amongst_nearest_relatives(basemesh, "Hair")
    if existing is not None:
        raise RuntimeError(
            f"Un objet Hair existe deja ({existing.name}) -- ne pas en ajouter un second sans le retirer d'abord."
        )

    clothes = HumanService.add_mhclo_asset(
        args["mhclo"],
        basemesh,
        asset_type="Hair",
        material_type="MAKESKIN",
        set_up_rigging=True,
        interpolate_weights=True,
        import_subrig=True,
        import_weights=True,
    )

    print(f"Hair object created: {clothes.name}")
    print(f"  vertices: {len(clothes.data.vertices)}")
    print(f"  parent: {clothes.parent.name if clothes.parent else None}")
    print(f"  modifiers: {[(m.name, m.type) for m in clothes.modifiers]}")
    for mod in clothes.modifiers:
        if mod.type == "ARMATURE":
            print(f"  armature modifier target: {mod.object.name if mod.object else None}")
    vgroups = [g.name for g in clothes.vertex_groups]
    print(f"  vertex groups ({len(vgroups)}): {vgroups[:10]}{'...' if len(vgroups) > 10 else ''}")

    if args["save"]:
        bpy.ops.wm.save_mainfile()
        print(f"Saved: {bpy.data.filepath}")


if __name__ == "__main__":
    main()
