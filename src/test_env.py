from exo_env import BrasOuvriereEnv
import numpy as np

# Créer l'environnement
env = BrasOuvriereEnv()

# Tester avec des actions aléatoires
obs, info = env.reset()
print(f"\n🔍 Observation initiale : {obs}")

for i in range(10):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    print(f"Step {i+1} - Reward: {reward:.3f}")

print("\n✅ Test de l'environnement réussi !")