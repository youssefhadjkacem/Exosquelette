"""Render selected animation frames with the scene camera for visual QA."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


def parse_args() -> tuple[Path, list[int], int, int, str]:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    output = Path(args[args.index("--output") + 1])
    frames = [int(value) for value in args[args.index("--frames") + 1].split(",")]
    width, height = (960, 540)
    if "--res" in args:
        width, height = (int(value) for value in args[args.index("--res") + 1].split("x"))
    engine = args[args.index("--engine") + 1].upper() if "--engine" in args else "WORKBENCH"
    return output, frames, width, height, engine


def main() -> None:
    output, frames, width, height, engine = parse_args()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    if engine == "EEVEE":
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(output / f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"Frame {frame}: {scene.render.filepath}")


if __name__ == "__main__":
    main()
