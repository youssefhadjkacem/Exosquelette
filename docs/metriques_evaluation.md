# Métriques d'évaluation du projet

Ce document rassemble les métriques quantitatives du projet et précise, pour chacune, **ce qu'elle mesure réellement et ce qu'elle ne prouve pas**.

## Règle appliquée

Précision, rappel et F1-score ne sont calculés **que** pour une tâche de classification ou de détection disposant d'une **vérité terrain indépendante**. Sans vérité terrain, ou pour une mesure continue, on utilise la métrique adaptée (erreur RMS, erreur de reprojection, taux de conformité, etc.). Aucun chiffre n'est inventé : quand une métrique n'est pas calculable, le document le dit.

| Sujet | Vérité terrain ? | Métrique retenue | Section |
|---|---|---|---|
| Détection des cycles de repassage | **Non** (le « 7 cycles » est lui-même algorithmique) | comptage, accord entre méthodes, sensibilité au seuil ; **pas de F1** | 1 |
| Détection de pose (MediaPipe) | **Non** | taux de détection brut, visibility moyenne ; **pas de P/R/F1** | 2 |
| Validation de session V3 | Sans objet (règles fixes) | taux de conformité par catégorie | 3 |
| Erreurs continues (reprojection, IK, synchro, etc.) | Sans objet (mesures continues) | erreurs, écarts, pourcentages | 4 |

---

## 1. Détection des cycles de repassage

### Ce qui existe

Le nombre de cycles de la session de capture (`complete_cycles_recorded = 7`) est enregistré dans `data/sessions/session_capture_stereo_test/metadata.json`. Les notes de ce même fichier précisent que ce n'est **pas un comptage manuel** :

- corrélation de phase (`cv2.phaseCorrelate`) image par image sur `camera_1_vue_laterale_droite_synced.mov`, dans une zone fixe autour de la planche (x 820–1400, y 620–1060 px) ;
- position cumulée filtrée (Butterworth 4e ordre, 2 Hz) ;
- détection des retournements par `scipy.signal.find_peaks`, prominence = 15 % de l'amplitude totale (~47 px) ;
- résultat : 8 pics et 8 creux alternés, soit 15 segments et 7 cycles complets aller-retour.

### Conclusion stricte

- **Aucun comptage manuel** ni aucune position de pic/creux annotée à la main n'existe dans le dépôt.
- La détection automatique ne peut donc pas être comparée à une référence indépendante : **précision, rappel et F1 ne sont pas calculables**. L'écart de comptage détecteur/manuel ne l'est pas non plus. Comparer le détecteur à son propre résultat serait circulaire.

### Ce qui peut être mesuré honnêtement

**a) Cohérence interne** (`metadata.json`) : pics − 1 = creux − 1 = 7. Le détecteur est cohérent avec lui-même, ce qui ne prouve pas qu'il est juste.

**b) Accord entre deux méthodes automatiques.** L'estimateur du projet (`scripts/compare_motion_v2.py`, fonction `estimate_cycles`, appliqué à l'angle d'épaule reconstruit) donne, sur la même prise :

| Méthode (signal analysé) | Cycles |
|---|---:|
| Corrélation de phase sur la zone planche/fer (`metadata.json`) | 7 |
| `estimate_cycles` sur `shoulder_planar_angle_deg` (`video_stereo_cam1_methode_v2/motion_constrained.csv`) : 10 pics, prominence 5,0° | 9 |
| **Écart absolu** | **2** (soit 28,6 % de 7) |

Cet écart mesure le **désaccord entre deux méthodes automatiques** sur deux signaux différents. Il ne dit pas laquelle est correcte.

**c) Sensibilité au seuil de prominence** (fraction de l'amplitude, distance minimale 0,5 s ; nombre de cycles = pics − 1) :

| Fraction | 5 % | 10 % | 15 % (défaut) | 20 % | 25 % | 30 % |
|---|---:|---:|---:|---:|---:|---:|
| Prise stéréo cam1 (amplitude 24°, plancher de prominence 5°) | 9 | 9 | 9 | 9 | 8 | 8 |
| `scenario_principal` (amplitude 114°) | 29 | 24 | 22 | 17 | 14 | 13 |

À 15 %, la valeur du scénario principal (22) retrouve celle de `comparaison_video_principale_vs_secondaire/comparison.json`. Sur `scenario_principal` le comptage varie de 13 à 29 selon le seuil : **sans vérité terrain, aucun de ces nombres ne peut être présenté comme exact.**

### Pour obtenir un vrai F1

Annoter manuellement les frames de retournement sur la vidéo (idéalement deux annotateurs), fixer une tolérance d'appariement (par exemple ± 5 frames), puis calculer précision, rappel et F1 du détecteur. Ce travail n'a pas été fait.

---

## 2. Détection de pose (MediaPipe)

### Vérité terrain

**Il n'existe aucun échantillon de frames avec landmarks vérifiés manuellement** dans le dépôt (aucun fichier d'annotation, aucune vérification manuelle documentée). **Précision, rappel et F1 ne sont donc pas calculés.**

### Ce qui est mesuré à la place

Les chiffres ci-dessous sont un **taux de détection brut** et un **score de confiance moyen**, calculés sur les CSV d'extraction. **Ce ne sont pas des métriques de précision ni de rappel**, faute de vérité terrain.

- Paramètres MediaPipe Pose : `min_detection_confidence = 0,5`, `min_tracking_confidence = 0,5` (défauts de `src/extract_motion.py` et `src/acquisition/detect_pose_2d.py`).
- « Pose détectée » : `pose_detected = 1` (MediaPipe a renvoyé une pose sur la frame).
- Visibility moyenne : moyenne du score `visibility` sur les frames où une pose est détectée. C'est un score de confiance du modèle, **pas** une probabilité calibrée ni un accord avec la réalité.
- « % frames vis ≥ 0,5 » : sur toutes les frames, part où le score atteint 0,5 (seuil par défaut `--min-visibility` de `src/smooth_motion.py`).

| Jeu de données | Frames | Pose détectée |
|---|---:|---:|
| `video_principale.mp4` (`video_principale_methode_v1/motion_raw.csv`) | 2298 | 94,43 % (2170) |
| `video_secondaire.mp4` (`video_secondaire_methode_v1/motion_raw.csv`) | 804 | 95,15 % (765) |
| Session, caméra 1 (`raw/pose2d_camera_1.csv`) | 1396 | 100 % |
| Session, caméra 2 (`raw/pose2d_camera_2.csv`) | 1396 | 100 % |

Visibility moyenne (frames détectées) / % de frames avec visibility ≥ 0,5 :

| Landmark | video_principale | video_secondaire | Session cam. 1 | Session cam. 2 |
|---|---|---|---|---|
| Épaule droite | 0,9997 / 94,43 % | 0,9977 / 95,15 % | 0,9996 / 100 % | 0,9998 / 100 % |
| Coude droit | 0,9409 / 92,86 % | **0,2952 / 18,41 %** | 0,9646 / 100 % | 0,9894 / 100 % |
| Poignet droit | 0,9097 / 92,95 % | **0,4318 / 31,72 %** | 0,8929 / 100 % | 0,9747 / 100 % |
| Épaule gauche | 0,9995 / 94,43 % | 0,9992 / 95,15 % | 0,9939 / 100 % | 0,9993 / 100 % |
| Coude gauche | 0,7613 / 79,63 % | 0,9835 / 95,15 % | **0,2346 / 0,57 %** | 0,8002 / 93,27 % |
| Poignet gauche | 0,7651 / 79,77 % | 0,9569 / 95,15 % | **0,3266 / 8,24 %** | 0,8371 / 93,55 % |
| Hanche droite | 0,9968 / 94,43 % | 0,9546 / 95,15 % | 0,8407 / 100 % | 0,9734 / 100 % |
| Hanche gauche | 0,9984 / 94,43 % | 0,9468 / 95,15 % | 0,7704 / 99,64 % | 0,9732 / 100 % |

Lecture (descriptive, sans vérité terrain) :
- Sur `video_secondaire.mp4`, le bras droit tenant le fer est peu visible (coude 18,4 %, poignet 31,7 %). C'est cohérent avec la couverture de 19,15 % relevée en section 4 et avec l'échec de ce scénario.
- Sur la session, la caméra 1 (vue latérale droite) masque le bras gauche (coude 0,57 %), ce qui est attendu vu son placement.
- Une pose « détectée » avec une visibility élevée peut néanmoins être mal placée : ces taux ne mesurent pas la justesse des positions.
- Les valeurs de `video_stereo_cam1_methode_v1/motion_raw.csv` sont identiques à celles de `pose2d_camera_1.csv` (même vidéo, même extraction).

---

## 3. Validation de session V3 (`src/acquisition/validate_v3_session.py`)

### Nature du validateur

Ce n'est **pas un classifieur statistique** : il ne prédit rien. Chaque critère est vérifié par une **règle déterministe fixe** (présence d'un champ, valeur dans des bornes, fichier existant, écart inférieur à un seuil). Il n'y a ni prédiction ni vérité terrain à comparer, donc **le F1-score n'est pas la métrique adaptée**. On mesure un taux de conformité.

Protocole : `config/acquisition/v3_protocol.json`. Rapport enregistré : `data/sessions/session_capture_stereo_test/quality/acquisition_v3_readiness.json` (statut `FAIL`, 12 éléments en attente, 1 échec).

### Matrice de conformité (session `session_capture_stereo_test`)

Les 38 contrôles ci-dessous ont été recalculés règle par règle à partir de `metadata.json` et du protocole. Le résultat coïncide avec le rapport enregistré (mêmes 12 éléments en attente, même unique échec).

| Catégorie | Contrôles | Conformes | En attente | Échec | Non évaluable |
|---|---:|---:|---:|---:|---:|
| Mesures requises (bornes) | 6 | 6 | 0 | 0 | 0 |
| Cycles (≥ 10) | 1 | 0 | 0 | **1** | 0 |
| Structure (2 caméras distinctes) | 2 | 2 | 0 | 0 | 0 |
| Par caméra (rôle, vidéo, calibration, fps, durée, résolution, synchro début/fin, landmarks visibles) | 18 | 12 | 6 | 0 | 0 |
| Entre caméras (fps, durée, fichiers distincts, synchro début/fin) | 5 | 4 | 0 | 0 | 1 |
| Checklist terrain | 6 | 0 | 6 | 0 | 0 |
| **Total** | **38** | **24** | **12** | **1** | **1** |

- **Taux de conformité global : 24/38 = 63,2 %** (24/37 = 64,9 % des contrôles évaluables).
- Les « 12 » du rapport sont le nombre d'éléments **en attente**, pas le nombre total de critères. Une lecture « X/12 » serait trompeuse.
- Les éléments en attente : calibration, événement de synchronisation de fin et visibilité complète des landmarks (pour chaque caméra), plus les 6 items de la checklist (consentement, damier, référence métrique, trépieds, éclairage, événements de synchro début et fin).
- L'unique échec est le nombre de cycles (7 < 10). Sans lui, le statut serait `PREPARED_AWAITING_CAPTURE`.
- L'écart de synchronisation de fin est non évaluable : aucun événement de fin n'a été enregistré.

### Réserves

- Les 6 mesures « conformes » (stature 1,60 m, masse 60 kg, bras 0,30 m, avant-bras 0,23 m, fer 1,4 kg, table 0,87 m) sont des **estimations génériques non mesurées** (voir les notes de `metadata.json`). Être dans les bornes ne veut pas dire avoir été mesuré.
- Le validateur ne teste pas certains seuils pourtant définis dans le protocole : couverture de pose ≥ 98 %, erreur de reprojection ≤ 3,0 px, trous de triangulation ≤ 3 frames. Ils sont évalués en aval (section 4 pour la reprojection).
- Les éléments en attente ont été volontairement laissés en l'état (voir la clôture de session dans les notes de `metadata.json`).
- Aucune matrice d'avancement antérieure n'a été trouvée dans le dépôt : celle du tableau ci-dessus est calculée ici.

---

## 4. Métriques continues et mesures du projet

Aucun F1 ici : ce sont des erreurs, des écarts et des pourcentages. « Recalculé » signifie recalculé pour ce document à partir des fichiers bruts ; sinon la valeur est lue dans le fichier cité. Tous les résultats d'optimisation, de reconstruction et de contrôle reposent sur des trajectoires **exploratoires** (une seule caméra, longueurs de segments supposées) : ils valident la chaîne logicielle, pas l'efficacité réelle d'un exosquelette.

### 4.1 Session de capture, calibration et triangulation

| Métrique | Valeur | Seuil / référence | Source |
|---|---|---|---|
| Décalage temporel estimé entre caméras (3 méthodes de corrélation audio) | 840,0 à 845,2 ms | — | `session_capture_stereo_test/metadata.json` (notes) |
| Correction appliquée (coupe caméra 1) | 25 frames = 0,8333 s | — | idem |
| **Erreur de synchronisation résiduelle** | **10,771 ms** | ≤ 16,7 ms | idem ; seuil dans `config/acquisition/v3_protocol.json` |
| Erreur de reprojection, moyenne | **58,99 px** | ≤ 3,0 px | `session_capture_stereo_test/quality/triangulation_quality.json` |
| Erreur de reprojection, RMS / p95 / max | 67,50 / 110,18 / 206,02 px | ≤ 3,0 px | idem |
| Frames sous le seuil de 3 px : coude droit / poignet droit | 5,30 % (74/1396) / 4,44 % (62/1396) | — | idem |
| Frames sous le seuil de 3 px : épaule droite, hanche droite, épaule gauche | 0 % | — | idem |
| Longueur épaule→coude triangulée : moyenne / CV | 0,406 m / 5,58 % | CV ≤ 10 % ; longueur supposée 0,30 m | `session_capture_stereo_test/quality/motion_quality.json` ; `metadata.json` |
| Longueur coude→poignet triangulée : moyenne / CV | 0,490 m / 10,85 % (**FAIL**) | CV ≤ 10 % ; longueur supposée 0,23 m | idem |

Précisions : la synchronisation repose sur un seul transitoire audio commun, sans événement de fin donc sans contrôle de dérive. La calibration utilisée est **approximative** (dérivée de fiches techniques, sans damier) : une reprojection à 59 px vient au moins en partie de là ; elle ne permet pas de conclure sur la qualité de la détection 2D. Les longueurs triangulées s'écartent fortement des longueurs supposées (+35 % et +113 %, écarts calculés ici).

### 4.2 Qualité du mouvement (chaîne V1, seuils : données manquantes ≤ 2 %, CV des segments ≤ 10 %)

| Prise | Frames | Manquant épaule / coude / poignet | CV épaule→coude / coude→poignet | Statut | Source |
|---|---:|---|---|---|---|
| `video_principale` | 2298 | 2,57 / 4,48 / 4,31 % | 33,05 / 40,00 % | FAIL | `video_principale_methode_v1/motion_quality.json` |
| `video_secondaire` | 804 | 3,36 / 80,85 / 67,54 % | 19,37 / 50,47 % | FAIL | `video_secondaire_methode_v1/motion_quality.json` |
| Stéréo cam. 1 | 1396 | 0 / 0 / 0 % | 10,31 / 8,14 % | FAIL (un seul critère, de 0,31 point) | `video_stereo_cam1_methode_v1/motion_quality.json` |

Données historiques (ancien prototype, non recalculées ici) : 2170 poses, 128 frames manquantes, CV 33,6 % / 40,4 % (`docs/current_status.md`).

### 4.3 Reconstruction V2 et comparaison des prises

| Métrique | Valeur | Source |
|---|---|---|
| Frames valides, `scenario_principal` | 1081/1081 (0 % manquant) | `scenario_principal/motion_quality_v2.json` |
| Amplitude épaule / coude reconstruites | 114,23° / 113,39° | idem |
| Vitesse p95 épaule / coude | 187,6 / 243,7 °/s | idem ; `docs/scenarios/video1_v2.md` |
| Accélération p95 épaule / coude | 1266,6 / 1872,4 °/s² | idem ; `docs/scenarios/video1_v2.md` |
| CV des segments reconstruits | ~1e-16 | idem — **valeur imposée** (0,30 / 0,25 m constants), pas une mesure |
| Couverture bras droit, `video_secondaire` vs `video_principale` | **19,15 %** (154/804) vs 100 % | `comparaison_video_principale_vs_secondaire/comparison.json` ; seuil de couverture : 80 % |
| Cycles estimés (`video_principale` / `video_secondaire`) | 22 / non estimés | idem (voir la section 1 pour les réserves) |

### 4.4 OpenSim

| Métrique | Valeur | Seuil / référence | Source |
|---|---|---|---|
| **Erreur RMS des marqueurs (IK), moyenne sur 1396 frames** | **0,6834 m** (min 0,6703 ; max 0,7028) | ≤ 0,02 m | `video_stereo_cam1_methode_v2/opensim/ironing_inverse_kinematics_ik_marker_errors.sto` (**recalculé**) ; « ~0,68 m » dans `docs/scenarios/v3_20260825_v2.md` |
| Erreur maximale d'un marqueur (moyenne sur les frames) | 0,7225 m | — | idem (recalculé) |
| Amplitude épaule / coude après IK | 7,11° / 4,78° | reconstruction V2 : 24,00° / 42,52° | `ik_results.mot` (recalculé) ; `motion_quality_v2.json` |
| Historique : IK sur TRC historique, RMS / max | 0,0878 m / 0,4057 m | ≤ 0,02 m | `docs/current_status.md` (non recalculé) |
| Historique : accélérations max épaule / coude | ~6333 / ~14 457 °/s² | — | idem |
| Historique : `BIClong` saturé près de 1 | ~32 % des frames | — | idem |

Précisions : l'IK a tourné sans erreur d'exécution mais son résultat **n'est pas exploitable** (échelle du modèle `arm26_scaled.osim` très différente des longueurs imposées à la reconstruction, cf. `docs/scenarios/v3_20260825_v2.md`). L'IK a été lancée avec le drapeau d'exception `exploratory_override` (`opensim/analysis_metadata.json`) ; ID et SO n'ont pas été exécutées sur ce scénario.

### 4.5 MuJoCo (assistance simulée, couples humains idéaux)

| Métrique | Épaule | Coude | Source |
|---|---:|---:|---|
| Réduction du RMS de couple humain, optimisation passive | 6,21 % | 36,87 % | `scenario_principal/passive_optimization_report.json` |
| Réduction du RMS de couple humain, boucle fermée passive | 6,14 % | 36,51 % | `scenario_principal/closed_loop_report.json` |
| Réduction du RMS de couple humain, boucle fermée hybride | **38,59 %** | **58,73 %** | idem |
| Erreur de suivi RMS, sans assistance | 0,1653° | 0,2598° | idem |
| Erreur de suivi RMS, hybride | 0,1639° | 0,2594° | idem |
| Saturation du couple exosquelette, hybride | 2,08 % des échantillons | 0 % | idem |

Ces réductions viennent de simulations sur une seule trajectoire monoculaire exploratoire, avec des couples humains idéaux : ce sont des tests logiciels, pas une estimation d'efficacité ou de fatigue. L'optimisation passive peut sur-ajuster ce cas (limites listées dans `passive_optimization_report.json`).

### 4.6 Avatar Blender

| Métrique | Valeur | Source |
|---|---|---|
| **Frames avec poignet hors planche, avant recentrage** | **30,06 %** (325/1081, soit 10,83 s) | `scenario_principal/wrist_board_coverage_before_recenter.json` ; `docs/blender/wrist_board_coverage_audit.md` |
| Frames avec poignet hors planche, après correction | **0 %** (0/1081) | `wrist_board_coverage_after_recenter.json`, `wrist_board_coverage_arm_v2_final.json` |
| Paires de triangles en intersection vêtement/planche, aux 4 frames de contrôle | 133 → 0 ; scan complet des 1081 frames : 0 | `scenario_principal/casualsuit_table_fix_report.json` |
| Démo lissée : poignet hors planche / collisions / frames | 0 % / 0 paire / 1081 | `scenario_principal/demo_smoothed/validation_report_postheight.json` |
| Démo lissée : distance main–fer | 0,09541 m constante (étendue 2,3e-8 m) | idem |
| Démo lissée : déviation max angulaire due au filtre | 13,8° (épaule) / 17,5° (coude) | `docs/blender/demo_smoothed_disclaimer.md` (non recalculé) |
| Démo lissée : réduction du « jerk » moyen | 30 à 44 % | idem |
| Démo lissée : hauteur du poignet au-dessus de la planche | min 4,6 / moy 9,0 / max 12,7 cm ; 0 % des frames au-dessus de 15 cm (contre 98 % avant correction) | idem (non recalculé) |
| Cheveux `ponytail01` : paires de triangles cheveux/vêtement, frames 1/181/541/1081 | 0 (sur `femme.blend` et sur `femme_demo_smoothed.blend`) | `demo_smoothed/hair_collision_report.json` ; `presentation_assets/avatar_makehuman/hair_collision_report.json` |
| Cheveux `ponytail01` : paires cheveux/corps | 98, identiques sur les 4 frames | idem — ancrage sur le cuir chevelu, pas une collision due au mouvement |

Précisions : le fichier `demo_smoothed/height_correction_report.json` décrit un état intermédiaire de la correction de hauteur (après cette étape : min 3,2 / moy 9,2 / max 13,7 cm) ; les valeurs finales, après re-filtrage, sont celles de `demo_smoothed_disclaimer.md`. La version lissée est cosmétique et ne doit servir à aucune conclusion biomécanique.

---

## Limites générales

- Toutes les trajectoires viennent d'une caméra unique (ou d'une calibration approximative pour la session stéréo) : les valeurs absolues (mètres, degrés, couples) ne sont pas des mesures du sujet réel.
- Aucune vérité terrain n'existe dans le dépôt pour les cycles ni pour les landmarks : les métriques de classification/détection (précision, rappel, F1) ne peuvent pas être produites sans annotation manuelle préalable.
- Les valeurs marquées « non recalculé » sont reprises de la documentation du dépôt et n'ont pas été revérifiées sur les données brutes pour ce document.
