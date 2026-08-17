"""Evaluate zero and deterministic assistance on the synthetic RL sandbox."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

from exploratory_assist_env import ExploratoryAssistEnv, resolve


def evaluate(config_path: str | Path, policy: str, assistance_fraction: float) -> tuple[dict, list[dict]]:
    env = ExploratoryAssistEnv(config_path)
    _, _ = env.reset(seed=int(env.config["evaluation"]["seed"]))
    rows: list[dict] = []
    rewards, tracking, human_torques, exo_torques = [], [], [], []
    terminated = truncated = False
    while not (terminated or truncated):
        if policy == "zero":
            action = np.zeros(env.action_space.shape, dtype=np.float32)
        elif policy == "pd_assist":
            desired = env.desired_human_torque()
            limits = env.exo_ranges[:, 1]
            action = np.clip(assistance_fraction * desired / limits, -1.0, 1.0).astype(np.float32)
        else:
            raise ValueError(f"unknown policy: {policy}")
        _, reward, terminated, truncated, info = env.step(action)
        rewards.append(reward)
        tracking.append(info["tracking_mse_rad2"])
        human_torques.append(info["human_torque_nm"])
        exo_torques.append(info["exo_torque_nm"])
        rows.append({
            "policy": policy,
            "time_s": env.data.time,
            "shoulder_angle_rad": env.data.qpos[0],
            "elbow_angle_rad": env.data.qpos[1],
            "tracking_mse_rad2": info["tracking_mse_rad2"],
            "human_shoulder_torque_nm": info["human_torque_nm"][0],
            "human_elbow_torque_nm": info["human_torque_nm"][1],
            "exo_shoulder_torque_nm": info["exo_torque_nm"][0],
            "exo_elbow_torque_nm": info["exo_torque_nm"][1],
            "reward": reward,
        })
    human = np.asarray(human_torques)
    exo = np.asarray(exo_torques)
    summary = {
        "policy": policy,
        "steps": len(rewards),
        "duration_s": float(env.data.time),
        "return": float(np.sum(rewards)),
        "tracking_rmse_deg": math.degrees(math.sqrt(float(np.mean(tracking)))),
        "human_torque_rms_nm": {
            "shoulder": float(np.sqrt(np.mean(human[:, 0] ** 2))),
            "elbow": float(np.sqrt(np.mean(human[:, 1] ** 2))),
        },
        "exo_torque_rms_nm": {
            "shoulder": float(np.sqrt(np.mean(exo[:, 0] ** 2))),
            "elbow": float(np.sqrt(np.mean(exo[:, 1] ** 2))),
        },
    }
    env.close()
    return summary, rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/rl/exploratory_sandbox_v1.json")
    args = parser.parse_args(argv)
    try:
        config_path = resolve(args.config)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        fraction = float(config["evaluation"]["assistance_fraction"])
        summaries, all_rows = [], []
        for policy in ("zero", "pd_assist"):
            summary, rows = evaluate(config_path, policy, fraction)
            summaries.append(summary)
            all_rows.extend(rows)
        zero, assisted = summaries
        reductions = {}
        for joint in ("shoulder", "elbow"):
            baseline = zero["human_torque_rms_nm"][joint]
            value = assisted["human_torque_rms_nm"][joint]
            reductions[joint] = 100.0 * (1.0 - value / baseline) if baseline > 0 else 0.0
        report = {
            "schema_version": 1,
            "status": "SOFTWARE_EXPLORATION_ONLY",
            "sandbox_id": config["sandbox_id"],
            "baselines": summaries,
            "pd_assist_human_torque_reduction_pct": reductions,
            "scientific_claims_allowed": False,
            "hardware_deployment_allowed": False,
            "interpretation": "Software regression baseline only; not an exoskeleton efficacy result.",
        }
        output = resolve(config["evaluation_report"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        timeseries = resolve(config["evaluation_timeseries"])
        with timeseries.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]))
            writer.writeheader()
            writer.writerows(all_rows)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Evaluation RL exploratoire impossible: {exc}", file=sys.stderr)
        return 2
    print(f"Evaluation: {output}")
    print(
        "Reduction proxy couple humain (logiciel uniquement): "
        f"epaule={reductions['shoulder']:.1f}%, coude={reductions['elbow']:.1f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
