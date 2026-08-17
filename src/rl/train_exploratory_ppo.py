"""Train PPO in the synthetic sandbox after explicit exploratory acknowledgement."""

from __future__ import annotations

import argparse
import json
import sys

from exploratory_assist_env import ExploratoryAssistEnv, resolve


ACKNOWLEDGEMENT = "software-only-no-scientific-claim"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/rl/exploratory_sandbox_v1.json")
    parser.add_argument("--timesteps", type=int)
    parser.add_argument("--acknowledge", default="")
    args = parser.parse_args(argv)
    if args.acknowledge != ACKNOWLEDGEMENT:
        print(
            f"Entrainement refuse. Utilisez --acknowledge {ACKNOWLEDGEMENT} ",
            "uniquement pour le bac a sable synthetique.", file=sys.stderr,
        )
        return 1
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.env_checker import check_env

        config_path = resolve(args.config)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config["scientific_policy"]["scientific_claims_allowed"]:
            raise ValueError("exploratory config cannot allow scientific claims")
        env = ExploratoryAssistEnv(config_path)
        check_env(env, warn=True)
        timesteps = args.timesteps or int(config["training"]["default_timesteps"])
        output = resolve(config["training_output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        agent = PPO(
            "MlpPolicy", env, verbose=1, seed=int(config["training"]["seed"]),
            tensorboard_log=str(output.parent / "tensorboard"), n_steps=256, batch_size=64,
        )
        agent.learn(total_timesteps=timesteps)
        agent.save(str(output))
        env.close()
        metadata = {
            "schema_version": 1,
            "status": "SOFTWARE_EXPLORATION_ONLY",
            "algorithm": "PPO",
            "timesteps": timesteps,
            "model": str(output) + ".zip",
            "scientific_claims_allowed": False,
            "replacement_required_after_v3": True,
        }
        resolve(str(output) + ".metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except (ImportError, OSError, KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Entrainement exploratoire impossible: {exc}", file=sys.stderr)
        return 2
    print(f"PPO exploratoire: {output}.zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
