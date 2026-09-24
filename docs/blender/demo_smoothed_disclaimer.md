# femme_demo_smoothed.blend — avertissement (usage cosmetique uniquement)

## Ce que c'est

`C:\Users\youss\mpfb-data\femme_demo_smoothed.blend` est une **copie** de
`femme.blend` (production), sur laquelle les deux courbes d'animation du
bras droit ont ete lissees avec un filtre Butterworth passe-bas
(ordre 4, zero-phase `sosfiltfilt`, meme famille de filtre que
`src/smooth_motion.py`, coupure ajustee a **1,5 Hz** au lieu du defaut
pipeline de 6 Hz — voir "Pourquoi 1,5 Hz" ci-dessous).

Canaux modifies :
- `pose.bones["upperarm01.R"].rotation_euler[2]` (epaule)
- `pose.bones["lowerarm01.R"].rotation_euler[0]` (coude)

Rien d'autre n'a change : meme rig, meme position, meme vetement/materiaux,
meme correction de garde-robe/table, memes 1081 keyframes (une par frame,
valeurs remplacees en place, pas de re-echantillonnage).

## Ce que ce N'EST PAS

**Cette version ne doit jamais servir de base a une affirmation scientifique
ou a une mesure biomecanique** (amplitudes articulaires, vitesses,
accelerations, validation de modele, comparaison a l'IK OpenSim, etc.).
Le filtrage cosmetique deforme legerement les positions angulaires
(deviation max observee : 13,8° epaule / 17,5° coude par rapport aux
donnees sources) precisement aux endroits ou le mouvement change de
direction — soit exactement les instants qui interessent une analyse
biomecanique.

Pour toute mesure ou affirmation scientifique, se referer exclusivement a :
- `C:\Users\youss\mpfb-data\femme.blend` (reference, non modifiee par ce travail)
- `data/scenarios/scenario_principal/blender_animation_review.mp4` (rendu de reference)
- Les donnees sources : `data/scenarios/scenario_principal/target_arm26_exploratory.mot`
  et la chaine OpenSim associee.

## Pourquoi 1,5 Hz et pas 6 Hz (defaut pipeline)

Le defaut du pipeline (`--cutoff-hz 6.0`, utilise par `smooth_motion.py` sur
des donnees de marqueurs 3D bruitees) n'avait quasiment aucun effet ici
(deviation max 0,01°/0,6°), car cette trajectoire est deja une sortie
d'import `.mot` propre, sans bruit de capture. Une coupure plus basse etait
necessaire pour produire un lissage visuellement perceptible. 1,5 Hz a ete
choisi car il reduit le "jerk" moyen (derivee seconde) de 30 a 44% tout en
preservant l'amplitude generale du geste (114,2°→114,5° epaule,
108,3°→107,9° coude) — un ordre de grandeur plus bas (1,0 Hz) commence a
aplatir sensiblement l'amplitude (114,2°→101,6° epaule) et a ete ecarte pour
cette raison.

## Validation geometrique (1081 frames completes, pas d'echantillon)

Voir `data/scenarios/scenario_principal/demo_smoothed/validation_report.json` pour le
detail initial, et `validation_report_postheight.json` pour l'etat final
apres la correction de hauteur ci-dessous. Criteres verifies apres chaque
etape : poignet droit hors zone de `White_desk`, collisions triangle
torse/vetement-table, distance main-fer.

## Correction de hauteur du poignet (etape 2)

Le lissage seul ne corrigeait pas un defaut different : le poignet restait
constamment 13-39cm au-dessus de la planche (jamais proche du tissu),
irrealiste pour un geste de repassage. `src/blender/reduce_wrist_height_demo.py`
comprime cette hauteur via une recherche "compass" (descente locale sans
direction fixe, car la hauteur n'est pas une fonction monotone simple de
(epaule, coude) une fois les canaux secondaires `upperarm01.R` idx0/idx1 pris
en compte) vers `target = 0.08m + 0.20 * max(0, h - 0.08m)`. Resultat final
apres reapplication du filtre Butterworth (1,5Hz) pour lisser le bruit
reintroduit par la recherche independante frame-par-frame : hauteur min
4,6cm / max 12,7cm / moyenne 9,0cm / mediane 9,0cm -- 0% des frames au-dessus
de 15cm (contre 98% avant correction). Deux tres courts segments (4 et 6
frames, sur 1081) n'ont pas atteint la cible via la recherche et ont ete
combles par interpolation lineaire des frames voisines corrigees, pour
eviter un saut visible plutot que d'utiliser le "meilleur effort" de la
recherche (qui derivait vers une limite articulaire physique extreme).

Voir `data/scenarios/scenario_principal/demo_smoothed/height_correction_report.json`
pour le detail complet (avant/apres, segments interpoles, etc.).

## Fichiers produits par cette etape

- `src/blender/extract_arm_fcurves.py` — extrait les valeurs de F-curve en JSON
- `src/blender/smooth_arm_fcurve_values.py` — filtre Butterworth (scipy, hors Blender)
- `src/blender/apply_smoothed_arm_fcurves.py` — reinjecte les valeurs filtrees
- `src/blender/validate_demo_smoothed.py` — revalidation geometrique 1081 frames
- `src/blender/render_demo_smoothed_video.py` — rendu Eevee de la video de demo
- `data/scenarios/scenario_principal/demo_smoothed/` — JSON intermediaires + rapport
- `data/scenarios/scenario_principal/blender_animation_demo_smoothed.mp4` — video de demo
- `data/scenarios/scenario_principal/control_frames_demo_smoothed/` — 4 frames de controle
