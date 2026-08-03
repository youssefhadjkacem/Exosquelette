import myosuite
import gymnasium as gym

# Modèle bras complet
env = gym.make('myoArmReachFixed-v0')
obs, info = env.reset()

print("Observation space:", env.observation_space.shape)
print("Action space:", env.action_space.shape)
print("Nombre de muscles:", env.action_space.shape[0])

for i in range(50):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()
    print(f"Step {i} - Reward: {reward:.3f}")

env.close()
print("Test bras complet réussi !")