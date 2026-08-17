# État de référence du dépôt

Ce document distingue les artefacts historiques des résultats validés par le nouveau pipeline.

## Données historiques

`data/motion_data.csv` contient 2 170 poses pour une plage de frames 0–2297 :

- 37 événements de lacune ;
- 128 frames manquantes ;
- lacune maximale de 18 frames ;
- CV épaule–coude de 33,6 % ;
- CV coude–poignet de 40,4 %.

Ces données obtiennent `FAIL`. Elles peuvent illustrer l’ancien prototype, mais ne doivent pas alimenter une nouvelle ID/SO ou un entraînement RL.

## OpenSim historique

Le modèle `arm26_scaled.osim` est structurellement lisible avec OpenSim 4.5 et contient trois corps, deux coordonnées, trois marqueurs et six muscles. Les géométries `.vtp` sont absentes du chemin attendu.

Une nouvelle exécution exploratoire de l’IK sur le TRC historique contient 2 170 lignes. Les accélérations maximales atteignent environ 6 333°/s² à l’épaule et 14 457°/s² au coude. Le fichier d’erreurs produit par cette exécution donne une RMS temporelle agrégée de 0,0878 m et une erreur maximale de 0,4057 m, toujours très au-dessus du seuil de 0,02 m. La valeur de 0,128 m citée dans le rapport correspond donc à une autre configuration ou agrégation historique.

Les résultats SO actuels sont complets jusqu’à 72,3 s, mais `BIClong` est saturé près de 1 pendant environ 32 % des frames. `id_results.sto` est absent.

## MuJoCo historique

`models/mujoco/v2/mujoco_models_v2/arm26_scaled_cvt3.xml` se charge et simule un pas avec MuJoCo 2.3.7. Sa version migrée `arm26_scaled_cvt3_mujoco36.xml` se charge avec MuJoCo 3.6.0 et possède des limites actives :

- `nq=2`, `nv=2`, `nu=6` ;
- deux articulations, six muscles ;
- aucune commande `exo_*` ;
- limites désactivées dans l’original, actives dans l’artefact migré.

Le modèle obtient donc `FAIL` pour la préparation RL.

## Exception MyoConverter Python 3.8

Les exigences publiées de MyoConverter et la disponibilité des roues SciPy sont incompatibles sous Python 3.8. L’installation reproductible applique le mode de compatibilité documenté dans `docs/windows_setup.md`; elle doit être remplacée dès qu’une pile OpenSim plus récente est adoptée.

## Conditions de sortie de cet état

Un nouveau jeu de résultats devient la référence uniquement lorsqu’il possède :

1. une calibration documentée ;
2. un rapport mouvement `PASS` ;
3. les setups et journaux OpenSim ;
4. un rapport OpenSim `PASS` incluant la RMS marqueurs ;
5. pour le RL, un modèle avec actionneurs d’exosquelette et limites actives.

## Préparation hors caméra

La branche de préparation V3 ajoute un protocole à deux caméras et un bac à sable RL indépendant des vidéos humaines. Le modèle simplifié possède deux moteurs humains idéaux et deux moteurs `exo_*` limités. Il sert uniquement à tester l'API Gymnasium, la récompense, PPO et les garde-fous.

Son statut maximal est `SOFTWARE_EXPLORATION_ONLY`. Les réductions de couple obtenues dans ce bac à sable sont des tests de régression logicielle, pas des estimations d'efficacité ou de fatigue. Les critères de sortie ci-dessus restent inchangés.
