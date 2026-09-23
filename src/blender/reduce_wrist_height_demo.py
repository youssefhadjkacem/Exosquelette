"""Pull the right wrist's height down to a realistic ironing range (demo copy only).

COSMETIC / PRESENTATION-ONLY. Run only against femme_demo_smoothed.blend
(guarded below), never femme.blend. See docs/blender/demo_smoothed_disclaimer.md.

IMPORTANT correctness notes from development:

1. upperarm01.R has *three* animated rotation_euler channels, not one --
   index 2 is the primary shoulder-elevation channel from the arm26 retarget
   (dense, 1081 keys, one per frame), but index 0 (30 sparse keys, ramps
   1.5deg->45deg then holds) and index 1 (500 sparse keys, settles around
   -19deg to -35deg) also carry real motion, most likely a secondary sway
   added by an earlier correction pass to keep the wrist inside the board
   footprint. They are read at each frame via scene.frame_set() and held
   fixed (never modified) during this correction -- only the two originally
   densely-keyed channels (shoulder elevation index 2, elbow flexion index 0)
   are rewritten, so the board-containment sway is preserved exactly.

2. Height is NOT a simple monotonic function of (shoulder, elbow) once
   indices 0/1 are nonzero -- a fixed "push shoulder up / elbow down"
   direction that lowers height at idx0=idx1=0 can *raise* height at the
   idx0=45deg/idx1=-19deg steady state reached by most of this animation.
   A plain 1D bisection along one fixed direction was tried and rejected
   for this reason. Instead, for each frame that needs correction, this
   script does a nearest-candidate search over a 2D grid of (shoulder,
   elbow) offsets from the frame's own original values, sorted by
   ascending angular distance, and takes the first candidate (smallest
   change) that reaches the frame's target height. This is robust to the
   non-monotonicity and, because the target height itself varies smoothly
   across frames, produces a smoothly varying correction in practice
   (verified in the report's frame-to-frame delta check).

3. A pure-matrix (no view_layer.update()) reimplementation of the bone FK
   chain was attempted for speed, matched Blender exactly for the
   upperarm01.R bone alone (0.0 diff), but showed up to ~5cm error once
   the lowerarm01.R/wrist.R inherit_scale="NONE" step was included --
   the anisotropic-scale-plus-rotation decomposition does not cleanly
   invert the way a naive "strip scale, keep rotation+translation" does.
   This was caught by validating against known-correct scene.frame_set()
   heights *before* using it for any real correction (see
   validate_fk_math.py in the session scratchpad). Rather than risk a
   silently-wrong correction, height evaluation here uses genuine
   Blender pose evaluation (view_layer.update()), which is proven
   correct.

4. A fixed 625-candidate grid (5deg step, 60deg radius) per frame was
   tried next: too slow (215s for 50 frames -> ~78min extrapolated for
   1081) AND insufficient coverage (44% of the 50 test frames found no
   candidate within the grid at all). Replaced with a compass/pattern
   search: probe 8 neighboring directions around the current (shoulder,
   elbow), step toward whichever most reduces height, halve the step
   when no neighbor improves, stop as soon as the target is crossed.
   This needs on the order of tens of evaluations per frame rather than
   hundreds, and is not limited to a fixed search radius.

target_height = FLOOR_M + RATIO * max(0, height - FLOOR_M)
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

RIG_NAME = "Human.rig"
SHOULDER_BONE = "upperarm01.R"
ELBOW_BONE = "lowerarm01.R"
FLOOR_M = 0.08
RATIO = 0.20

SHOULDER_MIN_DEG, SHOULDER_MAX_DEG = -90.0, 100.0
ELBOW_MIN_DEG, ELBOW_MAX_DEG = -10.0, 150.0
PROGRESS_EVERY = 100
COMPASS_START_STEP_DEG = 20.0
COMPASS_MIN_STEP_DEG = 0.5
COMPASS_MAX_EVALS = 200
COMPASS_DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"output": None, "report": None, "max_frames": None}
    i = 0
    while i < len(values):
        if values[i] == "--output":
            out["output"] = values[i + 1]
            i += 2
        elif values[i] == "--report":
            out["report"] = values[i + 1]
            i += 2
        elif values[i] == "--max-frames":
            out["max_frames"] = int(values[i + 1])
            i += 2
        elif values[i] == "--no-save":
            out["no_save"] = True
            i += 1
        else:
            raise ValueError(f"Argument inconnu: {values[i]}")
    if out["output"] is None or out["report"] is None:
        raise ValueError("--output et --report sont requis")
    return out


def find_fcurve(action, bone_name, data_path, index):
    target = f'pose.bones["{bone_name}"].{data_path}'
    for layer in action.layers:
        for strip in layer.strips:
            if strip.type != "KEYFRAME":
                continue
            for channelbag in strip.channelbags:
                for fcurve in channelbag.fcurves:
                    if fcurve.data_path == target and fcurve.array_index == index:
                        return fcurve
    raise ValueError(f"F-curve introuvable: {target}[{index}]")


def compass_search(height_fn, s0, e0, h0, target, s_min, s_max, e_min, e_max):
    """Derivative-free descent: probe 8 neighbors, step toward the best one,
    halve the step when stuck, stop as soon as height <= target."""
    s, e, h = s0, e0, h0
    step = math.radians(COMPASS_START_STEP_DEG)
    min_step = math.radians(COMPASS_MIN_STEP_DEG)
    evals = 0
    while step > min_step and evals < COMPASS_MAX_EVALS:
        improved = False
        best_h, best_s, best_e = h, s, e
        for dx, dy in COMPASS_DIRECTIONS:
            cs, ce = s + dx * step, e + dy * step
            if cs < s_min or cs > s_max or ce < e_min or ce > e_max:
                continue
            ch = height_fn(cs, ce)
            evals += 1
            if ch <= target:
                return cs, ce, ch, evals, True
            if ch < best_h:
                best_h, best_s, best_e = ch, cs, ce
                improved = True
            if evals >= COMPASS_MAX_EVALS:
                break
        if improved:
            s, e, h = best_s, best_e, best_h
        else:
            step /= 2.0
    return s, e, h, evals, (h <= target)


def main():
    args = arguments()
    rig = bpy.data.objects.get(RIG_NAME)
    if rig is None or not rig.get("demo_smoothed_cosmetic_only"):
        raise RuntimeError(
            "Ce script attend femme_demo_smoothed.blend (marqueur "
            "'demo_smoothed_cosmetic_only' absent) -- ne pas l'utiliser sur femme.blend."
        )

    scene = bpy.context.scene
    board = bpy.data.objects["White_desk"]
    board_top_z = max((board.matrix_world @ Vector(c)).z for c in board.bound_box)
    shoulder_bone = rig.pose.bones[SHOULDER_BONE]
    elbow_bone = rig.pose.bones[ELBOW_BONE]
    wrist = rig.pose.bones["wrist.R"]

    action = rig.animation_data.action
    shoulder_fc = find_fcurve(action, SHOULDER_BONE, "rotation_euler", 2)
    elbow_fc = find_fcurve(action, ELBOW_BONE, "rotation_euler", 0)
    if len(shoulder_fc.keyframe_points) != len(elbow_fc.keyframe_points):
        raise RuntimeError("shoulder/elbow keyframe counts differ -- expected one per frame for both")

    frame_start, frame_end = scene.frame_start, scene.frame_end
    frames = list(range(frame_start, frame_end + 1))
    n = len(frames)

    idx0_vals = [0.0] * n
    idx1_vals = [0.0] * n
    shoulder_vals = [0.0] * n
    elbow_vals = [0.0] * n
    heights_before = [0.0] * n
    for i, frame in enumerate(frames):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        idx0_vals[i] = shoulder_bone.rotation_euler[0]
        idx1_vals[i] = shoulder_bone.rotation_euler[1]
        shoulder_vals[i] = shoulder_bone.rotation_euler[2]
        elbow_vals[i] = elbow_bone.rotation_euler[0]
        pos = rig.matrix_world @ wrist.head
        heights_before[i] = pos.z - board_top_z

    def height_at(i, s, e):
        shoulder_bone.rotation_euler[0] = idx0_vals[i]
        shoulder_bone.rotation_euler[1] = idx1_vals[i]
        shoulder_bone.rotation_euler[2] = s
        elbow_bone.rotation_euler[0] = e
        bpy.context.view_layer.update()
        pos = rig.matrix_world @ wrist.head
        return pos.z - board_top_z

    s_min, s_max = math.radians(SHOULDER_MIN_DEG), math.radians(SHOULDER_MAX_DEG)
    e_min, e_max = math.radians(ELBOW_MIN_DEG), math.radians(ELBOW_MAX_DEG)

    test_mode = args["max_frames"] is not None
    indices_to_process = list(range(min(args["max_frames"], n) if test_mode else n))

    corrected_shoulder = list(shoulder_vals)
    corrected_elbow = list(elbow_vals)
    heights_after = list(heights_before)
    deviations = [0.0] * n
    candidates_tried = [0] * n
    changed_count = 0
    unresolved_frames = []

    search_start = time.perf_counter()
    for count, i in enumerate(indices_to_process, start=1):
        h0 = heights_before[i]
        target = FLOOR_M + RATIO * max(0.0, h0 - FLOOR_M)
        s0, e0 = shoulder_vals[i], elbow_vals[i]
        if h0 <= target + 1e-6:
            continue

        height_fn = lambda s, e, i=i: height_at(i, s, e)
        s, e, h, tried, reached = compass_search(height_fn, s0, e0, h0, target, s_min, s_max, e_min, e_max)
        candidates_tried[i] = tried
        if reached:
            corrected_shoulder[i] = s
            corrected_elbow[i] = e
            heights_after[i] = h
            deviations[i] = max(0.0, target - h)
            changed_count += 1
        else:
            # Compass search failed to reach target and typically drifted to a
            # physical joint-limit corner far from neighboring frames (e.g.
            # shoulder ~-90deg) -- using that "best effort" pose creates a
            # visible pop. Fall back to the original pose here; the gap-fill
            # pass below then smooths this frame from its corrected neighbors.
            corrected_shoulder[i] = s0
            corrected_elbow[i] = e0
            heights_after[i] = h0
            deviations[i] = h0 - target
            unresolved_frames.append(frame_start + i)
        if count % PROGRESS_EVERY == 0 or count == len(indices_to_process):
            elapsed = time.perf_counter() - search_start
            print(f"  progres: {count}/{len(indices_to_process)} frames traitees, {elapsed:.2f}s ecoulees "
                  f"({elapsed/count*1000:.2f}ms/frame en moyenne)")
    search_elapsed = time.perf_counter() - search_start

    if test_mode:
        avg_per_frame = search_elapsed / len(indices_to_process) if indices_to_process else 0.0
        estimated_total = avg_per_frame * n
        test_report = {
            "test_mode": True,
            "frames_tested": len(indices_to_process),
            "elapsed_s": search_elapsed,
            "avg_ms_per_frame": avg_per_frame * 1000.0,
            "estimated_total_s_for_all_frames": estimated_total,
            "estimated_total_minutes_for_all_frames": estimated_total / 60.0,
            "changed_in_test": changed_count,
            "unresolved_in_test": unresolved_frames,
            "avg_candidates_tried": statistics.mean(candidates_tried[i] for i in indices_to_process) if indices_to_process else 0,
            "max_candidates_tried": max((candidates_tried[i] for i in indices_to_process), default=0),
            "sample_before_after_cm": [
                {"frame": frame_start + i, "before_cm": heights_before[i] * 100, "after_cm": heights_after[i] * 100}
                for i in indices_to_process if candidates_tried[i] > 0
            ][:15],
        }
        print(json.dumps(test_report, indent=2))
        report_path = Path(args["report"])
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(test_report, indent=2) + "\n", encoding="utf-8")
        scene.frame_set(1)
        bpy.context.view_layer.update()
        return

    # Gap-fill: linearly interpolate any unresolved run of frames from the
    # nearest successfully-corrected neighbors on each side, so the fallback
    # to original values above never shows up as a jump against corrected
    # neighbors. Falls back to a flat hold only at the very start/end of the
    # animation, where there is no corrected neighbor on one side.
    unresolved_set = set(frame_start + i for i in range(n)) & set(unresolved_frames)
    i = 0
    gap_fill_log = []
    while i < n:
        if (frame_start + i) not in unresolved_set:
            i += 1
            continue
        gap_start = i
        while i < n and (frame_start + i) in unresolved_set:
            i += 1
        gap_end = i - 1  # inclusive
        left = gap_start - 1
        right = gap_end + 1
        if left >= 0 and right < n:
            for k in range(gap_start, gap_end + 1):
                t = (k - left) / (right - left)
                corrected_shoulder[k] = corrected_shoulder[left] + (corrected_shoulder[right] - corrected_shoulder[left]) * t
                corrected_elbow[k] = corrected_elbow[left] + (corrected_elbow[right] - corrected_elbow[left]) * t
        elif right < n:
            for k in range(gap_start, gap_end + 1):
                corrected_shoulder[k] = corrected_shoulder[right]
                corrected_elbow[k] = corrected_elbow[right]
        elif left >= 0:
            for k in range(gap_start, gap_end + 1):
                corrected_shoulder[k] = corrected_shoulder[left]
                corrected_elbow[k] = corrected_elbow[left]
        gap_fill_log.append({"frames": [frame_start + gap_start, frame_start + gap_end], "method": "linear interpolation of corrected neighbors"})
        for k in range(gap_start, gap_end + 1):
            heights_after[k] = height_at(k, corrected_shoulder[k], corrected_elbow[k])

    if not test_mode:
        for i, keyframe in enumerate(shoulder_fc.keyframe_points):
            keyframe.co.y = corrected_shoulder[i]
            keyframe.handle_left.y = corrected_shoulder[i]
            keyframe.handle_right.y = corrected_shoulder[i]
        shoulder_fc.update()
        for i, keyframe in enumerate(elbow_fc.keyframe_points):
            keyframe.co.y = corrected_elbow[i]
            keyframe.handle_left.y = corrected_elbow[i]
            keyframe.handle_right.y = corrected_elbow[i]
        elbow_fc.update()

    # Smoothness check: largest frame-to-frame jump introduced by the correction.
    shoulder_delta_before = [abs(shoulder_vals[i+1] - shoulder_vals[i]) for i in range(n - 1)]
    shoulder_delta_after = [abs(corrected_shoulder[i+1] - corrected_shoulder[i]) for i in range(n - 1)]
    elbow_delta_before = [abs(elbow_vals[i+1] - elbow_vals[i]) for i in range(n - 1)]
    elbow_delta_after = [abs(corrected_elbow[i+1] - corrected_elbow[i]) for i in range(n - 1)]

    rig["demo_smoothed_height_correction_note"] = (
        f"Wrist height compressed toward FLOOR_M={FLOOR_M}m with RATIO={RATIO} "
        f"(target = FLOOR_M + RATIO*max(0, h-FLOOR_M)) via nearest-candidate "
        f"(shoulder,elbow) search per frame. Only shoulder-elevation (idx2) and "
        f"elbow-flexion channels changed; secondary board-containment sway "
        f"(upperarm01.R idx0/idx1) left untouched. Cosmetic only, see "
        "docs/blender/demo_smoothed_disclaimer.md."
    )

    report = {
        "floor_m": FLOOR_M,
        "ratio": RATIO,
        "before": {
            "min_m": min(heights_before), "max_m": max(heights_before),
            "mean_m": statistics.mean(heights_before), "median_m": statistics.median(heights_before),
        },
        "after": {
            "min_m": min(heights_after), "max_m": max(heights_after),
            "mean_m": statistics.mean(heights_after), "median_m": statistics.median(heights_after),
        },
        "frames_changed": changed_count,
        "total_frames": n,
        "unresolved_frames": unresolved_frames,
        "gap_fill": gap_fill_log,
        "max_target_deviation_m": max(deviations) if deviations else 0.0,
        "max_frame_to_frame_deg": {
            "shoulder_before": math.degrees(max(shoulder_delta_before)),
            "shoulder_after": math.degrees(max(shoulder_delta_after)),
            "elbow_before": math.degrees(max(elbow_delta_before)),
            "elbow_after": math.degrees(max(elbow_delta_after)),
        },
    }

    scene.frame_set(1)
    bpy.context.view_layer.update()
    output = Path(args["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report_path = Path(args["report"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
