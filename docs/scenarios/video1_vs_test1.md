# Comparaison — `video1.mp4` et `test1.mp4`

## Objectif et méthode

Les deux vidéos ont été traitées avec MediaPipe Pose et exactement les mêmes paramètres : visibilité minimale de 0,5, interpolation maximale de 5 frames, filtre Butterworth d’ordre 4 à 6 Hz et seuil de variation des longueurs de 10 %.

La comparaison ne change pas les seuils après observation des résultats. Les côtés droit et gauche sont analysés séparément, car la visibilité est très différente dans `test1.mp4`.

## Caractéristiques des vidéos

| Caractéristique | `video1.mp4` | `test1.mp4` |
|---|---:|---:|
| Résolution | 720 × 1280 | 640 × 360 |
| Fréquence | 30 Hz | 25 Hz |
| Durée | 76,60 s | 32,16 s |
| Frames | 2 298 | 804 |
| Frames avec une pose | 2 170 (94,4 %) | 765 (95,1 %) |

Le taux global de détection de personne est légèrement meilleur dans `test1`, mais il ne suffit pas à évaluer la qualité d’un bras particulier.

## Comparaison du bras droit

| Mesure | `video1` | `test1` | Meilleur |
|---|---:|---:|---|
| Épaule manquante | 2,6 % | 3,4 % | `video1` |
| Coude manquant | 4,5 % | 80,8 % | `video1` |
| Poignet manquant | 4,3 % | 67,5 % | `video1` |
| CV épaule–coude | 33,1 % | 19,4 % | `test1` |
| CV coude–poignet | 40,0 % | 50,5 % | `video1` |

Pour le bras droit, `video1` est nettement préférable. Dans `test1`, la visibilité moyenne du coude droit n’est que de 0,295 et celle du poignet de 0,432. Ce bras est vraisemblablement occulté, hors champ ou opposé à la caméra pendant une grande partie du geste.

## Comparaison du bras gauche

| Mesure | `video1` | `test1` | Meilleur |
|---|---:|---:|---|
| Épaule manquante | 2,6 % | 3,4 % | `video1` |
| Coude manquant | 19,1 % | 3,4 % | `test1` |
| Poignet manquant | 18,5 % | 3,4 % | `test1` |
| CV épaule–coude | 33,3 % | 14,8 % | `test1` |
| CV coude–poignet | 33,1 % | 24,0 % | `test1` |

Pour le bras gauche, `test1` est nettement préférable et se rapproche davantage des seuils. Elle reste néanmoins en `FAIL` : 3,4 % de données manquantes et des variations de longueur supérieures au seuil de 10 %.

## Verdict

- La vérification visuelle confirme que le fer est tenu par le **bras droit anatomique** dans les deux vidéos.
- Le bras fonctionnel retenu pour l’étude est donc le bras droit, indépendamment de la dominance déclarée du sujet.
- Pour ce bras, conserver `video1` comme meilleure référence actuelle.
- `test1` reste utile pour la comparaison, mais son coude et son poignet droits sont trop souvent occultés.
- Aucune des deux vidéos ne permet encore une analyse OpenSim quantitative validée.

La différence entre les côtés montre que l’orientation de la caméra et les occultations influencent fortement les résultats. Pour la prochaine capture, placer la caméra du côté du bras étudié, garder épaule, coude et poignet visibles, et ajouter une deuxième caméra ou un capteur RGB-D.

## Reproduction

```powershell
# Rejouer test1
.\.venv310\Scripts\python.exe .\scripts\run_scenario.py `
  --config config\scenarios\test1_v1.json

# Produire la comparaison JSON après les quatre validations droite/gauche
.\.venv310\Scripts\python.exe .\scripts\compare_motion_reports.py
```

Le rapport généré est `data/scenarios/video1_vs_test1/comparison.json`.
