# Installation Windows 11

## Prérequis

- Python 3.10 et 3.8 visibles par `py -0p` ;
- Git ;
- OpenSim 4.5 installé, par défaut dans `C:\OpenSim 4.5` ;
- pilotes graphiques compatibles avec MuJoCo.

## Installation automatique

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

Pour un autre emplacement OpenSim :

```powershell
.\scripts\setup_windows.ps1 -OpenSimHome "D:\Applications\OpenSim 4.5"
```

Si le lanceur `py` ne détecte pas les interpréteurs, le script recherche aussi les installations utilisateur standards. Les chemins peuvent être imposés :

```powershell
.\scripts\setup_windows.ps1 `
  -Python310Base "C:\Users\<vous>\AppData\Local\Programs\Python\Python310\python.exe" `
  -Python38Base "C:\Users\<vous>\AppData\Local\Programs\Python\Python38\python.exe"
```

## Pourquoi deux environnements

OpenSim/MyoConverter reste isolé sous Python 3.8. La capture, MuJoCo, MyoSuite et Stable-Baselines3 utilisent Python 3.10. Ne jamais exécuter un `pip install` sans appeler explicitement le Python de l’environnement concerné.

```powershell
.\.venv310\Scripts\python.exe -m pip check
```

## DLL OpenSim

Les scripts utilisent `OPENSIM_HOME` et ajoutent temporairement `bin`, `sdk\lib` et `sdk\Python\opensim` via `os.add_dll_directory`. Il n’est pas nécessaire de modifier globalement le `PATH` Windows.

## MyoConverter

Les métadonnées du commit MyoConverter retenu demandent actuellement `scipy>=1.11.1` et `pyvista>=0.40`. SciPy 1.11 ne fournit cependant pas de distribution Python 3.8. Cette combinaison est donc insoluble avec le résolveur pip, alors que le code du convertisseur a déjà été utilisé dans ce projet avec SciPy 1.10.1 et PyVista 0.38.6.

Le commit déclare également Python ≥3.9. Le script installe par conséquent la pile Python 3.8 compatible, puis MyoConverter avec `--no-deps --ignore-requires-python`. `pip check` signale logiquement les métadonnées non satisfaites ; dans cet environnement précis, le contrôle retenu est l’import OpenSim/MyoConverter suivi d’une conversion et de `src/mujoco/validate_model.py`. Ne pas modifier directement `site-packages`. Une future migration vers un OpenSim compatible Python ≥3.9 permettra de supprimer cette exception.

Les bindings OpenSim ne sont pas téléchargés depuis PyPI : le script installe le package local situé dans `%OPENSIM_HOME%\sdk\Python`.
L’environnement Python 3.8 conserve `pip==23.3.2`, compatible avec le `setup.py` historique livré par OpenSim 4.5.

## Vérification rapide

```powershell
.\.venv310\Scripts\python.exe -m unittest discover -s tests -v
.\.venv38\Scripts\python.exe -m pip check
```
