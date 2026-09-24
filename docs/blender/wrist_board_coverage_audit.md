# Audit de la trajectoire du poignet par rapport à la planche

## Définition du contrôle

- Scène : `C:\Users\youss\mpfb-data\femme.blend`
- Rig : `Human.rig`
- Point anatomique : tête de l'os `wrist.R`
- Planche : maillage `White_desk`
- Une frame est classée « au-dessus » lorsque la projection `(x, y)` du
  poignet appartient à la bounding box mondiale de la planche.
- L'écart est la distance euclidienne horizontale jusqu'au bord le plus proche.

## Limites et trajectoire

La bounding box mondiale de la planche, en mètres, est :

- `x = [-1.079717 ; 0.667402]`, largeur 1.747119 m ;
- `y = [-0.727575 ; -0.112392]`, profondeur 0.615183 m ;
- `z = [0.115103 ; 1.040954]`, avec le plateau à `z = 1.040954 m`.

Sur les 1 081 frames, le poignet parcourt :

- `x = [-0.248705 ; 0.034368] m` ;
- `y = [-0.255790 ; 0.048181] m` ;
- `z = [1.157701 ; 1.398088] m`.

## Résultat

- 325 frames hors empreinte sur 1 081, soit **30,06 %** et 10,83 s cumulées ;
- 756 frames dans l'empreinte, soit 69,94 % ;
- toutes les sorties se produisent du côté `y_max`, vers le buste ;
- écart maximal : **16,06 cm**, frame 825 ;
- plage continue la plus longue : frames 165–213, soit 49 frames ou 1,63 s.

Plages hors empreinte :

`1`, `5–18`, `28–33`, `46–53`, `64–68`, `82–100`, `165–213`,
`258–259`, `310–313`, `346–351`, `364–382`, `448–476`, `488–498`,
`522–523`, `558–587`, `622–628`, `657–663`, `760–768`, `819–836`,
`858–873`, `882–906`, `918–926`, `979–996`, `1048–1058`.

Aux frames 181–192, l'écart passe de 5,19 cm à un maximum local de
14,41 cm à la frame 189, puis revient à 12,78 cm à la frame 192.

## Diagnostic

L'excursion est fréquente et importante. Sa cause principale est la trajectoire
angulaire V2 exploratoire : amplitude d'épaule 114,23° et amplitude de coude
108,26°. La capture ultérieure de repassage réel donne seulement 24,0° à
l'épaule et 42,5° au coude.

La coordonnée `y` du poignet Blender est presque parfaitement corrélée à la
flexion du coude (`r = 0.986`) et pas à l'angle d'épaule (`r = -0.021`). L'angle
de coude moyen vaut 97,36° hors planche contre 55,95° dans la zone. Les grandes
flexions du proxy V2 ramènent donc mécaniquement le poignet vers le buste.

Un facteur secondaire amplifie le taux : à la frame 1, le poignet est déjà à
0,26 mm au-delà du bord proche. Le placement relatif avatar/planche ne comporte
pratiquement aucune marge et n'a pas été calibré sur le sujet filmé.

Il n'y a pas d'indice d'un bug d'unité ou d'échelle globale : le rig est à
l'échelle `(1, 1, 1)` et la planche mesure 1,75 m × 0,62 m. Les segments du rig
Blender mesurent 23,23 cm et 21,09 cm, contre les hypothèses V2 de 30 cm et
25 cm. Cet écart anthropométrique existe, mais il raccourcit plutôt la portée
spatiale et n'explique pas la grande amplitude angulaire.

Le mapping est continu et cohérent avec les angles fournis ; aucune inversion,
rupture ou instabilité résiduelle n'est visible. Le problème est donc surtout
une donnée source V2 trop ample, aggravée par le placement non calibré de la
planche et par l'absence de mouvement du tronc.

## Recalage esthétique pour la présentation

Le premier essai déplaçait la planche, ce qui créait un chevauchement visuel
avec le portant. Ce déplacement a été annulé : `White_desk` et son parent sont
revenus à leur position d'origine.

La correction retenue déplace uniquement la racine `Human.rig` de
`(-0.098989, -0.316179, 0) m`. Ses enfants `Human` et
`Human.female_elegantsuit01` suivent rigidement le rig ; le fer suit toujours
la main par sa contrainte. Le centre de la bounding box de la trajectoire du
poignet coïncide ainsi avec le centre X/Y de la planche, avec une marge
équilibrée de 73,20 cm en X et de 15,56 cm en Y.

Après recalage, le taux de frames hors planche passe de **30,06 % à 0,00 %**.
Il ne reste donc aucune excursion supérieure à 10 cm et aucune rotation
d'épaule ou de coude n'a été atténuée. Les 1 081 keyframes, leur timing et les
données cinématiques sources restent strictement inchangés.

Ce recalage est une correction esthétique de mise en scène pour la
présentation. Il est distinct de la reconstruction cinématique V2, qui conserve
son statut exploratoire et ses limites documentées.

Le déplacement vertical est nul. La hauteur minimale du corps reste constante
à 9,14 cm dans le repère de la scène et les os des pieds conservent exactement
leurs coordonnées Z. Le portant reste séparé de l'avatar, sans intersection de
maillage sur les frames de contrôle 1, 181, 541 et 1 081.

## Fichiers reproductibles

- Trajectoire complète : `data/scenarios/scenario_principal/wrist_board_coverage.csv`
- Rapport calculé : `data/scenarios/scenario_principal/wrist_board_coverage.json`
- Contrôle avant recalage :
  `data/scenarios/scenario_principal/wrist_board_coverage_before_recenter.json`
- Contrôle après recalage :
  `data/scenarios/scenario_principal/wrist_board_coverage_after_recenter.json`
- Script : `src/blender/analyze_wrist_board_coverage.py`
- Script de recalage : `src/blender/recenter_board_to_wrist_trajectory.py`
- Script final de recalage de l'avatar :
  `src/blender/recenter_avatar_to_board.py`
