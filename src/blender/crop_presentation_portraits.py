"""Crop raw Blender portrait renders into framed presentation portraits.

Takes the two supersampled PNGs produced by render_presentation_portraits.py
and produces two framed, resized-to-target-resolution portraits:
  - avatar_portrait_01.png: wide shot (avatar + desk/iron/rack context)
  - avatar_portrait_02.png: close-up (head to mid-torso)

The avatar-only render is used solely to find a clean bounding box (no desk
or rack pixels), which is then applied to crop the full-scene render so the
final portraits keep the scene context. Plain Python (PIL/NumPy) -- run with
the project's regular Python, not Blender's.

    .venv310\\Scripts\\python.exe src/blender/crop_presentation_portraits.py \
        --dir data/presentation_assets/avatar_makehuman --res 1920x1080
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def find_avatar_bbox(avatar_only_path: Path, threshold: int = 15) -> tuple[int, int, int, int]:
    img = Image.open(avatar_only_path).convert("RGB")
    arr = np.array(img)
    bg = arr[5, 5].astype(int)
    diff = np.abs(arr.astype(int) - bg).sum(axis=2)
    mask = diff > threshold
    ys, xs = np.where(mask)
    if len(xs) == 0:
        raise RuntimeError(f"Aucun pixel avatar detecte dans {avatar_only_path}")
    return xs.min(), xs.max(), ys.min(), ys.max()


def crop_and_resize(
    img: Image.Image, cx: float, y_top: float, height: int, target_res: tuple[int, int]
) -> Image.Image:
    width_img, height_img = img.size
    aspect = target_res[0] / target_res[1]
    crop_w = int(height * aspect)
    x_lo = max(0, int(cx - crop_w / 2))
    x_hi = min(width_img, x_lo + crop_w)
    y_lo = max(0, int(y_top))
    y_hi = min(height_img, y_lo + height)
    crop = img.crop((x_lo, y_lo, x_hi, y_hi))
    return crop.resize(target_res, Image.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Contient les rendus bruts et recoit les portraits finaux")
    parser.add_argument("--res", default="1920x1080")
    args = parser.parse_args()

    target_res = tuple(int(v) for v in args.res.split("x"))
    base = Path(args.dir)

    full_path = base / "portrait_raw_full.png"
    avatar_only_path = base / "portrait_raw_avatar_only.png"
    img_full = Image.open(full_path).convert("RGB")

    ax0, ax1, ay0, ay1 = find_avatar_bbox(avatar_only_path)
    avatar_cx = (ax0 + ax1) / 2
    avatar_h = ay1 - ay0
    avatar_cy = (ay0 + ay1) / 2 - avatar_h * 0.05

    wide = crop_and_resize(img_full, avatar_cx, avatar_cy - int(avatar_h * 0.75), int(avatar_h * 1.5), target_res)
    wide_path = base / "avatar_portrait_01.png"
    wide.save(wide_path)
    print(f"Saved {wide_path} (plan large, avatar + contexte scene)")

    closeup = crop_and_resize(img_full, avatar_cx, ay0 - int(avatar_h * 0.11), int(avatar_h * 0.72), target_res)
    closeup_path = base / "avatar_portrait_02.png"
    closeup.save(closeup_path)
    print(f"Saved {closeup_path} (plan rapproche, tete a mi-torse)")

    full_path.unlink()
    avatar_only_path.unlink()


if __name__ == "__main__":
    main()
