[CmdletBinding()]
param(
    [string]$OpenSimHome = "C:\OpenSim 4.5",
    [string]$Python310Base = "",
    [string]$Python38Base = "",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python310 = Join-Path $ProjectRoot ".venv310\Scripts\python.exe"
$Python38 = Join-Path $ProjectRoot ".venv38\Scripts\python.exe"

function Resolve-PythonVersion {
    param([string]$Version, [string]$ExplicitPath)
    $Digits = $Version.Replace(".", "")
    $Candidates = @()
    if ($ExplicitPath) { $Candidates += $ExplicitPath }
    $Candidates += Join-Path $env:LOCALAPPDATA "Programs\Python\Python$Digits\python.exe"
    $NamedCommand = Get-Command "python$Version" -ErrorAction SilentlyContinue
    if ($NamedCommand) { $Candidates += $NamedCommand.Source }
    foreach ($Candidate in $Candidates) {
        if (-not (Test-Path -LiteralPath $Candidate)) { continue }
        $Detected = & $Candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($LASTEXITCODE -eq 0 -and $Detected -eq $Version) { return $Candidate }
    }
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($Launcher) {
        $Candidate = & py "-$Version" -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $Candidate)) { return $Candidate }
    }
    throw "Python $Version est requis. Passez -Python${Digits}Base avec le chemin de python.exe."
}

Set-Location $ProjectRoot
$Python310Base = Resolve-PythonVersion "3.10" $Python310Base
$Python38Base = Resolve-PythonVersion "3.8" $Python38Base
Write-Host "Python 3.10: $Python310Base"
Write-Host "Python 3.8 : $Python38Base"

if (-not (Test-Path -LiteralPath $Python310)) {
    & $Python310Base -m venv (Join-Path $ProjectRoot ".venv310")
}
if (-not (Test-Path -LiteralPath $Python38)) {
    & $Python38Base -m venv (Join-Path $ProjectRoot ".venv38")
}

if (-not $SkipInstall) {
    & $Python310 -m pip install --upgrade pip
    & $Python310 -m pip install -r (Join-Path $ProjectRoot "requirements-py310.txt")
    # OpenSim 4.5 fournit encore un setup.py classique; garder une version pip compatible Python 3.8.
    & $Python38 -m pip install "pip==23.3.2" "wheel==0.41.3"
    & $Python38 -m pip install -r (Join-Path $ProjectRoot "requirements-py38-myoconverter.txt")
    $OpenSimPython = Join-Path $OpenSimHome "sdk\Python"
    if (-not (Test-Path -LiteralPath (Join-Path $OpenSimPython "setup.py"))) {
        throw "Bindings OpenSim introuvables dans $OpenSimPython"
    }
    & $Python38 -m pip install $OpenSimPython
    & $Python38 -m pip install --no-deps --ignore-requires-python "git+https://github.com/MyoHub/myoconverter.git@cadf38059367a51239e6dc28c9fbe8b8fbd5149f"
}

if ($SkipInstall) {
    Write-Host "Environnements crees; installation et imports ignores par -SkipInstall."
    exit 0
}

if (-not (Test-Path -LiteralPath $OpenSimHome)) {
    Write-Warning "OpenSim n'a pas ete trouve dans $OpenSimHome. Installez OpenSim 4.5 ou passez -OpenSimHome."
}

& $Python310 -m pip check
if ($LASTEXITCODE -ne 0) { throw "pip check Python 3.10 a echoue." }
& $Python310 -c "import cv2, mediapipe, mujoco, gymnasium, stable_baselines3, myosuite; print('Python 3.10: OK')"
if ($LASTEXITCODE -ne 0) { throw "Validation de l'environnement Python 3.10 echouee." }

$env:OPENSIM_HOME = $OpenSimHome
$OpenSimCommand = @"
import os, pathlib
home = pathlib.Path(os.environ['OPENSIM_HOME'])
for path in (home/'bin', home/'sdk'/'lib', home/'sdk'/'Python'/'opensim'):
    if path.exists(): os.add_dll_directory(str(path))
import opensim, myoconverter
print('Python 3.8 OpenSim/MyoConverter: OK')
"@
& $Python38 -c $OpenSimCommand
if ($LASTEXITCODE -ne 0) { throw "Validation de l'environnement Python 3.8 echouee." }

Write-Host "Installation terminee."
Write-Host "Capture/RL : .\.venv310\Scripts\Activate.ps1"
Write-Host "OpenSim    : .\.venv38\Scripts\Activate.ps1"
