"""Render the presentation-only smoothed demo video (Eevee).

COSMETIC DEMO ONLY -- see docs/blender/demo_smoothed_disclaimer.md. Must be
run against femme_demo_smoothed.blend, never against the reference
femme.blend. Identical rendering approach to render_final_demo_video.py
(engine/AgX look left as already configured in the file).

Run headless, e.g.:

    "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background \
        "C:\\Users\\youss\\mpfb-data\\femme_demo_smoothed.blend" --python \
        src/blender/render_demo_smoothed_video.py -- \
        --output data/scenarios/video1_v2/blender_animation_demo_smoothed.mp4
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
    args = {"output": "demo_smoothed.mp4", "res_x": 960, "res_y": 540}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--output":
            args["output"] = argv[i + 1]
            i += 2
        elif token == "--res":
            args["res_x"], args["res_y"] = (int(v) for v in argv[i + 1].split("x"))
            i += 2
        else:
            raise ValueError(f"Argument inconnu: {token}")
    return args


def main() -> None:
    args = parse_args(sys.argv)
    scene = bpy.context.scene

    rig = bpy.data.objects.get("Human.rig")
    if rig is None or not rig.get("demo_smoothed_cosmetic_only"):
        raise RuntimeError(
            "Ce script attend femme_demo_smoothed.blend (marqueur "
            "'demo_smoothed_cosmetic_only' absent) -- ne pas l'utiliser sur femme.blend."
        )

    camera = bpy.data.objects.get("Camera")
    if camera is None:
        raise ValueError("Aucun objet 'Camera' dans la scene")
    scene.camera = camera

    if scene.render.engine != "BLENDER_EEVEE":
        raise RuntimeError(f"Expected engine BLENDER_EEVEE, got {scene.render.engine}")

    scene.render.resolution_x = args["res_x"]
    scene.render.resolution_y = args["res_y"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    output_path = Path(args["output"])
    frames_dir = output_path.parent / f"{output_path.stem}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(frames_dir.resolve()) + "/frame_"

    print(f"Rendu EEVEE (demo lissee) de {scene.frame_start} a {scene.frame_end} ({scene.render.fps} fps) -> {frames_dir}")
    bpy.ops.render.render(animation=True)
    print(f"Frames rendues dans: {frames_dir}")


if __name__ == "__main__":
    main()
