# Pipeline biomécanique pour exosquelette de repassage

Ce dépôt construit un pipeline reproductible pour étudier l’assistance du membre supérieur pendant le repassage industriel. Il sépare explicitement :

1. la capture et la reconstruction du mouvement ;
2. la validation biomécanique OpenSim ;
3. la simulation MuJoCo ;
4. l’optimisation d’une assistance passive ou, plus tard, le contrôle RL d’un exosquelette actif ;
5. la visualisation du jumeau numérique.

Le modèle `arm26` et les résultats historiques restent disponibles pour comparaison. Ils ne sont pas considérés comme validés pour un geste 3D bimanuel.

## Principe de sécurité scientifique

Chaque phase produit un rapport `PASS` ou `FAIL`. Un résultat `FAIL` bloque la phase suivante :

```text
Vidéo → CSV canonique → lissage → qualité mouvement
                                      │ PASS
                                      ▼
Calibration → TRC → OpenSim IK/ID/SO → qualité OpenSim
                                               │ PASS
                                               ▼
Modèle humain + actionneurs exo_* → readiness RL → PPO
```

Les options `--allow-*` servent uniquement aux démonstrations exploratoires. Elles ne rendent pas les résultats biomécaniquement valides.

## Installation Windows 11

Prérequis : Python 3.10, Python 3.8, Git et OpenSim 4.5.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

Le script crée :

- `.venv310` pour MediaPipe, MuJoCo, MyoSuite et Stable-Baselines3 ;
- `.venv38` pour OpenSim et MyoConverter.

Voir [docs/windows_setup.md](docs/windows_setup.md) pour les détails et le dépannage.

## Parcours minimal

Pour reproduire directement la première analyse complète de `video1.mp4`, voir [le scénario V1](docs/scenarios/video1_v1.md) et lancer :

```powershell
.\.venv310\Scripts\python.exe .\scripts\run_scenario.py `
  --config config\scenarios\video1_v1.json
```

Ce scénario s'arrête volontairement avant OpenSim si la qualité du mouvement obtient `FAIL`.

### 1. Extraction

```powershell
.\.venv310\Scripts\python.exe .\src\extract_motion.py `
  --video data\videos\video1.mp4 `
  --output data\motion_data_v2.csv
```

Toutes les frames sont conservées, y compris celles sans pose. `--show` active l’aperçu graphique.

### 2. Lissage sans compression temporelle

```powershell
.\.venv310\Scripts\python.exe .\src\smooth_motion.py `
  --input data\motion_data_v2.csv `
  --output data\motion_data_smoothed.csv `
  --cutoff-hz 6 `
  --max-gap-frames 5
```

### 3. Qualité du mouvement

```powershell
.\.venv310\Scripts\python.exe .\src\validate_motion.py `
  --required-markers r_shoulder,r_elbow,r_wrist
```

Le rapport est écrit dans `data/results/motion_quality.json`. Le code de sortie vaut `1` si les seuils échouent.

### 4. Calibration et TRC

Copier `config/calibration.example.json` vers `config/calibration.json`, renseigner la calibration réelle et définir `analysis_valid` à `true` uniquement après validation.

```powershell
Copy-Item .\config\calibration.example.json .\config\calibration.json
.\.venv310\Scripts\python.exe .\src\convert_to_trc.py
```

### 5. OpenSim

```powershell
$env:OPENSIM_HOME = "C:\OpenSim 4.5"
.\.venv38\Scripts\python.exe .\src\opensim\run_analysis.py
```

L’IK seule peut être exécutée sans force externe. Dans ce cas d’usage, ID et SO nécessitent un fichier de charges du fer et de la table :

```powershell
.\.venv38\Scripts\python.exe .\src\opensim\run_analysis.py `
  --id --so --external-loads config\opensim\external_loads.xml
```

Valider ensuite les résultats :

```powershell
.\.venv38\Scripts\python.exe .\src\opensim\validate_results.py `
  --marker-errors data\results\opensim\ironing_inverse_kinematics_marker_errors.sto `
  --activations data\results\opensim\ironing_static_optimization_StaticOptimization_activation.sto
```

### 6. RL, uniquement pour un exosquelette actif

Le modèle MuJoCo doit contenir des moteurs distincts nommés `exo_*`. Les muscles humains ne sont jamais les actions de l’agent.

Pour reproduire la migration technique de l’ancien XML vers MuJoCo 3.6 :

```powershell
.\.venv310\Scripts\python.exe .\src\mujoco\migrate_xml.py `
  --input models\mujoco\v2\mujoco_models_v2\arm26_scaled_cvt3.xml `
  --output models\mujoco\v2\mujoco_models_v2\arm26_scaled_cvt3_mujoco36.xml
```

```powershell
.\.venv310\Scripts\python.exe .\src\validate_rl_readiness.py `
  --model models\mujoco\active_exoskeleton.xml

.\.venv310\Scripts\python.exe .\src\train_myoassist.py `
  --model models\mujoco\active_exoskeleton.xml `
  --human-controls data\results\opensim\so_activation.sto
```

Si le dispositif choisi est passif, ne pas utiliser PPO. Optimiser ses ressorts, sa précharge et sa courbe de couple selon [docs/rl_protocol.md](docs/rl_protocol.md).

## Documentation

- [Architecture et périmètre](docs/architecture.md)
- [Contrat des données](docs/data_contract.md)
- [Calibration et validation biomécanique](docs/biomechanics_validation.md)
- [Protocole assistance passive/RL](docs/rl_protocol.md)
- [Installation Windows](docs/windows_setup.md)
- [Plan d’exécution](docs/roadmap.md)
- [État de référence et résultats historiques](docs/current_status.md)
- [Scénario reproductible `video1_v1`](docs/scenarios/video1_v1.md)
- [Comparaison de `video1` et `test1`](docs/scenarios/video1_vs_test1.md)
- [Sélection du modèle d’exosquelette](docs/exoskeleton_model_selection.md)
- [Prototype MuJoCo hybride V1](docs/hybrid_exoskeleton_v1.md)

## État actuel

- Le XML `arm26_scaled_cvt3.xml` a été historiquement validé sous MuJoCo 2.3.7 et doit être revalidé sous la version 3.6.0 requise par MyoSuite 2.12.2.
- Il ne comporte que deux DDL, six muscles et aucun actionneur d’exosquelette. L’artefact migré MuJoCo 3.6 active les limites, mais reste volontairement bloqué pour le RL.
- Les données historiques échouent aux critères de rigidité segmentaire et de chronologie.
- Un modèle 3D, une calibration métrique et des forces externes doivent être fournis avant de considérer ID/SO ou RL comme validés.
