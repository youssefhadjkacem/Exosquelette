# Préparation hors caméra : acquisition V3 et bac à sable RL

## Objectif de cette branche

Cette branche permet d'avancer pendant l'indisponibilité temporaire des caméras, sans réutiliser une vidéo insuffisante comme vérité biomécanique.

Deux travaux indépendants sont préparés :

```text
Maintenant                                      Dans quelques jours
──────────                                      ───────────────────
Protocole V3 + fiche de session ──────────────→ capture à deux caméras
        │                                             │
        │                                             ▼
        │                                      reconstruction 3D
        │                                             │
        │                                             ▼
        └─ contrôle automatique des fichiers ← validation biomécanique

Trajectoire synthétique → environnement RL → tests logiciels seulement
                                                    │
                                                    └─ sera remplacé après V3
```

Le chemin synthétique ne débloque ni OpenSim, ni le RL scientifique, ni un essai sur matériel réel.

## Exécution immédiate

Depuis la racine du projet :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_offline_preparation.ps1
```

Cette commande :

1. vérifie que le gabarit V3 est complet et en attente de capture ;
2. génère une trajectoire de repassage synthétique bornée ;
3. charge le modèle MuJoCo simplifié à deux articulations ;
4. compare l'absence d'assistance à une assistance déterministe ;
5. exécute tous les tests.

L'entraînement PPO est volontairement optionnel :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_offline_preparation.ps1 `
  -TrainRL -TrainingTimesteps 10000
```

Cette option ajoute automatiquement l'acquittement `software-only-no-scientific-claim`. Elle ne doit jamais être utilisée pour annoncer un gain de fatigue ou choisir un exosquelette industriel.

## Bloc acquisition V3

Les fichiers principaux sont :

- `config/acquisition/v3_protocol.json` : exigences fixes de la campagne ;
- `config/acquisition/v3_session.example.json` : fiche à copier et remplir le jour de la capture ;
- `src/acquisition/validate_v3_session.py` : contrôle automatique.

Avant la capture, le statut attendu est `PREPARED_AWAITING_CAPTURE`. Après avoir renseigné les mesures et les deux vidéos, le statut maximal devient `READY_FOR_3D_RECONSTRUCTION`. Même ce statut ne débloque pas immédiatement OpenSim : la calibration et la reconstruction 3D doivent encore passer leurs propres contrôles.

### Placement prévu

- Caméra 1 : côté droit, vue latérale, hauteur proche de l'épaule.
- Caméra 2 : vue frontale oblique d'environ 35°.
- Les deux vues doivent montrer continuellement épaule, coude, poignet, main et fer.
- Un événement de synchronisation visible est enregistré au début et à la fin.
- Un damier de calibration et une référence métrique sont enregistrés sans déplacer les caméras.

### Mesures à relever

| Mesure | Unité | Pourquoi |
|---|---|---|
| Taille et masse du participant | m, kg | mise à l'échelle du modèle |
| Longueur bras et avant-bras droits | m | reconstruction segmentaire |
| Masse du fer | kg | charge externe |
| Hauteur de la table | m | géométrie de la tâche |
| Au moins dix cycles complets | nombre | répétabilité du geste |

Ne jamais enregistrer le nom ou une information directement identifiante dans la fiche versionnée.

## Bloc RL logiciel

Le modèle `two_dof_ironing_v1.xml` possède :

- deux articulations bornées : épaule et coude ;
- deux moteurs humains idéaux limités à ±30 Nm et ±15 Nm ;
- deux moteurs d'exosquelette indépendants limités à ±5 Nm et ±3 Nm ;
- aucun contact, muscle ou paramètre revendiqué comme mesure humaine.

L'agent observe la posture, la vitesse, la cible, l'erreur, la commande précédente et la phase. Il commande uniquement les deux moteurs `exo_*`. Un contrôleur PD représente provisoirement l'effort humain.

La récompense pénalise :

- l'erreur de suivi ;
- le couple humain normalisé ;
- l'effort de l'exosquelette ;
- les changements brusques de commande ;
- la proximité des limites articulaires.

## Garde-fous

- Le statut `SOFTWARE_EXPLORATION_ONLY` est vérifié au chargement.
- Les actions de l'agent sont limitées à `[-1, 1]`, puis converties dans les limites des moteurs.
- L'entraînement nécessite un acquittement explicite.
- Tous les résultats et modèles entraînés sont écrits sous `data/rl_sandbox/`, donc exclus de Git.
- Les métadonnées interdisent les revendications scientifiques et le déploiement matériel.
- Après V3, la trajectoire synthétique et le contrôleur humain idéal devront être remplacés.

## Critères avant la prochaine phase

La suite scientifique demande :

1. deux vidéos synchronisées et calibrées ;
2. au moins 98 % de couverture du bras droit dans chaque vue ;
3. une reconstruction 3D avec erreur de reprojection inférieure ou égale à 3 px ;
4. les mesures anthropométriques et la masse du fer ;
5. une validation OpenSim indépendante ;
6. une comparaison du futur RL avec les contrôleurs classique, passif et hybride.
