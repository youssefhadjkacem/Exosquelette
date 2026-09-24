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

- `data/scenarios/pipeline_principal/motion_constrained.csv` ;
- `data/scenarios/pipeline_principal/motion_quality_v2.json` ;
- `data/scenarios/pipeline_principal/motion_exploratory.trc`.
- `data/scenarios/pipeline_principal/target_arm26_exploratory.mot`.

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

## Retargeting Blender (avatar MPFB2, bras droit)

`src/blender/import_animation.py` importe `target_arm26_exploratory.mot` sur les os
`upperarm01.R` (épaule) et `lowerarm01.R` (coude) du rig `Human.rig`, avec :

- `r_shoulder_elev` → `rotation_euler[2]` (axe Z local), **signe inversé** ;
- `r_elbow_flex` → `rotation_euler[0]` (axe X local), signe inchangé ;
- remise à zéro de tout l'armature avant application (le reste du corps reste en pose neutre, sans donnée inventée).

Ce mapping a été validé empiriquement (calcul direct des positions monde du poignet dans `femme.blend`, pas seulement une lecture visuelle) : l'axe Z est bien celui qui balaie le bras dans le plan vertical, et le signe inversé fait correctement monter le bras quand `r_shoulder_elev` augmente.

**Limite constatée** : une comparaison image par image sur toute la séquence (8 instants répartis entre 0 et 36 s) contre `video1.mp4` montre que le rythme, l'amplitude et la direction du geste ne correspondent pas bien à la vidéo, malgré un mapping épaule/coude techniquement correct. Dans la vidéo, l'ouvrière est penchée en avant au niveau du buste et le fer reste bas, près de la planche, avec des allers-retours de faible amplitude. Dans le rendu, le buste reste rigide et vertical (aucune donnée de tronc dans arm26) et le bras seul doit couvrir toute l'amplitude du geste, ce qui produit de grands balayages qui ne ressemblent pas au mouvement réel.

Cette limite vient du modèle arm26 lui-même (2 DOF, pas de tronc), pas du mapping épaule/coude. Elle sera levée par le protocole V3 (deux caméras) uniquement si le modèle biomécanique retenu à ce moment-là inclut un degré de liberté de tronc ; sinon elle persistera même avec des angles épaule/coude mieux mesurés.

## Passage à une version validée

Il faudra remplacer les hypothèses par les mesures du sujet et obtenir une profondeur mesurée avec deux caméras calibrées ou une caméra RGB-D. Cette future acquisition pourra produire un véritable statut `PASS`.
