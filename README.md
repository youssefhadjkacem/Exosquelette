# Exosquelette

Projet de modélisation et d'analyse pour un exosquelette / bras assisté.
Utilise MuJoCo pour la simulation physique, OpenSim pour la biomécanique, et Stable Baselines 3 pour l'apprentissage par renforcement (PPO).

## Structure du dépôt

```
.
├── src/                          # Scripts Python principaux
│   ├── convert_to_trc.py        # Convertir données motion capture en format TRC (OpenSim)
│   ├── exo_env.py               # Environnement Gymnasium pour simulation MuJoCo
│   ├── export_animation.py      # Exporter animation du modèle entraîné en JSON
│   ├── extract_motion.py        # Extraire pose landmarks vidéo via MediaPipe
│   ├── smooth_motion.py         # Lisser données de motion capture
│   ├── test_scale.py            # Calculer facteur d'échelle anatomique
│   └── train_myoassist.py       # Entraîner agent PPO sur l'environnement
├── tests/                        # Tests et scripts de validation
├── data/                         # Données (fichiers volumineux excluS)
│   ├── opensim/                 # Fichiers OpenSim et résultats associés
│   ├── motion_data*.csv         # Données de motion capture
│   └── videos/                  # ⚠️ Stocké externellement (voir section Fichiers volumineux)
├── models/                       # Modèles de simulation et entraînement
│   ├── mujoco/
│   │   ├── v1/                  # Version 1 du modèle MuJoCo
│   │   └── v2/                  # Version 2 du modèle MuJoCo
│   └── myoassist/               # Modèles PPO entraînés
├── resources/                    # Ressources externes (fichiers volumineux exclus)
│   └── mobl_arms/               # ⚠️ Stocké externalement (voir section Fichiers volumineux)
├── requirements.txt             # Dépendances Python (pip)
├── environment.yml              # Environnement Conda
└── README.md                    # Ce fichier
```

## Installation

### Option 1 : Avec pip et virtualenv

```bash
python -m venv myoconv_env_py38
myoconv_env_py38\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Option 2 : Avec Conda

```bash
conda env create -f environment.yml
conda activate myoconv_env
```

## Dépendances principales

- **MuJoCo** 2.3.7 : moteur de simulation physique
- **OpenSim** 4.5 : modélisation biomécanique
- **Stable Baselines 3** : apprentissage par renforcement (PPO)
- **MediaPipe** : détection de pose
- **NumPy**, **SciPy**, **Pandas** : calcul scientifique
- **PyOpenGL**, **VTK** : visualisation 3D

Voir `requirements.txt` pour la liste complète.

## Utilisation

### Exécuter les scripts

Tous les scripts utilisent des chemins relatifs au PROJECT_ROOT :

```bash
cd src
python extract_motion.py      # Extraire pose vidéo
python smooth_motion.py       # Lisser données
python convert_to_trc.py      # Convertir en format OpenSim
python test_scale.py          # Calculer échelle
python train_myoassist.py     # Entraîner agent PPO
python export_animation.py    # Exporter animation
```

### Structure de données

- **Entrée vidéo** : `data/videos/video1.mp4`
- **Données motion** : `data/motion_data.csv` → `data/motion_data_smoothed.csv`
- **Format OpenSim** : `data/motion_data.trc`
- **Animation JSON** : `data/animation_data.json`
- **Modèles MuJoCo** : `models/mujoco/v2/arm26_scaled_cvt3.xml`
- **Modèle PPO** : `models/myoassist/myoassist_trained`

## Notes

- Ne pas versionner `myoconv_env_py38/` (environnement virtuel)
- Tous les chemins de fichiers sont relatifs au PROJECT_ROOT pour portabilité cross-plateforme
- Le `.gitignore` exclut les fichiers volumineux (.mp4, .vtp) et les caches Python
