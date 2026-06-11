$ErrorActionPreference = "Stop"

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

$exePath = Join-Path $PSScriptRoot "dist\TukushiNote.exe"
$runningProcesses = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    try {
        $_.Path -eq $exePath
    } catch {
        $false
    }
}

if ($runningProcesses) {
    $processIds = ($runningProcesses | ForEach-Object { $_.Id }) -join ", "
    throw "TukushiNote.exe is running. Close it before building. PID: $processIds"
}

Invoke-NativeCommand { python -m pip install -r requirements.txt }
Invoke-NativeCommand { python -m pip install -r requirements-dev.txt }
Invoke-NativeCommand { python -m PyInstaller --clean --noconfirm TukushiNote.spec }

Write-Host "Build complete: dist\TukushiNote.exe"
