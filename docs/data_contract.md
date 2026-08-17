# Contrat des données de mouvement

## Données contraintes V2

Le fichier `motion_constrained.csv` conserve `frame` et `time_s`, exprime les coordonnées en mètres et ajoute :

- `source_valid` : directions sources disponibles ou interpolables ;
- `analysis_valid=0` : interdit de présenter la reconstruction comme une mesure 3D validée ;
- `reconstruction_method` : méthode planaire utilisée ;
- `shoulder_planar_angle_deg` ;
- `elbow_interior_angle_deg`.

Un rapport `EXPLORATORY_PASS` ne doit jamais être converti implicitement en `PASS`.

## CSV canonique

Une ligne correspond à une frame vidéo, même si aucune pose n’est détectée.

Champs obligatoires :

| Champ | Type | Description |
|---|---:|---|
| `frame` | entier | Index original dans la vidéo, sans renumérotation |
| `time_s` | réel | `frame / fps`, en secondes |
| `pose_detected` | 0/1 | Détection globale MediaPipe |
| `<marker>_x/y/z` | réel ou vide | Coordonnées dans le repère source déclaré |
| `<marker>_visibility` | [0,1] | Confiance de visibilité |
| `<marker>_presence` | [0,1] ou vide | Confiance de présence |
| `valid` | 0/1 | Toutes les coordonnées requises sont utilisables |
| `interpolated` | 0/1 | Au moins une coordonnée a été interpolée |

Marqueurs actuels : `r_shoulder`, `r_elbow`, `r_wrist`, `l_shoulder`, `l_elbow`, `l_wrist`, `r_hip`, `l_hip`.

## Règles

1. Ne jamais supprimer une frame pour faire disparaître une lacune.
2. Interpoler seulement une lacune courte encadrée par deux mesures valides.
3. Ne pas filtrer à travers une lacune longue.
4. Ne jamais remplacer une profondeur inconnue par zéro.
5. Déclarer le repère et les unités dans le fichier de calibration.
6. Conserver les données brutes ; les sorties lissées sont de nouveaux fichiers.

## Rapport qualité

`validate_motion.py` mesure :

- ordre et lacunes des frames ;
- monotonie du temps ;
- taux manquant par marqueur ;
- coefficient de variation des longueurs épaule–coude et coude–poignet.

Pendant la validation progressive du bras dominant, passer `--required-markers r_shoulder,r_elbow,r_wrist`. Omettre l’option seulement lorsque la capture bimanuale complète doit être exigée.

Seuils initiaux : 2 % de données manquantes, CV segmentaire 10 %, aucune lacune résiduelle. Ces seuils doivent être adaptés à un protocole validé, pas assouplis uniquement pour obtenir `PASS`.

## Sessions futures

Pour plusieurs acquisitions, utiliser :

```text
data/sessions/<session_id>/
├── metadata.json
├── video/
├── raw/motion.csv
├── processed/motion_smoothed.csv
├── calibration/calibration.json
├── opensim/
└── quality/
```
