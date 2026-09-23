# src/blender/

Les scripts à la racine de ce dossier forment le pipeline principal (import, recentrage, réparation, lissage des courbes, rendu, validation) et sont réutilisés d'une étape à l'autre du projet. `diagnostics/` contient des scripts d'investigation ponctuelle (`inspect_*`, `audit_*`, `measure_*`, `search_*`) qui ont chacun servi une seule fois pour trancher une décision précise ; ils sont conservés pour la traçabilité, pas pour être relancés.
