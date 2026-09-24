# Scénario V1 — `video_principale.mp4`

## 1. Objectif

Cette première version transforme `data/videos/video_principale.mp4` en une expérience reproductible. Elle sert à vérifier la capture du mouvement avant toute interprétation biomécanique, simulation d’exosquelette ou utilisation du RL.

Le geste est identifié comme un geste de repassage. La vérification visuelle confirme que le fer est tenu par le bras droit anatomique, qui devient le bras fonctionnel étudié. La V1 ne prétend pas encore estimer correctement les efforts musculaires ni la fatigue.

## 2. Données d’entrée

| Élément | Valeur V1 |
|---|---:|
| Vidéo | `data/videos/video_principale.mp4` |
| Résolution | 720 × 1280 |
| Fréquence | 30 Hz |
| Nombre d’images | 2 298 |
| Durée | 76,6 s |
| Caméras | 1 |
| Côté analysé | droit |
| Calibration métrique | absente |
| Anthropométrie du sujet | absente |
| Forces externes | absentes |

La configuration versionnée se trouve dans `config/scenarios/video1_v1.json`.

## 3. Exécution reproductible

Depuis la racine du projet :

```powershell
.\.venv310\Scripts\python.exe .\scripts\run_scenario.py `
  --config config\scenarios\video1_v1.json
```

Après une première extraction, la version rapide réutilise le CSV brut :

```powershell
.\.venv310\Scripts\python.exe .\scripts\run_scenario.py `
  --config config\scenarios\video1_v1.json `
  --skip-extraction
```

Le code de sortie vaut `1` lorsque le contrôle qualité échoue. C’est le comportement attendu d’un garde-fou, même si tous les fichiers et rapports ont été produits.

## 4. Étapes réalisées

```text
video_principale.mp4
   ↓ MediaPipe Pose, toutes les images conservées
motion_raw.csv
   ↓ visibilité, interpolation courte, filtre Butterworth 6 Hz
motion_smoothed.csv
   ↓ contrôle des lacunes, valeurs manquantes et rigidité des segments
motion_quality.json
   ↓
PASS : calibration métrique puis OpenSim
FAIL : correction de la capture avant de continuer
```

Les artefacts générés sont isolés dans `data/scenarios/scenarios_secondaires/video_principale_methode_v1/`.

## 5. Résultat obtenu le 17 août 2026

L’extraction détecte une pose dans 2 170 images sur 2 298, soit 94,4 %. Le lissage produit 1 801 images entièrement valides. La chronologie est désormais correcte : aucune image n’est supprimée, la plage reste 0–2297 et le temps est monotone à 30 Hz.

Le statut final est néanmoins `FAIL` :

| Contrôle | Résultat | Seuil | Décision |
|---|---:|---:|---|
| Données manquantes épaule droite | 2,6 % | ≤ 2 % | FAIL |
| Données manquantes coude droit | 4,5 % | ≤ 2 % | FAIL |
| Données manquantes poignet droit | 4,3 % | ≤ 2 % | FAIL |
| CV longueur épaule–coude | 33,1 % | ≤ 10 % | FAIL |
| CV longueur coude–poignet | 40,0 % | ≤ 10 % | FAIL |
| Lacunes dans la chronologie finale | 0 | 0 | PASS |

La variation des longueurs est le problème principal. Les os humains étant rigides, ces variations montrent que la reconstruction monoculaire MediaPipe n’est pas suffisamment métrique pour une analyse OpenSim quantitative.

## 6. Décision scientifique V1

La vidéo reste utile pour :

- démontrer le pipeline logiciel ;
- visualiser qualitativement le geste ;
- tester la conservation du temps et les rapports automatiques ;
- préparer le modèle de scénario suivant.

Elle ne doit pas encore être utilisée pour :

- calculer des moments articulaires validés ;
- conclure sur les activations ou la fatigue musculaire ;
- entraîner un agent RL présenté comme biomécaniquement optimal.

Une conversion TRC avec `--allow-unvalidated-calibration` serait seulement exploratoire. Elle n’est donc pas incluse dans l’exécution normale du scénario.

## 7. Passage vers OpenSim

OpenSim sera débloqué lorsque `motion_quality.json` indiquera `PASS`. Il faudra ensuite :

1. renseigner les dimensions épaule–coude et coude–poignet du sujet ;
2. fournir une reconstruction métrique par caméra RGB-D ou deux caméras calibrées ;
3. créer `config/calibration.json` avec `analysis_valid: true` ;
4. produire le TRC ;
5. adapter `arm26_scaled.osim` au sujet ;
6. exécuter l’IK et contrôler la RMS des marqueurs ;
7. mesurer les charges externes avant ID et SO.

## 8. Scénario d’assistance prévu

La première assistance à comparer ciblera le coude droit :

1. condition sans assistance ;
2. assistance passive de type ressort ;
3. assistance active avec contrôleur classique ;
4. assistance active pilotée par PPO, uniquement après validation des trois précédentes.

Le modèle MuJoCo devra comporter un moteur `exo_elbow_motor`, des limites articulaires et une plage de couple explicite. Le RL ne commandera jamais directement les muscles humains.

## 9. Critère de fin de la V1

La V1 est terminée lorsque l’extraction et le rapport sont reproductibles. Elle est actuellement **terminée mais bloquée au contrôle du mouvement**. La V2 doit améliorer la mesure, et non contourner les seuils.
