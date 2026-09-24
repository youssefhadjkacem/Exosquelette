"""Render presentation views of an OpenSim model via forward kinematics.

OpenSim has no headless image-rendering API, and this install is missing the
.vtp bone mesh files (see docs/current_status.md), so the GUI viewport would
show an empty model anyway. Instead this script drives the model with the
Python API -- joint/marker positions and muscle path points, which are
computed independently of mesh geometry -- and draws the result with
matplotlib: bone segments as solid gray lines between joint centers, muscles
as thin red lines along their true path points.

Must run under the Python 3.8 OpenSim environment (see docs/windows_setup.md):

    .venv38\\Scripts\\python.exe src/opensim/render_model_views.py --mode static ^
        --model data/opensim/arm26_scaled.osim ^
        --output data/presentation_assets/opensim

    .venv38\\Scripts\\python.exe src/opensim/render_model_views.py --mode motion ^
        --model data/opensim/arm26_scaled.osim ^
        --mot data/scenarios/pipeline_principal/target_arm26_exploratory.mot ^
        --output data/presentation_assets/opensim --start-time 10 --duration 6
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def configure_opensim_dlls(home: Path) -> None:
    if not hasattr(os, "add_dll_directory"):
        return
    for candidate in (home / "bin", home / "sdk" / "lib", home / "sdk" / "Python" / "opensim"):
        if candidate.exists():
            os.add_dll_directory(str(candidate))


configure_opensim_dlls(Path(r"C:\OpenSim 4.5"))

import opensim as osim  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d import Axes3D  # noqa: E402,F401


BODIES = ["base", "r_humerus", "r_ulna_radius_hand"]
MARKERS = ["r_acromion", "r_humerus_epicondyle", "r_radius_styloid"]
MUSCLES = ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"]


def extract_pose(model: "osim.Model", state: "osim.State") -> dict:
    model.realizePosition(state)
    bodies = {}
    for name in BODIES:
        loc = model.getBodySet().get(name).findStationLocationInGround(state, osim.Vec3(0, 0, 0))
        bodies[name] = (loc.get(0), loc.get(1), loc.get(2))

    markers = {}
    for name in MARKERS:
        loc = model.getMarkerSet().get(name).getLocationInGround(state)
        markers[name] = (loc.get(0), loc.get(1), loc.get(2))

    muscles = {}
    for name in MUSCLES:
        muscle = model.getMuscles().get(name)
        path = muscle.getGeometryPath().getCurrentPath(state)
        pts = []
        for i in range(path.getSize()):
            loc = path.get(i).getLocationInGround(state)
            pts.append((loc.get(0), loc.get(1), loc.get(2)))
        muscles[name] = pts

    return {"bodies": bodies, "markers": markers, "muscles": muscles}


def draw_pose(ax, pose: dict, title: str, fixed_bounds: tuple | None = None) -> None:
    ax.clear()
    markers = pose["markers"]

    # Bone segments: shoulder -> elbow -> wrist, using marker positions
    # (accurate joint/segment endpoints independent of missing mesh files).
    shoulder = markers["r_acromion"]
    elbow = markers["r_humerus_epicondyle"]
    wrist = markers["r_radius_styloid"]
    for a, b in ((shoulder, elbow), (elbow, wrist)):
        ax.plot(*zip(a, b), color="#4a4a4a", linewidth=6, solid_capstyle="round", zorder=2)

    label_map = {"r_acromion": "epaule", "r_humerus_epicondyle": "coude", "r_radius_styloid": "poignet"}
    for name, loc in markers.items():
        ax.scatter(*loc, color="#1f77b4", s=60, zorder=4)
        ax.text(loc[0], loc[1], loc[2], "  " + label_map.get(name, name), fontsize=9, zorder=5)

    # Muscle origins attach near the thorax body origin, not the acromion
    # marker -- show it so the muscle lines don't look disconnected from the
    # arm segment (this offset is real model geometry, not a rendering bug).
    base_loc = pose["bodies"]["base"]
    ax.scatter(*base_loc, color="#7f7f7f", s=40, zorder=4)
    ax.text(base_loc[0], base_loc[1], base_loc[2], "  tronc (origine)", fontsize=8, color="#7f7f7f", zorder=5)

    for name, pts in pose["muscles"].items():
        if len(pts) < 2:
            continue
        xs, ys, zs = zip(*pts)
        ax.plot(xs, ys, zs, color="#c0392b", linewidth=1.4, alpha=0.85, zorder=3)

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title(title)

    if fixed_bounds is not None:
        cx, cy, cz, radius = fixed_bounds
    else:
        all_pts = list(markers.values()) + list(pose["bodies"].values())
        for pts in pose["muscles"].values():
            all_pts.extend(pts)
        xs, ys, zs = zip(*all_pts)
        cx, cy, cz = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2
        radius = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) / 2 + 0.08
    ax.set_xlim(cx - radius, cx + radius)
    ax.set_ylim(cy - radius, cy + radius)
    ax.set_zlim(cz - radius, cz + radius)
    ax.set_box_aspect((1, 1, 1))


def bounding_box(poses: list) -> tuple:
    all_pts = []
    for pose in poses:
        all_pts.extend(pose["markers"].values())
        all_pts.extend(pose["bodies"].values())
        for pts in pose["muscles"].values():
            all_pts.extend(pts)
    xs, ys, zs = zip(*all_pts)
    cx, cy, cz = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2
    radius = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) / 2 + 0.08
    return cx, cy, cz, radius


def cmd_static(args: argparse.Namespace) -> None:
    model = osim.Model(args.model)
    state = model.initSystem()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    views = [
        ("opensim_model_scaled_01.png", 20, -60, "arm26_scaled -- vue 3/4"),
        ("opensim_model_scaled_02.png", 20, 125, "arm26_scaled -- vue 3/4 (cote oppose)"),
        ("opensim_model_scaled_03.png", 5, -60, "arm26_scaled -- vue de profil"),
    ]
    pose = extract_pose(model, state)

    fig = plt.figure(figsize=(12.8, 7.2), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    for filename, elev, azim, title in views:
        draw_pose(ax, pose, title)
        ax.view_init(elev=elev, azim=azim)
        out_path = output_dir / filename
        fig.savefig(out_path, facecolor="white")
        print(f"Saved {out_path}")
    plt.close(fig)


def cmd_motion(args: argparse.Namespace) -> None:
    model = osim.Model(args.model)
    state = model.initSystem()
    coord_shoulder = model.getCoordinateSet().get("r_shoulder_elev")
    coord_elbow = model.getCoordinateSet().get("r_elbow_flex")

    storage = osim.Storage(args.mot)
    n_rows = storage.getSize()
    time_col = -1
    labels = storage.getColumnLabels()
    col_shoulder = None
    col_elbow = None
    for i in range(labels.getSize()):
        if labels.get(i) == "r_shoulder_elev":
            col_shoulder = i - 1  # column 0 is time, not included in StateVector values
        if labels.get(i) == "r_elbow_flex":
            col_elbow = i - 1

    frames = []
    for row in range(n_rows):
        state_vec = storage.getStateVector(row)
        t = state_vec.getTime()
        vals = state_vec.getData()
        frames.append((t, vals.get(col_shoulder), vals.get(col_elbow)))

    start = args.start_time
    end = start + args.duration
    selected = [f for f in frames if start <= f[0] <= end]
    selected = selected[:: args.stride]
    print(f"{len(selected)} frames selected from t={start}s to t={end}s (stride={args.stride})")

    frames_dir = Path(args.output) / "opensim_motion_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Pass 1: compute every frame's pose and a fixed camera box for the whole
    # clip -- without this the axis limits auto-fit per frame (muscle
    # wrapping points can jump at extreme joint angles), making the arm
    # appear to teleport around the frame instead of moving smoothly.
    poses = []
    for t, shoulder_deg, elbow_deg in selected:
        coord_shoulder.setValue(state, osim.SimTK_DEGREE_TO_RADIAN * shoulder_deg)
        coord_elbow.setValue(state, osim.SimTK_DEGREE_TO_RADIAN * elbow_deg)
        poses.append((t, extract_pose(model, state)))
    fixed_bounds = bounding_box([p for _, p in poses])

    fig = plt.figure(figsize=(12.8, 7.2), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    for idx, (t, pose) in enumerate(poses):
        draw_pose(ax, pose, f"arm26_scaled -- mouvement V2 (t={t:.2f}s)", fixed_bounds=fixed_bounds)
        ax.view_init(elev=15, azim=-75)
        out_path = frames_dir / f"frame_{idx:04d}.png"
        fig.savefig(out_path, facecolor="white")
    plt.close(fig)
    print(f"{len(selected)} frames rendered to {frames_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["static", "motion"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mot")
    parser.add_argument("--start-time", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--stride", type=int, default=1)
    args = parser.parse_args()

    if args.mode == "static":
        cmd_static(args)
    else:
        if not args.mot:
            raise ValueError("--mot est requis pour --mode motion")
        cmd_motion(args)


if __name__ == "__main__":
    main()
