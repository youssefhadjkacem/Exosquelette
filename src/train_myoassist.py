from pathlib import Path
from exo_env import BrasOuvriereEnv
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARTIE 1 : Créer l'environnement
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# On charge notre modèle MuJoCo (converti depuis OpenSim)
# C'est le "terrain d'entraînement" de MyoAssist
env = BrasOuvriereEnv()

# Vérifier que l'environnement est bien configuré
# (gymnasium vérifie que les espaces d'action/observation sont corrects)
print("🔍 Vérification de l'environnement...")
check_env(env)
print("✅ Environnement valide !")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARTIE 2 : Créer MyoAssist (l'agent IA)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━
save_dir = PROJECT_ROOT / 'models' / 'myoassist'
os.makedirs(save_dir, exist_ok=True)

# PPO = l'algorithme d'apprentissage
# MlpPolicy = réseau de neurones classique
# (Multi-Layer Perceptron = plusieurs couches de neurones)
agent = PPO(
    "MlpPolicy",      # Type de réseau de neurones
    env,              # Notre environnement MuJoCo
    verbose=1,        # Afficher les progrès pendant l'entraînement
    learning_rate=3e-4,  # Vitesse d'apprentissage (0.0003)
    n_steps=2048,     # Steps avant chaque mise à jour
    batch_size=64,    # Taille des mini-batches
    n_epochs=10,      # Répétitions par mise à jour
    tensorboard_log=save_dir  # Sauvegarder les logs
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARTIE 3 : Entraîner MyoAssist
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# total_timesteps = nombre total d'essais
# 100 000 = environ 10 minutes sur votre PC
print("\n🏋️ Début de l'entraînement...")
agent.learn(total_timesteps=100_000)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARTIE 4 : Sauvegarder MyoAssist
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Sauvegarder le "cerveau" de MyoAssist
# sous forme de fichier .zip
agent.save(save_dir / "myoassist_trained")
print(f"\n✅ MyoAssist entraîné et sauvegardé !")