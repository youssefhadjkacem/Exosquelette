# Documentation de l'avatar 3D de `femme.blend`

## Provenance et version

L'avatar a été généré avec **MPFB2 (MakeHuman Plugin For Blender)**. Les noms
des clés morphologiques (`$md-...`), la topologie MakeHuman et la correspondance
exacte du squelette avec le rig MPFB `default_no_toes` le confirment.

Le fichier `femme.blend` ne contient ni numéro de version MPFB, ni chemin vers
un preset `.mhm`. La version actuellement installée sur la machine d'inspection
est **MPFB 2.0.16**, d'après son `blender_manifest.toml`. Cette valeur décrit
l'environnement actuel ; elle ne prouve pas que la scène a été initialement
créée avec cette même version. La scène a été inspectée avec Blender 5.1.2.

## Morphologie observée

Les clés morphologiques actives décrivent un personnage :

- féminin (`$fe`) et jeune adulte (`$yn`) ;
- de corpulence et musculature moyennes (`$av$wg`, `$av$mu`) ;
- sans ethnicité dominante : les composantes asiatique, caucasienne et
  africaine ont toutes la même valeur, `0,326766` ;
- avec deux composantes poitrine/féminité faibles, `0,088567` et `0,088467`.

Ces valeurs sont les poids des clés macro actuellement présents dans le
maillage, pas l'historique des sliders manipulés dans MPFB. Aucun ensemble de
paramètres détaillés, nom de preset ou fichier `.mhm` n'est embarqué. Il est
donc impossible d'affirmer si l'utilisateur est parti du bouton de création
par défaut ou d'un preset ensuite modifié. Le profil est néanmoins proche d'un
personnage générique jeune, féminin, de poids et musculature moyens, avec un
mélange ethnique équilibré.

## Dimensions mesurées dans la scène

Les mesures sont faites en coordonnées mondiales Blender, en mètres, sur le
maillage évalué `Human` à la frame 1 :

| Mesure | Valeur |
|---|---:|
| Hauteur totale du maillage corporel | **1,59123 m** |
| Épaule droite → coude droit | **0,232265 m (23,23 cm)** |
| Coude droit → poignet droit | **0,210860 m (21,09 cm)** |

Les longueurs du bras sont les distances entre les centres articulaires du rig
dans sa pose de repos : tête de `upperarm01.R`, tête de `lowerarm01.R`, puis
tête de `wrist.R`. Elles représentent donc les dimensions anthropométriques du
modèle 3D utilisé et non les longueurs génériques précédemment attribuées au
modèle OpenSim. Ces valeurs correspondent à la géométrie originale avant
l'ajustement visuel V2 décrit ci-dessous.

## Ajustement des proportions visuelles pour la reconstruction V2

Pour rendre l'avatar affiché cohérent avec les longueurs utilisées lors de la
reconstruction vidéo V2, la chaîne du bras droit a reçu un facteur d'échelle
constant sur l'axe longitudinal local des os :

- `upperarm01.R` et `upperarm02.R` : facteur Y `1,162771285` ;
- `lowerarm01.R` et `lowerarm02.R` : facteur Y `1,118267596` ;
- `lowerarm01.R` n'hérite plus de l'échelle non uniforme du bras supérieur ;
- `wrist.R` n'hérite plus de l'échelle de l'avant-bras, afin de conserver la
  taille et la forme de la main.

Les distances articulaires effectives mesurées sur les 1 081 frames sont
désormais :

| Segment visuel animé | Avant | Après |
|---|---:|---:|
| Épaule → coude | 23,23 cm | **30,00 cm** |
| Coude → poignet | 21,09 cm | **25,00 cm** |

La correction est appliquée au rig de pose de l'avatar et non aux courbes de
rotation V2. Les modificateurs Armature du corps et du costume continuent à
utiliser les groupes de sommets existants : aucune retouche manuelle des poids
n'a été nécessaire. Les gros plans ne montrent ni pincement, ni rupture, ni
étirement transversal anormal. La clé corrective réversible
`Presentation_Table_Clearance` du costume a seulement été actualisée autour du
bassin pour conserver l'absence d'intersection avec la table.

L'allongement faisait descendre la main dans le plateau aux frames 156–161,
avec une pénétration verticale maximale mesurée de 3,2609 cm à la frame 159.
La racine complète `Human.rig` a donc été relevée rigidement de **3,37 cm**,
soit le minimum calculé plus environ 1 mm de marge. Cette translation ne change
pas les coordonnées X/Y du poignet. Après correction :

- bras droit contre table : 0 collision sur 1 081 frames ;
- poignet hors de l'empreinte X/Y de la planche : 0 sur 1 081, soit 0,00 % ;
- torse et zone corrigée du costume contre table : 0 collision aux frames de
  contrôle 1, 181, 541 et 1 081 ;
- contrainte du fer inchangée : `Old Iron` suit toujours
  `Human.rig/metacarpal3.R` ; la distance main–poignée reste dans la plage déjà
  acceptée et ne nécessite aucun nouvel offset.

Cet ajustement concerne **uniquement l'avatar visuel Blender**. Le fichier
biomécanique `arm26_scaled.osim`, les données OpenSim, les trajectoires sources
V2 et l'entraînement RL n'ont pas été modifiés. OpenSim et le RL conservent donc
leurs propres proportions internes. Cette séparation constitue une
incohérence résiduelle à signaler si les résultats Blender et RL/OpenSim sont
comparés quantitativement dans un autre livrable.

## Rig

- objet armature : `Human.rig` ;
- données d'armature : `Human.rig` ;
- **137 os** et 137 pose bones ;
- correspondance exacte avec le rig standard MPFB/MakeHuman
  **`default_no_toes`** ;
- ce n'est pas un rig Rigify et aucun méta-rig Rigify n'est présent.

Le nom `default_no_toes` signifie que le rig complet des orteils est omis. Il
conserve toutefois `toe1-1.L` et `toe1-1.R`, en plus du squelette du corps, des
doigts et des os faciaux.

## Vêtements et accessoires

Les seuls maillages directement parentés et déformés par `Human.rig` sont :

- `Human`, le corps ;
- `Human.female_casualsuit01`, une tenue simple composée d'un T-shirt et d'un
  pantalon long.

Le costume élégant `Human.female_elegantsuit01` a été remplacé pour rendre la
démonstration plus cohérente avec un poste de repassage. Le vêtement retenu est
un asset MPFB2/MakeHuman CC0, ajusté au corps puis attaché à `Human.rig` par un
modificateur d'armature et des groupes de sommets interpolés. Sa texture native
fournit un T-shirt bleu avec détails orange et un pantalon en jean bleu neutre.

Aucun objet séparé de cheveux, chaussures, lunettes, yeux ou autre vêtement
n'est attaché au rig. Certains détails anatomiques peuvent être intégrés au
maillage corporel plutôt que représentés par des objets séparés.

Le fer est un accessoire de scène BlenderKit distinct : le parent `Old Iron`
n'est pas enfant du rig, mais sa contrainte `COPY_LOCATION` cible
`Human.rig/metacarpal3.R`. Il suit donc fonctionnellement la main droite. Son
asset déclare une licence BlenderKit `royalty_free`. La table et le portant
sont des éléments de décor indépendants, également issus de BlenderKit, et non
des composants de l'avatar.

## Palette et rendu final de démonstration

La scène finale utilise Eevee et une palette volontairement sobre :

- peau : matériau naturel uniforme sur le corps, avec conservation de la
  texture détaillée d'origine sur la tête uniquement ; ce découpage évite les
  zones sombres peintes sur les bras par l'ancien preset
  `young_caucasian_female_special_suit` ;
- vêtement : texture MPFB2 native, T-shirt bleu et pantalon en jean ;
- fer : corps blanc, poignée turquoise et semelle métallique brossée ;
- table : tons blanc cassé et bois clair, avec éléments métalliques gris ;
- portant et cintres : métal gris anthracite ;
- éclairage : trois grandes sources surfaciques (principale chaude, remplissage
  froid léger et contre-jour), avec fond bleu-noir désaturé.

Cette passe a modifié les matériaux, l'éclairage et remplacé le maillage du
vêtement. Elle n'a modifié aucune transformation du rig, de la caméra, de la
table, du fer ou du portant ; cette invariance est vérifiée automatiquement par
le script avant l'enregistrement du fichier.

## Emplacement et suivi Git

Le fichier actif est externe au dépôt :

`C:\Users\youss\mpfb-data\femme.blend`

Le dépôt `C:\Users\youss\exosquelette` ne suit aucun fichier `.blend`, `.mhm`,
`.mhx2`, `.fbx` ou `.obj`. Aucun fichier source MakeHuman `.mhm` n'a été trouvé
dans `mpfb-data`. Le `.blend` contient des copies locales des maillages et ne
référence aucune bibliothèque Blender externe. Les trois assets BlenderKit du
décor sont mis en cache sous `mpfb-data/assets/models`, mais restent eux aussi
hors du contrôle de version.

## Licence et attribution

Le code de MPFB est publié sous **GPL-3.0-or-later**. Les assets MPFB intégrés
(maillage de base, morph targets, rigs et vêtements fournis avec MPFB) sont
placés sous **CC0 1.0**. Le projet MPFB précise qu'il ne revendique aucun droit
sur les fichiers de modèles, rendus et captures produits avec l'outil. Une
attribution n'est donc pas juridiquement exigée pour la sortie MPFB, mais une
citation académique de MPFB/MakeHuman est recommandée dans le rapport. Cette
conclusion ne couvre pas automatiquement les assets BlenderKit, qui conservent
leur propre licence `royalty_free`.

Sources officielles :

- [Licence de MPFB2](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md)
- [Dépôt officiel de MPFB2](https://github.com/makehumancommunity/mpfb2)
- [Licence CC0 des assets MakeHuman](https://github.com/makehumancommunity/makehuman-assets/blob/master/LICENSE.txt)

## Paragraphe réutilisable dans le rapport

> L'avatar numérique utilisé pour la visualisation biomécanique a été généré
> avec MPFB2 (MakeHuman Plugin For Blender). Il représente un jeune adulte de
> morphologie féminine, de corpulence et musculature moyennes, sans ethnicité
> dominante dans les paramètres macro conservés. Le maillage corporel mesure
> 1,591 m dans la scène ; les longueurs articulaires droites mesurées sur le rig
> étaient initialement de 23,23 cm entre l'épaule et le coude et de 21,09 cm
> entre le coude et le poignet. Pour la visualisation V2, elles ont été ajustées
> respectivement à 30,00 cm et 25,00 cm par une mise à l'échelle constante des
> os du bras droit, sans modifier les rotations cinématiques. L'animation repose
> sur l'armature standard MPFB
> `default_no_toes`, composée de 137 os, et l'avatar porte la tenue de travail
> simple `female_casualsuit01` (T-shirt bleu et pantalon en jean). Le rendu
> final utilise une peau naturelle, un fer blanc et turquoise, une table claire
> et un portant métallique anthracite sous un éclairage Eevee doux. Le fichier
> de travail reste externe au dépôt Git dans
> `mpfb-data/femme.blend` et aucun preset MakeHuman `.mhm` d'origine n'est
> conservé. Le code de MPFB est distribué sous GPL-3.0-or-later et ses assets
> intégrés sous CC0 1.0 ; l'attribution n'est pas obligatoire pour le modèle
> généré, mais MPFB/MakeHuman est cité ici par souci de traçabilité scientifique.
> Cet ajustement est limité à l'avatar visuel : `arm26_scaled.osim` et
> l'entraînement RL conservent leurs proportions internes et restent inchangés.

## Données reproductibles

- rapport machine : `data/scenarios/scenario_principal/avatar_metadata.json` ;
- script d'inspection : `src/blender/inspect_avatar_metadata.py` ;
- rapport des proportions :
  `data/scenarios/scenario_principal/avatar_arm_proportions_final.json` ;
- couverture finale du poignet :
  `data/scenarios/scenario_principal/wrist_board_coverage_arm_v2_final.json` ;
- audit complet du bras contre la table :
  `data/scenarios/scenario_principal/arm_table_fast_audit.json` ;
- contrôle historique de l'ancien costume élégant contre la table (antérieur
  au remplacement du vêtement) :
  `data/scenarios/scenario_principal/suit_table_clearance_arm_v2_final.json` ;
- script de correction : `src/blender/adjust_visual_arm_proportions.py` ;
- script de sélection du vêtement, des matériaux et de l'éclairage :
  `src/blender/apply_final_demo_materials.py` ;
- captures couleur finales :
  `data/scenarios/scenario_principal/final_color_control_frames/`.
