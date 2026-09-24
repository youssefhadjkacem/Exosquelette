param(
    [string]$PythonPath = ".\.venv310\Scripts\python.exe",
    [switch]$RefreshExtraction
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

if ($RefreshExtraction) {
    Invoke-Step "Extraction et validation V1 de video1" @(
        ".\scripts\run_scenario.py", "--config", "config\scenarios\video1_v1.json", "--report-on-fail"
    )
    Invoke-Step "Extraction et validation V1 de test1" @(
        ".\scripts\run_scenario.py", "--config", "config\scenarios\test1_v1.json", "--report-on-fail"
    )
}

Invoke-Step "Reconstruction V2 de video1" @(
    ".\scripts\run_motion_v2.py", "--config", "config\scenarios\video1_v2.json"
)
Invoke-Step "Reconstruction V2 de test1" @(
    ".\scripts\run_motion_v2.py", "--config", "config\scenarios\test1_v2.json", "--report-on-fail"
)
Invoke-Step "Comparaison et rapport" @(
    ".\scripts\compare_motion_v2.py"
)
Invoke-Step "Tests automatiques" @(
    "-m", "unittest", "discover", "-s", "tests", "-v"
)

Write-Host "`nComparaison V2 terminee." -ForegroundColor Green
Write-Host "Rapport: data\scenarios\scenarios_secondaires\comparaison_video_principale_vs_secondaire\comparison_report.md"
Write-Host "Une video en echec reste bloquee pour OpenSim, MuJoCo et RL."
