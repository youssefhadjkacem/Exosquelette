param(
    [string]$PythonPath = ".\.venv310\Scripts\python.exe",
    [switch]$TrainRL,
    [int]$TrainingTimesteps = 10000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Interpreteur Python introuvable: $PythonPath"
}

function Invoke-Step {
    param([string]$Name, [string[]]$Arguments)
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    & $PythonPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Etape '$Name' echouee avec le code $LASTEXITCODE"
    }
}

Invoke-Step "Verification du gabarit d'acquisition V3" @(
    ".\src\acquisition\validate_v3_session.py"
)
Invoke-Step "Generation de la trajectoire synthetique" @(
    ".\src\rl\generate_synthetic_target.py"
)
Invoke-Step "Validation du modele MuJoCo simplifie" @(
    ".\src\mujoco\validate_model.py",
    "--model", "models\mujoco\sandbox\two_dof_ironing_v1.xml",
    "--output", "data\results\rl_sandbox_model_quality.json"
)
Invoke-Step "Evaluation des baselines RL exploratoires" @(
    ".\src\rl\evaluate_exploratory_baselines.py"
)
Invoke-Step "Tests automatiques" @(
    "-m", "unittest", "discover", "-s", "tests", "-v"
)

if ($TrainRL) {
    Invoke-Step "Entrainement PPO logiciel" @(
        ".\src\rl\train_exploratory_ppo.py",
        "--timesteps", "$TrainingTimesteps",
        "--acknowledge", "software-only-no-scientific-claim"
    )
}

Write-Host "`nPreparation hors camera terminee." -ForegroundColor Green
Write-Host "Le protocole V3 attend les videos; les resultats RL restent logiciels et exploratoires."
