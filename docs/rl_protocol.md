# Protocole assistance passive et apprentissage par renforcement

## Choix passif ou actif

Le benchmark fourni recommande un dispositif passif pour les bras devant soi. Cette recommandation est une hypothèse à valider, pas une preuve expérimentale.

### Assistance passive — première option

Modéliser le couple par une fonction de posture :

```text
tau_assistance = f(angle_epaule, angle_coude, raideur, precharge, geometrie)
```

Optimiser les paramètres par grille, CMA-ES ou optimisation bayésienne. Objectifs : réduire activation et moment articulaire, conserver la trajectoire, éviter sur-assistance et gêne. Comparer au minimum : sans assistance, assistance fixe, assistance optimisée.

### Assistance active — RL possible

Le XML MuJoCo doit séparer :

- actionneurs humains, alimentés par des activations de référence ;
- moteurs `exo_*`, seuls contrôlés par l’agent.

L’environnement fourni est un squelette de recherche : il rejoue actuellement les activations humaines de référence pour maintenir le geste. Cette activation n’est pas encore un modèle neuromusculaire adaptatif ; le terme d’effort humain de la récompense ne suffit donc pas, à lui seul, à démontrer une réduction de fatigue. Avant une étude finale, intégrer un contrôleur humain de suivi qui réoptimise les activations en présence de l’assistance, ou une boucle musculo-squelettique validée équivalente.

## Garde d’entrée

`validate_rl_readiness.py` exige :

1. qualité mouvement `PASS` ;
2. qualité OpenSim `PASS` ;
3. actionneurs `exo_*` ;
4. limites articulaires actives.
5. plages de commande actives pour tous les moteurs `exo_*`.

## Observation et action

Observation actuelle : positions, vitesses, cible et erreur de trajectoire. À terme, ajouter phase du geste, force de contact, activations et état thermique/énergétique de l’exosquelette.

Action : commande normalisée des moteurs d’exosquelette, convertie dans leur `ctrlrange` MuJoCo.

## Récompense

```text
reward = -(
  w_track  * erreur_trajectoire
  + w_human * effort_humain
  + w_exo   * effort_exosquelette
  + w_smooth * variation_commande
)
```

Les poids doivent être documentés et soumis à analyse de sensibilité.

## Baselines et validation

PPO n’est accepté que s’il dépasse :

- aucune assistance ;
- assistance fixe ;
- contrôleur proportionnel/impédance ;
- optimisation passive si applicable.

Évaluer sur des sessions et morphologies non utilisées pendant l’entraînement. Rapporter effort humain, erreur de suivi, énergie, pics de couple, violations de sécurité et robustesse aux perturbations.

## Sécurité

Le RL reste en simulation tant que les limites de couple, vitesse et angle n’ont pas été validées. Un passage sur matériel réel nécessite une couche de sécurité indépendante, un arrêt d’urgence et un protocole expérimental approuvé.
