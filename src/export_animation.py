import mujoco
import numpy as np
import json
from pathlib import Path
from stable_baselines3 import PPO

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Charger le modèle MuJoCo
model = mujoco.MjModel.from_xml_path(
    str(PROJECT_ROOT / 'models' / 'mujoco' / 'v2' / 'mujoco_models_v2' / 'arm26_scaled_cvt3.xml')
)
data = mujoco.MjData(model)

# Charger MyoAssist entraîné
agent = PPO.load(
    str(PROJECT_ROOT / 'models' / 'myoassist' / 'myoassist_trained')
)

# Réinitialiser
mujoco.mj_resetData(model, data)

# Enregistrer les positions à chaque step
animation_data = []

obs = np.concatenate([data.qpos, data.qvel]).astype(np.float32)

for step in range(500):
    # MyoAssist décide de l'assistance
    action, _ = agent.predict(obs, deterministic=True)
    
    # Appliquer et simuler
    data.ctrl[:] = action
    mujoco.mj_step(model, data)
    
    # Récupérer les positions du bras
    shoulder_angle = float(data.qpos[0])  # épaule en radians
    elbow_angle = float(data.qpos[1])     # coude en radians
    
    # Sauvegarder
    animation_data.append({
        "step": step,
        "time": float(data.time),
        "shoulder_angle_deg": float(np.degrees(shoulder_angle)),
        "elbow_angle_deg": float(np.degrees(elbow_angle)),
        "shoulder_angle_rad": shoulder_angle,
        "elbow_angle_rad": elbow_angle,
        "muscle_activation": action.tolist()
    })
    
    obs = np.concatenate([data.qpos, data.qvel]).astype(np.float32)

# Sauvegarder en JSON
output_path = PROJECT_ROOT / 'data' / 'animation_data.json'
with open(output_path, 'w') as f:
    json.dump(animation_data, f, indent=2)

print(f" Animation exportée : {len(animation_data)} frames")
print(f" Fichier : {output_path}")