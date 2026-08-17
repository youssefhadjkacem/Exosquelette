# Calibration et validation biomécanique

## Limite de la vidéo actuelle

Les coordonnées `x/y` MediaPipe issues de l’image sont normalisées par la taille de l’image. La profondeur `z` monoculaire est relative et ne fournit pas une mesure métrique fiable. Multiplier toutes les coordonnées par 1000 et réduire `z` à 30 % ne constitue pas une calibration.

## Acquisition recommandée

Par ordre de préférence :

1. deux caméras calibrées et synchronisées avec triangulation ;
2. caméra RGB-D ;
3. IMU combinées à une caméra ;
4. monoculaire, uniquement pour démonstration ou analyse qualitative.

Mesurer au minimum la taille, la largeur d’épaules, la longueur acromion–épicondyle et épicondyle–styloïde. Placer une mire ou un objet métrique dans le volume de travail.

## Fichier de calibration

`config/calibration.json` contient :

- `scale_mm_per_unit` ;
- une matrice homogène `transform_4x4` source → OpenSim ;
- la méthode et la date ;
- `analysis_valid`, positionné à `true` après validation indépendante.

`calculate_scale.py` ne peut produire `analysis_valid=true` que si l’utilisateur confirme à la fois une source 3D métrique (`--metric-3d-source`) et un repère déjà transformé vers OpenSim (`--confirm-opensim-frame`). Une simple mesure anthropométrique sur une reconstruction monoculaire reste invalide.

## Modèle OpenSim

### Phase 1

Utiliser un modèle 3D du bras dominant, par exemple une version compatible de MoBL-ARMS. Vérifier les marqueurs, les degrés de liberté, les muscles et la compatibilité OpenSim avant toute conversion.

### Phase 2

Ajouter le thorax et le membre gauche. Une simple copie miroir doit être vérifiée : repères, signes des coordonnées, géométrie, chemins musculaires et inerties.

## Critères avant ID/SO

- RMS des marqueurs < 0,02 m ;
- erreurs maximales et marqueurs problématiques documentés ;
- aucune accélération angulaire aberrante ;
- longueurs segmentaires stables ;
- coordonnées filtrées sans rupture de temps ;
- forces externes synchronisées et exprimées dans le bon repère.

Le seuil d’accélération de `validate_results.py` est un garde-fou initial, pas une norme clinique.

## Forces du repassage

L’ID doit connaître l’effort appliqué par le fer et la réaction du plan de travail. Solutions possibles : balance/plateforme sous la table, capteur d’effort au manche, fer instrumenté ou scénario de force explicitement synthétique. Sans cela, les moments et activations ne doivent pas être présentés comme une mesure réelle de réduction de charge.

## Comparaison OpenSim–MuJoCo

Après conversion, comparer sur un ensemble de postures :

- positions des marqueurs terminaux ;
- limites articulaires ;
- bras de levier musculaires ;
- forces musculaires ;
- couple net par articulation.

Les graphiques `Step1`, `Step2` et `Step3` produits par MyoConverter constituent des diagnostics, pas une validation automatique.

Les anciens XML contiennent parfois `option@collision`, supprimé dans MuJoCo 3.6, et des articulations explicitement `limited="false"`. Utiliser `src/mujoco/migrate_xml.py` pour produire un nouvel artefact sans modifier l’original, puis exécuter `validate_model.py`.
