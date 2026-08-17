# Sélection du modèle d’exosquelette

## Source et portée

Le document `benchmark_desmodeles_exosqulettes.pdf` compare trois produits pour le repassage industriel : Japet.W+, PLUM et Light. Les valeurs ci-dessous proviennent de ce benchmark et n’ont pas encore été confirmées par des fiches techniques fabricant.

Ces produits ne sont pas des modèles OpenSim ou MuJoCo directement importables. Ils définissent des architectures de dispositif. Pour simuler l’un d’eux, il faut encore construire sa géométrie, ses liaisons, ses éléments d’assistance et ses interfaces avec le corps humain.

## Comparaison pour notre pipeline

| Solution | Architecture | Zone assistée | Adéquation au repassage | Compatibilité avec `arm26` | Décision V1 |
|---|---|---|---|---|---|
| Japet.W+ | active | dos | partielle | faible : aucun DDL lombaire dans `arm26` | écartée pour la V1 |
| PLUM | passive | épaules, bras levés | faible | partielle | écartée pour la V1 |
| Light | passive | épaules et coudes, bras devant soi | élevée | bonne au niveau conceptuel | retenue comme architecture V1 |

## Choix retenu

La première simulation utilisera un **modèle conceptuel passif inspiré du Light**. L’expression « inspiré du Light » est importante : sans géométrie CAO et sans paramètres mécaniques fabricant, le modèle ne pourra pas être présenté comme un jumeau numérique exact du produit commercial.

Le modèle humain actuel possède les deux coordonnées utiles :

- `r_shoulder_elev` pour l’élévation de l’épaule ;
- `r_elbow_flex` pour la flexion du coude.

La configuration initiale est enregistrée dans `config/exoskeleton/light_passive_v1.json`.

Une première implémentation passive et hybride est décrite dans `docs/hybrid_exoskeleton_v1.md`.

## Modèle mécanique à construire

La V1 MuJoCo ajoutera au modèle humain :

1. une structure portée liée au thorax ou à une base équivalente ;
2. un segment d’exosquelette parallèle au bras ;
3. un segment parallèle à l’avant-bras si l’assistance du coude est conservée ;
4. des interfaces souples plutôt que des liaisons parfaitement rigides avec le corps ;
5. un ressort et un amortisseur autour de l’épaule ;
6. un ressort et un amortisseur autour du coude ;
7. des butées correspondant aux amplitudes biomécaniques du modèle humain.

Les paramètres inconnus restent `null` dans la configuration. Ils doivent être mesurés, obtenus auprès du fabricant ou étudiés par plages plausibles avec une analyse de sensibilité.

## Expériences prévues

Quatre conditions seront comparées avec exactement la même trajectoire :

| Condition | Description |
|---|---|
| C0 | humain sans exosquelette |
| C1 | assistance passive de l’épaule uniquement |
| C2 | assistance passive du coude uniquement |
| C3 | assistance passive combinée épaule–coude |

Les paramètres de ressort, précharge et amortissement seront optimisés pour réduire les activations et moments articulaires sans réduire l’amplitude du mouvement ni augmenter excessivement les forces d’interface.

## Conséquence pour le RL

Le modèle Light du benchmark est passif. Il ne possède donc aucune action motrice que PPO pourrait commander. Pour cette architecture, la méthode correcte est une optimisation de paramètres mécaniques, pas le RL.

Une extension active pourra être étudiée plus tard en ajoutant `exo_shoulder_motor` et `exo_elbow_motor`. Elle deviendra alors un prototype actif inspiré du Light, et non le produit Light décrit par le benchmark. Le RL ne sera autorisé qu’après comparaison avec le dispositif passif et un contrôleur classique.

## Informations encore nécessaires

Avant une simulation quantitative, il faut obtenir :

- la masse et l’inertie de chaque pièce ;
- la courbe couple–angle de l’assistance ;
- les réglages de précharge ;
- les points d’attache sur le thorax, le bras et l’avant-bras ;
- les raideurs des interfaces textiles ;
- les limites et butées mécaniques ;
- la confirmation du bras étudié dans les vidéos ;
- des données EMG ou au minimum une référence ergonomique pour la validation.

## Critère de passage à la construction

Le modèle MuJoCo pourra être construit en version exploratoire avec des plages paramétriques. Il ne devra être qualifié de modèle validé qu’après acquisition des caractéristiques mécaniques et passage des contrôles mouvement/OpenSim.
