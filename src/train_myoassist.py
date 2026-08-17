"""Train PPO only after motion, OpenSim and MuJoCo readiness gates pass."""

from __future__ import annotations

import argparse
import json
import sys

from exo_env import BrasOuvriereEnv
from pipeline_utils import resolve_project_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Modele MuJoCo avec actionneurs exo_*.")
    parser.add_argument("--target", default="data/results/opensim/ik_results.mot")
    parser.add_argument("--human-controls", required=True, help="Activations humaines de reference OpenSim.")
    parser.add_argument("--readiness", default="data/results/rl_readiness.json")
    parser.add_argument("--output", default="models/myoassist/myoassist_trained")
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    try:
        readiness = json.loads(resolve_project_path(args.readiness).read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"Rapport readiness absent: {exc}", file=sys.stderr)
        return 2
    if readiness.get("status") != "PASS":
        print("Entrainement bloque. Corrigez les echecs de validate_rl_readiness.py.", file=sys.stderr)
        return 1
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.env_checker import check_env
        env = BrasOuvriereEnv(args.model, args.target, args.human_controls)
        check_env(env)
        output = resolve_project_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        agent = PPO("MlpPolicy", env, verbose=1, seed=args.seed, tensorboard_log=str(output.parent / "tensorboard"))
        agent.learn(total_timesteps=args.timesteps)
        agent.save(str(output))
        env.close()
    except (ImportError, ValueError, RuntimeError) as exc:
        print(f"Entrainement impossible: {exc}", file=sys.stderr)
        return 1
    print(f"Modele PPO: {output}.zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
