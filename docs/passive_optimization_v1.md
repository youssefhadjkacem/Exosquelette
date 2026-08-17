# Optimisation passive V1

## Problème corrigé

Le réglage passif initial augmentait le couple RMS estimé de 11,3 % à l’épaule et de 4,3 % au coude. La masse ajoutée et les références de ressort étaient donc défavorables au mouvement étudié.

Une recherche bornée a été exécutée sur la trajectoire exploratoire de `video1`, avec les contraintes suivantes :

- couple passif maximal à l’épaule : 5 N·m ;
- couple passif maximal au coude : 3 N·m ;
- masse totale conservée : 1,3 kg ;
- objectif : minimiser le couple humain RMS résiduel.

## Paramètres retenus

| Articulation | Raideur | Référence | Amortissement ajouté | Couple passif maximal |
|---|---:|---:|---:|---:|
| Épaule | 2,25 N·m/rad | 1,45 rad | 0 | 4,97 N·m |
| Coude | 1,75 N·m/rad | 2,05 rad | 0 | 2,92 N·m |

La recherche a évalué 2 861 candidats admissibles à l’épaule et 1 536 au coude. Les candidats dépassant les limites de couple ont été rejetés.

## Résultats

| Condition | Épaule RMS | Réduction | Coude RMS | Réduction |
|---|---:|---:|---:|---:|
| Sans assistance | 7,633 N·m | référence | 3,028 N·m | référence |
| Passive initiale | 8,496 N·m | −11,3 % | 3,160 N·m | −4,3 % |
| Passive optimisée | 7,159 N·m | +6,2 % | 1,912 N·m | +36,9 % |
| Hybride classique optimisée | 4,682 N·m | +38,7 % | 1,243 N·m | +59,0 % |

Dans la version hybride optimisée, le moteur d’épaule sature pendant environ 2,0 % des frames et le moteur du coude ne sature pas.

## Reproduction

```powershell
# Rechercher les paramètres passifs
.\.venv310\Scripts\python.exe .\src\mujoco\optimize_passive_assistance.py

# Générer les modèles optimisés
.\.venv310\Scripts\python.exe .\src\mujoco\build_hybrid_exoskeleton.py `
  --config config\exoskeleton\hybrid_optimized_v2.json

# Évaluer la variante hybride optimisée
.\.venv310\Scripts\python.exe .\src\mujoco\evaluate_classical_assistance.py `
  --config config\controllers\classical_assistance_optimized_v2.json
```

## Interprétation correcte

Ces résultats ne prouvent pas encore une réduction réelle de l’effort musculaire. Ils montrent qu’avec notre modèle et notre trajectoire exploratoires, les paramètres optimisés réduisent le proxy de couple articulaire.

Le réglage risque d’être sur-adapté au repassage de `video1`. Il devra être testé sur d’autres sujets, d’autres vitesses, différentes masses de fer et d’autres tâches textiles.

Les forces d’interface, le confort, les désalignements et les caractéristiques réelles du dispositif ne sont pas encore inclus.
