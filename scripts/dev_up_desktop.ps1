$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Stop-PortProcess {
    param([int]$Port)

    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pid in $connections) {
            if ($pid) {
                Write-Host "Killing existing process on port $Port (PID: $pid)..."
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
    }
    catch {
        Write-Warning "Could not inspect port $Port. Continuing."
    }
}

function Wait-ForHttp {
    param(
        [string]$Url,
        [int]$Attempts = 30,
        [int]$DelaySeconds = 1
    )

    Write-Host "Waiting for $Url ..."
    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            Write-Host "Ready: $Url"
            return $true
        }
        catch {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    Write-Warning "$Url did not become ready after $Attempts attempts."
    return $false
}

Write-Host "=== Cleaning up stale processes ==="
Stop-PortProcess -Port 8000
Stop-PortProcess -Port 3000

Write-Host "=== Setting up environment ==="

$backendDir = Join-Path $RepoRoot "backend"
$frontendDir = Join-Path $RepoRoot "frontend"
$electronDir = Join-Path $RepoRoot "electron"

$backendVenvDir = Join-Path $backendDir "venv"
$backendPython = Join-Path $backendVenvDir "Scripts\python.exe"

if (-not (Test-Path $backendVenvDir)) {
    Write-Host "Creating Python virtual environment..."
    try {
        & py -3.12 -m venv $backendVenvDir
    }
    catch {
        Write-Warning "py -3.12 failed, falling back to python -m venv"
        & python -m venv $backendVenvDir
    }

    & $backendPython -m pip install -r (Join-Path $backendDir "requirements.txt")
}
else {
    Write-Host "Python venv already exists, skipping..."
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $frontendDir
    try {
        & npm.cmd install
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "Frontend already installed, skipping..."
}

if (-not (Test-Path (Join-Path $electronDir "node_modules"))) {
    Write-Host "Installing Electron dependencies..."
    Push-Location $electronDir
    try {
        & npm.cmd install
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "Electron already installed, skipping..."
}

if (-not (Test-Path $backendPython)) {
    throw "Backend virtualenv is missing or incomplete: $backendPython"
}

Write-Host "=== Starting services ==="

$backendProc = Start-Process -FilePath $backendPython `
    -ArgumentList "-m", "uvicorn", "src.main:app", "--reload", "--port", "8000" `
    -WorkingDirectory $backendDir `
    -PassThru

Start-Sleep -Seconds 2

$frontendProc = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $frontendDir `
    -PassThru

Wait-ForHttp -Url "http://localhost:3000" | Out-Null

$electronCommand = 'set "ELECTRON_START_URL=http://localhost:3000" && set "ELECTRON_OPEN_DEVTOOLS=0" && npm.cmd run dev'
$electronProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", $electronCommand `
    -WorkingDirectory $electronDir `
    -PassThru

Write-Host ""
Write-Host "=== All services running ==="
Write-Host "  Backend:   http://localhost:8000"
Write-Host "  Frontend:  http://localhost:3000"
Write-Host "  Electron:  Desktop app window"
Write-Host ""
Write-Host "Close this PowerShell window or press Ctrl+C to stop all services"

try {
    Wait-Process -Id $electronProc.Id
}
finally {
    foreach ($proc in @($backendProc, $frontendProc, $electronProc)) {
        if ($proc -and -not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
