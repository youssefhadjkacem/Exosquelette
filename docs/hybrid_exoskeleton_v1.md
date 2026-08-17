# Prototype MuJoCo hybride V1

## Résultat

Deux modèles sont générés à partir de `arm26_scaled_cvt3_mujoco36.xml` :

- `light_passive_v1.xml` : structure et ressorts, sans moteur ;
- `hybrid_active_v1.xml` : même structure passive avec deux moteurs limités.

Cette séparation permet une comparaison correcte entre assistance passive et assistance active. Le prototype est inspiré de l’architecture fonctionnelle du Light, mais ne reproduit pas un produit commercial.

Le modèle assiste le bras droit, sélectionné parce qu’il tient le fer dans `video1` et `test1`. Ce choix fonctionnel est distinct de la dominance manuelle du sujet.

## Architecture implémentée

Le prototype ajoute trois composants bleus, rigidement alignés avec le modèle humain :

| Composant | Corps parent | Masse exploratoire |
|---|---|---:|
| Harnais | `base` | 0,55 kg |
| Rail du bras | `r_humerus` | 0,40 kg |
| Rail de l’avant-bras | `r_ulna_radius_hand` | 0,35 kg |
| Total | — | 1,30 kg |

Les contacts des géométries d’exosquelette sont désactivés dans cette V1. Les composants sont parfaitement attachés aux segments humains : il n’y a donc pas encore de glissement, de déformation textile ni de désalignement articulaire.

## Assistance passive exploratoire

| Articulation | Raideur | Référence du ressort | Amortissement ajouté |
|---|---:|---:|---:|
| Épaule | 3,0 N·m/rad | 0,7 rad | 0,10 N·m·s/rad |
| Coude | 1,5 N·m/rad | 1,0 rad | 0,08 N·m·s/rad |

Ces valeurs servent uniquement à vérifier le fonctionnement logiciel. Elles ne proviennent pas du fabricant et ne doivent pas être interprétées comme des paramètres optimaux.

## Assistance active exploratoire

| Actionneur | Articulation | Limite de couple |
|---|---|---:|
| `exo_shoulder_motor` | `r_shoulder_elev` | −5 à +5 N·m |
| `exo_elbow_motor` | `r_elbow_flex` | −3 à +3 N·m |

Les limites de commande et de force sont actives dans MuJoCo. Les six actionneurs musculaires humains restent distincts des deux moteurs d’exosquelette.

## Reproduction

```powershell
# Générer les deux XML depuis la configuration
.\.venv310\Scripts\python.exe .\src\mujoco\build_hybrid_exoskeleton.py `
  --config config\exoskeleton\hybrid_active_v1.json

# Vérifier la variante hybride
.\.venv310\Scripts\python.exe .\src\mujoco\validate_model.py `
  --model models\mujoco\exoskeleton\hybrid_active_v1.xml `
  --output data\results\hybrid_active_v1_quality.json
```

La variante hybride obtient structurellement `PASS` avec `nq=2`, `nv=2` et `nu=8`. La variante passive obtient volontairement `FAIL` dans le validateur orienté RL parce qu’elle ne comporte aucun actionneur `exo_*`.

## État du RL

Le modèle est techniquement compatible avec l’environnement Gymnasium : observation de dimension 8, action de dimension 2, et simulation stable pendant le test de 100 pas.

L’entraînement reste toutefois bloqué pour deux raisons indépendantes du XML :

1. la qualité du mouvement de `video1` est `FAIL` ;
2. aucun rapport OpenSim validé n’est encore disponible.

La présence de moteurs ne suffit donc pas à autoriser le RL.

## Prochaines validations

Avant d’optimiser ou d’entraîner :

1. obtenir un mouvement calibré avec statut `PASS` ;
2. valider l’IK OpenSim et les erreurs de marqueurs ;
3. remplacer les valeurs exploratoires par des plages justifiées ;
4. exécuter une analyse de sensibilité des ressorts et des couples ;
5. créer un contrôleur classique de référence ;
6. seulement ensuite entraîner PPO et comparer les résultats.

Une V2 physique devra ajouter des interfaces souples, les points d’attache réels et un désalignement contrôlé entre les axes humains et ceux de l’exosquelette.
