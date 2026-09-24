# Correction de la liaison du fer à la main droite

## Diagnostic initial

Dans `femme.blend`, le maillage `Iron` avait pour parent l'Empty `Old Iron`.
Cependant, ni `Iron` ni `Old Iron` n'étaient liés au rig et ils n'avaient pas
d'animation propre. La transformation du fer restait donc constante alors que
le bras droit était animé.

## Correction appliquée

- Le groupe complet du fer reste organisé sous `Old Iron`.
- `Old Iron` reçoit une contrainte `COPY_LOCATION` nommée
  `Iron follows right hand`.
- La cible est le rig `Human.rig` et l'os `metacarpal3.R`, situé dans la paume.
  Cet os donne une prise plus naturelle que le centre de `wrist.R`.
- Le décalage est calculé à partir de la zone supérieure du fer afin que la
  poignée, et non le centre géométrique de l'objet, soit placée dans la main.
- La semelle reste horizontale et le fer reçoit une rotation de lacet de 50°
  afin d'aligner la poignée avec l'axe paume-doigts.
- Le haut de la poignée est placé 15 mm sous le centre de la paume : l'arceau
  vient contre la main sans remonter autour du poignet.
- L'échelle du modèle est ajustée à `0.65, 0.65, 0.25`. La réduction verticale
  compense la hauteur excessive de l'asset tout en conservant une marge de
  sécurité avec la planche.

Le script reproductible est `src/blender/repair_iron_attachment.py`.

## Validation

La validation parcourt les 1 081 frames, de la frame 1 à la frame 1 081 :

- distance maximale entre le centre de prise et la poignée : 5,42 cm sur
  l'ensemble de l'animation, et 1,43 cm à la frame de référence ;
- marge minimale calculée au-dessus de `White_desk` : 6 mm ;
- aucun contact avec le portant, situé hors de la trajectoire du fer ;
- contrôles visuels réalisés aux frames 1, 541 et 1 081.

## Limite visuelle acceptée

La prise en main reste une approximation volontaire : le fer est repositionné
contre la paume et la poignée est au niveau des doigts, mais les os des doigts
ne sont pas modifiés et les doigts ne sont donc pas courbés autour de la
poignée. Cette limite mineure est acceptée pour la version actuelle et peut être
mentionnée dans la légende de la visualisation présentée à l'encadrant.

Les rapports machine sont générés dans :

- `data/scenarios/scenario_principal/iron_attachment_final.json` ;
- `data/scenarios/scenario_principal/iron_scene_final_audit.json`.

## Rendu de contrôle

Blender produit d'abord une séquence PNG Workbench en 960 x 540. Elle est
ensuite encodée avec le binaire fourni par `imageio-ffmpeg` : H.264, `yuv420p`,
30 fps. La vidéo finale contient 1 081 images et dure 36,03 secondes :

`data/scenarios/scenario_principal/blender_animation_review.mp4`

## Sauvegarde et retour arrière

Avant modification, une copie a été créée ici :

`C:\Users\youss\mpfb-data\femme.before_iron_attachment.blend`

Le fichier corrigé est :

`C:\Users\youss\mpfb-data\femme.blend`
