"""Export a validated PPO rollout for Blender; requires an active-exoskeleton model."""

from __future__ import annotations

import argparse
import json

from exo_env import BrasOuvriereEnv
from pipeline_utils import resolve_project_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--human-controls", default=None)
    parser.add_argument("--output", default="data/animation_data.json")
    args = parser.parse_args()
    from stable_baselines3 import PPO
    env = BrasOuvriereEnv(args.model, args.target, args.human_controls)
    agent = PPO.load(str(resolve_project_path(args.agent)))
    observation, _ = env.reset()
    frames = []
    while True:
        action, _ = agent.predict(observation, deterministic=True)
        observation, reward, terminated, truncated, info = env.step(action)
        frames.append({
            "time_s": float(env.data.time), "qpos_rad": env.data.qpos.tolist(),
            "qpos_deg": __import__("numpy").degrees(env.data.qpos).tolist(),
            "exo_action": action.tolist(), "reward": reward, "metrics": info,
        })
        if terminated or truncated:
            break
    env.close()
    output = resolve_project_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(frames, indent=2), encoding="utf-8")
    print(f"Animation: {output} ({len(frames)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
