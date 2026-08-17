param(
    [string]$PythonPath = ".\.venv310\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Interpreteur Python introuvable: $PythonPath"
}

function Invoke-PipelineStep {
    param(
        [string]$Name,
        [string[]]$Arguments
    )
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    & $PythonPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Etape '$Name' echouee avec le code $LASTEXITCODE"
    }
}

Invoke-PipelineStep "Mouvement V2 et cible MuJoCo" @(
    ".\scripts\run_motion_v2.py"
)
Invoke-PipelineStep "Optimisation passive" @(
    ".\src\mujoco\optimize_passive_assistance.py"
)
Invoke-PipelineStep "Generation des modeles optimises" @(
    ".\src\mujoco\build_hybrid_exoskeleton.py",
    "--config", "config\exoskeleton\hybrid_optimized_v2.json"
)
Invoke-PipelineStep "Validation du modele hybride" @(
    ".\src\mujoco\validate_model.py",
    "--model", "models\mujoco\exoskeleton\hybrid_optimized_v2.xml",
    "--output", "data\results\hybrid_optimized_v2_quality.json"
)
Invoke-PipelineStep "Evaluation classique prescrite" @(
    ".\src\mujoco\evaluate_classical_assistance.py",
    "--config", "config\controllers\classical_assistance_optimized_v2.json"
)
Invoke-PipelineStep "Controle dynamique ferme" @(
    ".\src\mujoco\run_closed_loop_controller.py",
    "--config", "config\controllers\closed_loop_v1.json"
)
Invoke-PipelineStep "Tests automatiques" @(
    "-m", "unittest", "discover", "-s", "tests", "-v"
)

Write-Host "`nPipeline experimental V2 termine avec succes." -ForegroundColor Green
Write-Host "Les resultats restent exploratoires et ne debloquent pas OpenSim quantitatif."
