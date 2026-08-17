# Plan d’exécution et livrables

## Lot 1 — reproductibilité logicielle

- créer les deux environnements ;
- faire passer `pip check` ;
- exécuter les tests ;
- figer les versions réellement fonctionnelles.

Livrable : installation depuis une machine Windows propre.

## Lot 2 — mouvement métrique

- utiliser le protocole V3 à deux caméras préparé dans `config/acquisition/` ;
- mesurer le sujet ;
- produire le CSV canonique ;
- calibrer et trianguler ;
- obtenir un rapport mouvement `PASS`.

Livrable : TRC métrique avec chronologie complète.

En attendant les caméras, `scripts/run_offline_preparation.ps1` valide le gabarit V3 et le bac à sable RL synthétique. Ce travail réduit le risque logiciel du lot 6, mais ne satisfait aucun critère biomécanique du lot 2.

## Lot 3 — biomécanique du bras dominant

- sélectionner/adapter le modèle 3D ;
- placer les marqueurs ;
- exécuter IK ;
- collecter les forces fer–table ;
- exécuter ID/SO ;
- obtenir un rapport OpenSim `PASS`.

Livrable : comparaison répétable des angles, moments et activations.

## Lot 4 — assistance passive

- utiliser l’architecture conceptuelle `light_passive_v1` retenue dans le benchmark ;
- ajouter ressorts, amortisseurs, segments et interfaces dans MuJoCo ;
- optimiser la courbe d’assistance ;
- comparer sans assistance, assistance fixe et optimisée.

Livrable : proposition mécanique et analyse de sensibilité.

## Lot 5 — extension 3D/bimanuelle

- ajouter thorax et bras gauche ;
- répéter tous les contrôles ;
- intégrer scores RULA/REBA/OCRA comme métriques complémentaires.

## Lot 6 — actif et RL, si retenu

- ajouter les moteurs `exo_*` ;
- valider contrôleur classique ;
- remplacer la trajectoire synthétique et le contrôleur humain idéal du bac à sable ;
- faire passer le readiness gate ;
- entraîner PPO ;
- comparer aux baselines et tester hors distribution.

## Lot 7 — jumeau numérique

- définir le modèle Eclipse Ditto ;
- publier seulement les états et métriques validés ;
- connecter Blender ;
- conserver les données brutes hors Ditto.
