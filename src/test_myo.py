import myosuite
import gymnasium as gym

env = gym.make('myoHandPoseFixed-v0')
obs, info = env.reset()

for i in range(100):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()
    print(f"Step {i} - Reward: {reward:.3f}")

env.close()
print("Test réussi !")