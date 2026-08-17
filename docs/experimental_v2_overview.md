# Parcours expérimental V2 simplifié

## But de cette branche

Le parcours V2 permet de continuer le développement avec la vidéo monoculaire actuelle sans confondre démonstration logicielle et validation biomécanique.

Il regroupe :

```text
video1, bras droit tenant le fer
        ↓
reconstruction planaire contrainte
        ↓
cible articulaire arm26
        ↓
optimisation des ressorts
        ↓
modèles passif et hybride
        ↓
contrôleur classique prescrit
        ↓
contrôleur dynamique en boucle fermée
```

## Exécution en une commande

Depuis la racine du projet :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_experimental_v2.ps1
```

Le script s’arrête immédiatement si une étape ou un test échoue.

## Résultats de référence actuels

| Étape | Statut |
|---|---|
| Reconstruction V2 | `EXPLORATORY_PASS` |
| Géométrie du mouvement | `PASS` |
| Cinématique filtrée | `PASS` |
| Modèle hybride MuJoCo | `PASS` structurel |
| Optimisation passive | `EXPLORATORY_PASS` |
| Contrôleur classique prescrit | `EXPLORATORY_PASS` |
| Contrôleur dynamique fermé | `EXPLORATORY_PASS` |
| OpenSim quantitatif | bloqué |
| RL scientifique | bloqué |

## Configurations principales

| Fichier | Rôle |
|---|---|
| `config/scenarios/video1_v2.json` | mouvement, anthropométrie supposée et conversion articulaire |
| `config/exoskeleton/hybrid_optimized_v2.json` | ressorts, masses et moteurs optimisés |
| `config/controllers/passive_optimization_v1.json` | espace de recherche des ressorts |
| `config/controllers/classical_assistance_optimized_v2.json` | comparaison en cinématique prescrite |
| `config/controllers/closed_loop_v1.json` | gains et limites de la boucle dynamique |

## Modèles principaux

- `models/mujoco/exoskeleton/light_passive_optimized_v2.xml` ;
- `models/mujoco/exoskeleton/hybrid_optimized_v2.xml`.

## Résultats principaux

Les fichiers générés sont placés dans `data/scenarios/video1_v2/` et restent exclus de Git :

- `motion_quality_v2.json` ;
- `target_arm26_mapping.json` ;
- `passive_optimization_report.json` ;
- `classical_assistance_optimized_report.json` ;
- `closed_loop_report.json`.

## Interprétation

La variante hybride fermée suit la trajectoire avec environ 0,16° d’erreur RMS à l’épaule et 0,26° au coude. Le proxy de couple humain diminue d’environ 38,6 % et 58,7 %.

Ces nombres reposent sur une trajectoire monoculaire, des longueurs anthropométriques supposées et des couples humains idéaux. Ils servent à valider le logiciel, pas à conclure sur la fatigue ou l’efficacité réelle d’un exosquelette.

## Passage à la validation

Lorsque de nouvelles vidéos calibrées seront disponibles, le pipeline V1 pourra être relancé indépendamment. Si le mouvement obtient un véritable `PASS`, les données exploratoires V2 seront remplacées avant OpenSim et le RL scientifique.
