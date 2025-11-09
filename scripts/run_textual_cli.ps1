Param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$BackendDir = Join-Path $ProjectRoot "backend"
$VenvDir = Join-Path $BackendDir "venv"

Set-Location $BackendDir

if (-not (Test-Path $VenvDir)) {
    Write-Host "Backend virtualenv not found. Creating..."
    python -m venv $VenvDir
}

$ActivateScript = Join-Path $VenvDir "Scripts/Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
    throw "Unable to locate venv activation script at $ActivateScript"
}
. $ActivateScript

python -m src.cli.textual_app @ScriptArgs
