"""Render the final colored presentation video (Eevee, as configured by
apply_final_demo_materials.py -- engine/AgX look are left as already set in
the file, not overridden to Workbench like the fast preview script).

Run headless, e.g.:

    "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background \
        "C:\\Users\\youss\\mpfb-data\\femme.blend" --python src/blender/render_final_demo_video.py -- \
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

    if scene.render.engine != "BLENDER_EEVEE":
        raise RuntimeError(
            f"Expected engine BLENDER_EEVEE (set by apply_final_demo_materials.py), got {scene.render.engine}"
        )

    scene.render.resolution_x = args["res_x"]
    scene.render.resolution_y = args["res_y"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    # An absolute path is required: this Blender build resolves relative
    # render paths against the process's own working directory, not the
    # invoking shell's cwd or the .blend file's location.
    output_path = Path(args["output"]).resolve()
    frames_dir = output_path.parent / f"{output_path.stem}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(frames_dir) + "/frame_"

    print(f"Rendu EEVEE de {scene.frame_start} a {scene.frame_end} ({scene.render.fps} fps) -> {frames_dir}")
    bpy.ops.render.render(animation=True)
    print(f"Frames rendues dans: {frames_dir}")


if __name__ == "__main__":
    main()
