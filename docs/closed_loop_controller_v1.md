# Contrôleur en boucle fermée V1

## Objectif

Cette étape vérifie que l’exosquelette suit réellement la trajectoire V2 dans la dynamique MuJoCo. Contrairement à l’analyse en cinématique prescrite, les positions articulaires ne sont pas imposées à chaque frame.

Un contrôleur couple calculé + PD utilise :

```text
couple total = M(q) q̈ cible + biais − forces passives
               + Kp × erreur de position
               + Kd × erreur de vitesse
```

Dans la condition hybride, 35 % du couple demandé est confié aux moteurs dans leurs limites. Le reste est représenté par un couple humain articulaire idéal.

## Réglages

| Articulation | Kp | Kd | Limite humaine | Limite moteur |
|---|---:|---:|---:|---:|
| Épaule | 100 | 16 | ±30 N·m | ±5 N·m |
| Coude | 40 | 6 | ±15 N·m | ±3 N·m |

Un premier réglage du coude à `Kp=80`, `Kd=12` provoquait 5 à 14 % de saturation humaine. Les gains ont été réduits sans dégrader le suivi.

## Résultats dynamiques

| Condition | RMSE épaule | RMSE coude | Couple humain épaule RMS | Couple humain coude RMS |
|---|---:|---:|---:|---:|
| Sans assistance | 0,165° | 0,260° | 7,657 N·m | 3,036 N·m |
| Passive optimisée | 0,164° | 0,259° | 7,187 N·m | 1,928 N·m |
| Hybride classique | 0,164° | 0,259° | 4,703 N·m | 1,253 N·m |

La réduction hybride du proxy de couple humain est d’environ 38,6 % à l’épaule et 58,7 % au coude. Aucun couple humain ne sature. Le moteur d’épaule sature environ 2,1 % du temps et le moteur du coude ne sature pas.

Le statut final est `EXPLORATORY_PASS`.

## Exécution

```powershell
.\.venv310\Scripts\python.exe .\src\mujoco\run_closed_loop_controller.py `
  --config config\controllers\closed_loop_v1.json
```

Les sorties sont :

- `data/scenarios/scenario_principal/closed_loop_report.json` ;
- `data/scenarios/scenario_principal/closed_loop_timeseries.csv`.

## Hypothèses de sécurité

Les contacts sont désactivés parce que les maillages convertis s’interpénètrent et créent des réactions artificielles. Les six actionneurs musculaires sont également désactivés ; l’effort humain est remplacé par un couple articulaire idéal limité.

Par conséquent, ce test valide le contrôleur et l’intégration logicielle, pas l’activité musculaire ni le confort de l’exosquelette.

## Position par rapport au RL

Cette boucle fermée constitue la baseline que PPO devra dépasser. Cependant, l’entraînement scientifique du RL reste bloqué tant que la trajectoire et OpenSim ne possèdent pas un véritable statut `PASS`.

Il est possible de tester techniquement le RL sur les données exploratoires, mais un tel résultat devra rester une démonstration logicielle et ne pourra pas être présenté comme une optimisation biomécanique validée.
