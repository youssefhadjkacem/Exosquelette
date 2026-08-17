"""Smoke-test an active-exoskeleton environment after readiness validation."""

import argparse

from exo_env import BrasOuvriereEnv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--human-controls", default=None)
    args = parser.parse_args()
    env = BrasOuvriereEnv(args.model, args.target, args.human_controls)
    observation, _ = env.reset(seed=42)
    for _ in range(10):
        observation, reward, terminated, truncated, info = env.step(env.action_space.sample())
        if terminated or truncated:
            break
    env.close()
    print(f"Test environnement OK; observation={observation.shape}, reward={reward:.6f}, info={info}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
