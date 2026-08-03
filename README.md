# Exosquelette

Projet de modélisation et d'analyse pour un exosquelette / bras assisté.

## Structure du dépôt

- `src/` : scripts Python principaux
- `tests/` : tests et scripts de validation
- `data/` : jeux de données
  - `opensim/` : fichiers OpenSim et résultats associés
  - `videos/` : vidéos de démonstration
- `models/` : modèles de simulation et répertoires MuJoCo
  - `models/mujoco/v1/`
  - `models/mujoco/v2/`
  - `models/myoassist/`
- `resources/` : ressources externes et modèles tiers
  - `resources/mobl_arms/`

## Utilisation

- Exécuter les scripts depuis `src/`.
- Les fichiers de données sont dans `data/`.
- Les modèles MuJoCo sont dans `models/mujoco/`.

## Conseils

- Ne pas versionner `myoconv_env_py38/`.
- Ajouter un environnement Python virtuel propre si nécessaire.
