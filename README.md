# Exosquelette d'assistance au repassage industriel

Simulation biomécanique et apprentissage par renforcement (RL) pour optimiser un exosquelette d'assistance du bras lors d'une tâche de repassage industriel.

> **Statut** : les résultats actuels sont *exploratoires* (une seule caméra, longueurs du bras supposées). Ils valident la chaîne logicielle de bout en bout, pas encore l'efficacité réelle d'un exosquelette.

## Pipeline

```text
Vidéo → Reconstruction   → OpenSim          → MuJoCo         → RL         → Blender
        du mouvement       Scale/IK/ID/SO     exosquelette     MyoAssist    avatar 3D animé
```

| Étape | État actuel |
|---|---|
| Reconstruction du mouvement | fait, exploratoire |
| OpenSim | modèle mis à l'échelle ; IK/ID/SO bloqués tant que le mouvement 3D n'est pas mesuré |
| MuJoCo (exosquelette passif/hybride, contrôleurs) | fait, exploratoire |
| RL (MyoAssist) | préparé, volontairement bloqué avant validation biomécanique |
| Blender | fait (limite connue : tronc rigide, seul le bras bouge) |

## Résultat de référence

`data/scenarios/pipeline_principal/` contient **le** scénario retenu, de la vidéo à l'animation Blender. Tout ce qui est dans `data/scenarios/essais/` sont des tentatives explorées puis mises de côté : documentées et conservées comme preuve méthodologique, mais pas le résultat final.

Livrables principaux (générés localement, non versionnés dans Git) :

- `blender_animation_review.mp4` : vidéo finale de l'avatar animé ;
- `motion_quality_v2.json`, `passive_optimization_report.json`, `closed_loop_report.json` : rapports sur le mouvement, l'optimisation et le contrôle.

## Organisation du dépôt

- `src/` : code du pipeline (reconstruction, OpenSim, MuJoCo, RL, Blender, acquisition)
- `scripts/` : lanceurs de bout en bout
- `config/` : paramètres des scénarios, de l'exosquelette et des contrôleurs
- `models/` : modèles OpenSim et MuJoCo
- `data/` : vidéos, résultats générés (`scenarios/`), sessions de capture (non versionné)
- `docs/` : documentation technique
- `tests/` : tests automatiques

## Reproduire le résultat principal

Windows 11, PowerShell, depuis la racine. Installation unique : `powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1`.

```powershell
# 1. Vidéo → mouvement lissé (data/videos/video1.mp4)
.\.venv310\Scripts\python.exe .\scripts\run_scenario.py --config config\scenarios\video1_v1.json --report-on-fail

# 2. Reconstruction V2, optimisation de l'exosquelette, contrôleurs MuJoCo, tests
powershell -ExecutionPolicy Bypass -File .\scripts\run_experimental_v2.ps1

# 3. Animation Blender (l'avatar femme.blend est hors dépôt), puis assemblage de la vidéo
$B = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"; $A = "C:\Users\youss\mpfb-data\femme.blend"
& $B --background $A --python src\blender\import_animation.py -- --mot data\scenarios\pipeline_principal\target_arm26_exploratory.mot
& $B --background $A --python src\blender\render_final_demo_video.py -- --output "$PWD\data\scenarios\pipeline_principal\blender_animation_review.mp4"
.\.venv310\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe -framerate 30 -i data\scenarios\pipeline_principal\blender_animation_review_frames\frame_%04d.png -c:v libx264 -pix_fmt yuv420p data\scenarios\pipeline_principal\blender_animation_review.mp4
```

## Aller plus loin

Détails techniques, choix de modélisation, limites et scénarios explorés : voir [docs/](docs/). Points d'entrée conseillés : [architecture](docs/architecture.md), [état de référence](docs/current_status.md), [scénario retenu](docs/scenarios/video1_v2.md).
