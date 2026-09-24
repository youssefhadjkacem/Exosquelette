# Comparaison V2 de `video1` et `test1`

## Conclusion actuelle

`video1` reste la référence exploratoire du projet. Avec les mêmes paramètres de reconstruction, elle fournit 1 081 frames valides sur 1 081, alors que `test1` n'en fournit que 154 sur 804. La couverture de `test1`, limitée à 19,2 %, empêche une comparaison biomécanique fiable.

Ce résultat ne signifie pas que le geste de `test1` est moins bon. Il signifie que le bras droit tenant le fer est trop souvent occulté ou mal orienté par rapport à la caméra. Les différences d'angles peuvent donc venir de l'acquisition plutôt que du mouvement réel.

## Résultats reproductibles

| Indicateur | `video1_v2` | `test1_v2` | Interprétation |
|---|---:|---:|---|
| Statut | `EXPLORATORY_PASS` | `FAIL` | `test1` reste bloquée |
| Frames analysées | 1 081 | 804 | fenêtres configurées complètes |
| Frames valides | 1 081 | 154 | direction complète épaule–coude–poignet |
| Couverture valide | 100,0 % | 19,2 % | seuil minimal : 98 % |
| Directions brutes fiables | 99,2 % | 17,9 % | avant interpolation limitée |
| Durée analysée | 36,00 s | 32,12 s | dernière frame moins première frame |
| Amplitude d'épaule | 114,2° | 28,8° | valeur `test1` non comparable |
| Amplitude du coude | 113,4° | 54,7° | valeur `test1` non comparable |
| Cycles d'épaule estimés | 22 | non estimés | estimation interdite sous 80 % de couverture |

Les amplitudes et vitesses de `test1` ne portent que sur quelques fragments visibles. Le fait que leurs seuils cinématiques locaux passent ne valide pas la vidéo complète.

## Protocole identique

Les deux scénarios utilisent :

- le bras droit anatomique confirmé comme bras tenant le fer ;
- une reconstruction dans le plan de la caméra ;
- une longueur de bras supposée de 0,30 m ;
- une longueur d'avant-bras supposée de 0,25 m ;
- un filtre Butterworth d'ordre 4 à 2 Hz ;
- une interpolation limitée à 10 frames ;
- un maximum de 2 % de données manquantes ;
- les mêmes limites de vitesse et d'accélération angulaires.

La fenêtre complète de `test1` est conservée. Choisir uniquement ses 50 meilleures frames masquerait l'occultation et donnerait une impression trompeuse de qualité.

## Exécution

Les CSV V1 déjà présents peuvent être réutilisés :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_video_comparison_v2.ps1
```

Pour repartir des deux vidéos et refaire l'extraction MediaPipe :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_video_comparison_v2.ps1 `
  -RefreshExtraction
```

Le dossier généré `data/scenarios/essais/video1_vs_test1_v2/` contient :

- `comparison.json` : décision et métriques structurées ;
- `comparison_metrics.csv` : tableau synthétique ;
- `comparison_trajectories.csv` : trajectoires avec lacunes conservées ;
- `motion_comparison.png` : couverture et angles ;
- `comparison_report.md` : rapport technique autonome ;
- `artifact.json` : source structurée du rapport portable.

Les résultats générés et les vidéos restent ignorés par Git afin de ne pas versionner de données lourdes ou personnelles.

## Règles de blocage

Le paramètre `--report-on-fail` autorise uniquement la production d'un rapport comparatif. Il ne transforme jamais un échec en succès scientifique.

Pour `test1` :

- aucun TRC exploratoire n'est produit par le lanceur V2 ;
- aucune cible MuJoCo n'est produite ;
- OpenSim quantitatif reste interdit ;
- l'évaluation de l'assistance reste interdite ;
- le RL reste interdit.

## Ce qu'il faut filmer ensuite

1. Placer une caméra du côté du bras droit, approximativement perpendiculaire au plan principal du geste.
2. Ajouter une seconde caméra oblique synchronisée pour mesurer la profondeur.
3. Garder l'épaule, le coude, le poignet, la main et le fer visibles pendant tous les cycles.
4. Éviter que le tronc, la table ou le vêtement occultent le coude et le poignet.
5. Ajouter une référence métrique rigide dans la scène.
6. Mesurer la taille, la masse, les longueurs segmentaires et la masse du fer.
7. Enregistrer au moins dix cycles continus, puis conserver une fenêtre explicitement définie.

## Critère pour poursuivre

La comparaison de l'assistance et la préparation du RL ne reprendront que lorsque deux acquisitions indépendantes du même geste obtiendront `EXPLORATORY_PASS` avec le même protocole. Une validation 3D et des charges externes seront encore nécessaires avant de qualifier les résultats de biomécaniques.
