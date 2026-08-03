import mujoco
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class BrasOuvriereEnv(gym.Env):
    """
    Environnement MuJoCo personnalisé pour simuler
    le bras de l'ouvrière avec l'exosquelette
    """
    
    def __init__(self):
        super(BrasOuvriereEnv, self).__init__()
        
        # Charger notre modèle converti depuis OpenSim
        self.model = mujoco.MjModel.from_xml_path(
            str(PROJECT_ROOT / 'models' / 'mujoco' / 'v2' / 'mujoco_models_v2' / 'arm26_scaled_cvt3.xml')
        )
        self.data = mujoco.MjData(self.model)
        
        # Espace d'observation : état du bras
        # (positions + vitesses des 2 articulations)
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.model.nq + self.model.nv,),
            dtype=np.float32
        )
        
        # Espace d'action : force d'assistance de l'exosquelette
        # (une valeur par muscle : 0 = pas d'assistance, 1 = assistance max)
        self.action_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(self.model.nu,),
            dtype=np.float32
        )
        
        self.max_steps = 500
        self.current_step = 0
        
        print(f"✅ Environnement créé !")
        print(f"   Observations : {self.observation_space.shape}")
        print(f"   Actions (muscles) : {self.action_space.shape}")
    
    def reset(self, seed=None, options=None):
        """Réinitialiser l'environnement"""
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.current_step = 0
        obs = self._get_observation()
        return obs, {}
    
    def step(self, action):
        """Effectuer une action (assistance de l'exosquelette)"""
        
        # Appliquer l'assistance de l'exosquelette
        self.data.ctrl[:] = action
        
        # Simuler 1 step physique
        mujoco.mj_step(self.model, self.data)
        self.current_step += 1
        
        # Observer le nouvel état
        obs = self._get_observation()
        
        # Calculer la récompense
        reward = self._calculate_reward(action)
        
        # Vérifier si l'épisode est terminé
        terminated = self.current_step >= self.max_steps
        truncated = False
        
        return obs, reward, terminated, truncated, {}
    
    def _get_observation(self):
        """Obtenir l'état actuel du bras"""
        return np.concatenate([
            self.data.qpos,  # angles des articulations
            self.data.qvel   # vitesses des articulations
        ]).astype(np.float32)
    
    def _calculate_reward(self, action):
        """
        Calculer la récompense :
        + bonne assistance = récompense positive
        - trop de force = pénalité (inconfort)
        - pas assez = pénalité (fatigue)
        """
        
        # Fatigue musculaire (vitesse élevée = effort élevé)
        fatigue = np.sum(np.abs(self.data.qvel))
        
        # Pénalité si assistance trop forte (inconfort)
        inconfort = np.sum(action ** 2) * 0.1
        
        # Récompense = réduire la fatigue sans causer d'inconfort
        reward = -fatigue - inconfort
        
        return float(reward)