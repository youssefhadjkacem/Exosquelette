# Contrôleur classique d’assistance V1

## Objectif

Cette étape construit une référence simple avant tout RL. Elle compare trois conditions sur exactement la même trajectoire V2 :

1. bras humain sans exosquelette ;
2. exosquelette passif avec ressorts ;
3. exosquelette hybride avec assistance classique limitée.

Le contrôleur hybride fournit 35 % du couple articulaire requis, dans la limite de ±5 N·m à l’épaule et ±3 N·m au coude. Le reste est comptabilisé comme couple humain résiduel.

## Conversion de la trajectoire

Le fichier V2 est converti vers les coordonnées du modèle :

```text
r_shoulder_elev = -(angle_image_epaule + 90°)
r_elbow_flex    = angle_filtre_du_coude
```

La cible obtenue couvre :

- épaule : −43,5° à 70,7°, sans écrêtage ;
- coude : 21,7° à 130,0°, avec 0,5 % des frames écrêtées à la limite du modèle.

Cette convention suppose que la verticale de l’image correspond à la référence d’élévation du modèle. Elle reste exploratoire tant qu’une calibration caméra–modèle n’est pas disponible.

## Exécution

```powershell
# Pipeline V2 et cible MOT
.\.venv310\Scripts\python.exe .\scripts\run_motion_v2.py

# Comparaison de l’assistance
.\.venv310\Scripts\python.exe .\src\mujoco\evaluate_classical_assistance.py `
  --config config\controllers\classical_assistance_v1.json
```

## Résultats exploratoires

| Condition | Épaule RMS | Coude RMS | Réduction épaule | Réduction coude |
|---|---:|---:|---:|---:|
| Sans assistance | 7,633 N·m | 3,028 N·m | référence | référence |
| Passive V1 | 8,496 N·m | 3,160 N·m | −11,3 % | −4,3 % |
| Hybride classique | 5,580 N·m | 2,054 N·m | +26,9 % | +32,2 % |

Le réglage passif actuel augmente l’effort estimé. Cela ne signifie pas qu’un produit passif est inefficace : les ressorts, précharges, masses et points d’attache de notre prototype sont encore hypothétiques et non optimisés.

Le contrôleur hybride réduit le proxy de couple humain dans cette expérience prescrite. Le moteur d’épaule atteint sa limite pendant environ 5,0 % des frames ; celui du coude ne sature pas.

## Problème de contact découvert

Les maillages issus de la conversion créent des contacts internes artificiels pouvant dépasser 1 000 N·m. Ils ne correspondent pas à un effort humain réel. L’évaluation articulaire calcule donc explicitement :

```text
couple requis = M(q) q̈ + biais − forces passives
```

et exclut les réactions de contact des maillages. Le rapport conserve leur maximum comme diagnostic. Avant une simulation physique avec contacts, il faudra définir des groupes de collision ou simplifier les géométries.

## Limites

- La trajectoire est imposée, pas suivie dans une simulation dynamique fermée.
- Le couple humain résiduel n’est pas une activation musculaire.
- Les angles proviennent de la reconstruction monoculaire exploratoire.
- Les valeurs mécaniques de l’exosquelette ne proviennent pas d’un fabricant.

Ces résultats servent uniquement à vérifier l’architecture du contrôleur et à définir une baseline pour les étapes suivantes.

Une seconde configuration utilisant les ressorts optimisés est documentée dans `docs/passive_optimization_v1.md`. Elle atteint des réductions exploratoires de 38,7 % à l’épaule et 59,0 % au coude pour la condition hybride classique.

## Prochaine étape

La priorité est d’optimiser les ressorts et leur précharge afin que la condition passive réduise réellement le couple au lieu de l’augmenter. Ensuite, le contrôleur classique devra être testé en boucle fermée avant toute comparaison avec PPO.
