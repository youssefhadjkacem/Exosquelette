"""Render raw material for high-resolution presentation portraits.

Uses the scene's existing camera and color pipeline (Eevee/AgX) as already
configured in femme.blend -- no materials, engine, or camera changes. The
source .blend file is never saved, so femme.blend is left untouched.

Renders two PNGs at `--supersample`x the target resolution:
  - <prefix>_full.png: the full validated scene framing (desk, rack, avatar)
  - <prefix>_avatar_only.png: the same shot with every other mesh/armature
    hidden, used only to compute a clean avatar bounding box for cropping

Run crop_presentation_portraits.py afterwards (plain Python, no Blender) to
turn these into the final framed portraits -- see that script's docstring.

Run headless, e.g.:

    "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background \
        "C:\\Users\\youss\\mpfb-data\\femme.blend" --python \
        src/blender/render_presentation_portraits.py -- \
        --output-dir data/presentation_assets/avatar_makehuman \
        --frame 1 --res 1920x1080 --supersample 2
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


def parse_args(argv: list[str]) -> dict:
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    args = {
        "output_dir": "presentation_portraits",
        "frame": 1,
        "res_x": 1920,
        "res_y": 1080,
        "supersample": 2,
    }
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--output-dir":
            args["output_dir"] = argv[i + 1]
            i += 2
        elif token == "--frame":
            args["frame"] = int(argv[i + 1])
            i += 2
        elif token == "--res":
            args["res_x"], args["res_y"] = (int(v) for v in argv[i + 1].split("x"))
            i += 2
        elif token == "--supersample":
            args["supersample"] = int(argv[i + 1])
            i += 2
        else:
            raise ValueError(f"Argument inconnu: {token}")
    return args


AVATAR_OBJECTS = {"Human", "Human.female_casualsuit01", "Human.rig", "Human.ponytail01"}


def main() -> None:
    args = parse_args(sys.argv)
    scene = bpy.context.scene

    camera = bpy.data.objects.get("Camera")
    if camera is None:
        raise ValueError("Aucun objet 'Camera' dans la scene")
    scene.camera = camera

    if scene.render.engine != "BLENDER_EEVEE":
        raise RuntimeError(f"Expected engine BLENDER_EEVEE, got {scene.render.engine}")
    if scene.view_settings.view_transform != "AgX":
        raise RuntimeError(
            f"Expected color management AgX, got {scene.view_settings.view_transform}"
        )

    scene.render.resolution_x = args["res_x"] * args["supersample"]
    scene.render.resolution_y = args["res_y"] * args["supersample"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    scene.frame_set(args["frame"])

    # An absolute path is required: this Blender build resolves relative
    # render paths against the process's own working directory, not the
    # invoking shell's cwd or the .blend file's location.
    output_dir = Path(args["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scene.render.filepath = str(output_dir / "portrait_raw_full.png")
    bpy.ops.render.render(write_still=True)
    print(f"Full scene (hi-res): {scene.render.filepath}")

    hidden = []
    for obj in bpy.data.objects:
        if obj.type in {"MESH", "ARMATURE"} and obj.name not in AVATAR_OBJECTS:
            hidden.append((obj, obj.hide_render))
            obj.hide_render = True

    scene.render.filepath = str(output_dir / "portrait_raw_avatar_only.png")
    bpy.ops.render.render(write_still=True)
    print(f"Avatar-only isolate (for bbox detection): {scene.render.filepath}")

    for obj, was_hidden in hidden:
        obj.hide_render = was_hidden


if __name__ == "__main__":
    main()
