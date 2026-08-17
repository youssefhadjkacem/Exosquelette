# Architecture et périmètre

## Objectif

Le système doit comparer objectivement un geste de repassage sans assistance et avec assistance. Il ne doit pas confondre un avatar visuel, une simulation physique et un résultat biomécanique validé.

## Couches

### Acquisition

Entrées : vidéo synchronisée, calibration caméra, mesures anthropométriques et, si possible, force fer–table. La capture monoculaire est admise pour la visualisation, pas comme référence métrique.

### Traitement local

Les traitements sensibles à la latence restent locaux : détection de pose, triangulation, filtrage, calcul de métriques et simulation MuJoCo. Chaque message possède un horodatage, une unité, un repère et un indicateur de qualité.

### Biomécanique

OpenSim réalise l’IK, puis éventuellement l’ID et la SO. Ces étapes sont hors ligne jusqu’à validation. Le modèle historique `arm26` est conservé comme test technique, pas comme modèle final.

### Simulation d’assistance

- Dispositif passif : ressorts/couples dépendant de la posture, optimisation paramétrique.
- Dispositif actif : moteurs séparés `exo_*`, limites de couple/vitesse, puis contrôle classique et RL.

### Jumeau numérique

Eclipse Ditto publiera l’état synthétique : pose, phase du geste, métriques, assistance et alertes. Les flux bruts haute fréquence restent dans les fichiers de session ou une base dédiée.

## Décision de progression

Le premier modèle utile est un bras dominant 3D validé. Le second bras et le tronc sont ajoutés après réussite des tests. Cette progression limite le nombre de causes possibles lors d’une erreur IK ou d’un problème de conversion.

## Traçabilité

Chaque session doit conserver :

- identifiant pseudonymisé du sujet ;
- versions des logiciels et modèle ;
- calibration et mesures anthropométriques ;
- données brutes immuables ;
- paramètres de filtrage ;
- rapports qualité ;
- configurations OpenSim/MuJoCo ;
- graine et hyperparamètres d’optimisation/RL.
