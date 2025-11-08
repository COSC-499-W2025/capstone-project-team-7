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

$env:PIP_BREAK_SYSTEM_PACKAGES = "1"

$pipList = python -m pip list --format=freeze
if (($pipList -notmatch "^questionary==") -or ($pipList -notmatch "^rich==")) {
    Write-Host "Installing CLI dependencies..."
    python -m pip install -r requirements.txt | Out-Null
}

$EnvFile = Join-Path $ProjectRoot ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^\s*#" -or [string]::IsNullOrWhiteSpace($_)) {
            return
        }
        $pair = $_ -split '=', 2
        if ($pair.Length -eq 2) {
            $name = $pair[0].Trim()
            $value = $pair[1].Trim().Trim("'\"")
            if ($name) {
                $env:$name = $value
            }
        }
    }
}

Write-Host "Launching CLI... (press Ctrl+C to exit)"
python -m src.cli.app @ScriptArgs
