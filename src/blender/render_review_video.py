"""Render the currently-baked animation to a quick review video (Workbench, fast).

Run headless, e.g.:

    "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background \
        "C:\\Users\\youss\\mpfb-data\\femme.blend" --python src/blender/render_review_video.py -- \
        --output data/scenarios/video1_v2/blender_animation_review.mp4
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
    args = {"output": "review.mp4", "res_x": 960, "res_y": 540}
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

    camera = bpy.data.objects.get("Camera")
    if camera is None:
        raise ValueError("Aucun objet 'Camera' dans la scene")
    scene.camera = camera

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = args["res_x"]
    scene.render.resolution_y = args["res_y"]
    scene.render.resolution_percentage = 100

    # This Blender build has no FFMPEG muxer compiled in (only still-image
    # formats are available), so render a PNG sequence and mux it to mp4
    # separately with imageio-ffmpeg.
    scene.render.image_settings.file_format = "PNG"

    output_path = Path(args["output"])
    frames_dir = output_path.parent / f"{output_path.stem}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(frames_dir) + "/frame_"

    print(f"Rendu de {scene.frame_start} a {scene.frame_end} ({scene.render.fps} fps) -> {output_path}")
    bpy.ops.render.render(animation=True)
    print(f"Video sauvegardee: {output_path}")


if __name__ == "__main__":
    main()
