# Pipeline mouvement V2 — `video1`

## Objectif

La V2 produit une trajectoire cohérente du bras droit qui tient le fer, tout en conservant une distinction stricte entre cohérence géométrique et mesure 3D réelle.

La V1 utilisait directement la profondeur MediaPipe. Elle échouait parce que les longueurs apparentes variaient de 33,1 % pour le bras et de 40,0 % pour l’avant-bras.

## Fenêtre analysée

La revue visuelle de la vidéo distingue :

- frames 0–1080, soit environ 36 secondes : phase continue de repassage ;
- suite de la vidéo : manipulation et repositionnement principal du vêtement.

La V2 conserve seulement la première fenêtre. Ce choix est enregistré dans `config/scenarios/video1_v2.json`.

## Reconstruction

Le pipeline utilise :

- le bras droit anatomique, confirmé comme bras tenant le fer ;
- 30 cm entre l’épaule et le coude ;
- 25 cm entre le coude et le poignet ;
- l’orientation 2D pour l’angle de l’épaule ;
- l’angle 3D MediaPipe filtré pour estimer la flexion du coude ;
- un filtre angulaire Butterworth à 2 Hz ;
- une reconstruction finale dans le plan de la caméra avec `z=0`.

Les longueurs et la stature sont des hypothèses anthropométriques, pas des mesures du sujet.

## Exécution

```powershell
.\.venv310\Scripts\python.exe .\scripts\run_motion_v2.py `
  --config config\scenarios\video1_v2.json
```

Cette commande produit :

- `data/scenarios/video1_v2/motion_constrained.csv` ;
- `data/scenarios/video1_v2/motion_quality_v2.json` ;
- `data/scenarios/video1_v2/motion_exploratory.trc`.
- `data/scenarios/video1_v2/target_arm26_exploratory.mot`.

## Résultats

| Contrôle | Résultat V2 |
|---|---:|
| Frames | 1 081 |
| Frames valides | 1 081 |
| Données manquantes | 0 % |
| Longueur épaule–coude | 0,30 m constante |
| Longueur coude–poignet | 0,25 m constante |
| Vitesse épaule P95 | 187,6°/s |
| Accélération épaule P95 | 1 266,6°/s² |
| Vitesse coude P95 | 243,7°/s |
| Accélération coude P95 | 1 872,4°/s² |
| Qualité géométrique | PASS |
| Qualité cinématique | PASS |
| Statut scientifique | EXPLORATORY_PASS |

## Pourquoi le statut n’est pas `PASS`

Les longueurs constantes sont imposées par l’algorithme. Elles montrent que le calcul fonctionne, mais ne prouvent pas que la trajectoire 3D réelle a été mesurée.

La V2 reste exploratoire parce que :

1. une seule caméra est utilisée ;
2. la profondeur réelle n’est pas mesurée ;
3. les longueurs anatomiques sont supposées ;
4. le mouvement final est contraint au plan de la caméra.

Le rapport porte donc le statut `EXPLORATORY_PASS`. Le garde-fou OpenSim exige exactement `PASS` et refusera ce rapport pour une analyse quantitative.

## Utilisation autorisée

La V2 peut servir à tester le suivi de trajectoire MuJoCo, développer le contrôleur classique, visualiser les angles et vérifier l’intégration logicielle du futur RL.

Elle ne peut pas encore servir à conclure sur les moments articulaires, les activations musculaires, la fatigue de l’opératrice ou l’efficacité industrielle de l’exosquelette.

## Passage à une version validée

Il faudra remplacer les hypothèses par les mesures du sujet et obtenir une profondeur mesurée avec deux caméras calibrées ou une caméra RGB-D. Cette future acquisition pourra produire un véritable statut `PASS`.
