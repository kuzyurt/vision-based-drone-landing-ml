$ErrorActionPreference = 'Stop'
$gameRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Join-Path $gameRoot 'app'
$runtimeRoot = Join-Path $gameRoot 'simulation\runtime'
$wslDistro = if ($env:PX4_WSL_DISTRO) { $env:PX4_WSL_DISTRO } else { 'Ubuntu-22.04' }
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null

$backend = Get-NetTCPConnection -State Listen -LocalPort 5195 -ErrorAction SilentlyContinue
if ($backend) {
    try { $null = Invoke-RestMethod 'http://127.0.0.1:5195/api/status' -TimeoutSec 2 }
    catch {
        $relayPidFile = Join-Path $runtimeRoot 'relay.pid'
        if (-not (Test-Path $relayPidFile)) { throw 'Port 5195 is occupied by an unavailable service.' }
        $relayProcessId = [int](Get-Content $relayPidFile)
        $relayProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$relayProcessId"
        if ($relayProcess -and $relayProcess.CommandLine -match 'simulation[\\/]relay\.cjs') {
            Stop-Process -Id $relayProcessId
            $backend = $null
        } else { throw 'Port 5195 is occupied by an unavailable service.' }
    }
}
if (-not $backend) {
    $physicsBase = Join-Path $runtimeRoot 'physics-base-linux.xml'
    if (-not (Test-Path $physicsBase)) {
        $physicsPython = Join-Path $gameRoot 'simulation\.venv\Scripts\python.exe'
        if (-not (Test-Path $physicsPython)) { $physicsPython = 'python' }
        Write-Output 'Preparing the original collision model and CAD transforms for the Linux physics service.'
        & $physicsPython (Join-Path $gameRoot 'simulation\prepare_physics.py')
        if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the original MuJoCo collision model.' }
    }
    $backendLog = Join-Path $runtimeRoot 'backend.log'
    $backendError = Join-Path $runtimeRoot 'backend-error.log'
    $linuxGameRoot = (& wsl.exe -d $wslDistro -- wslpath -u $gameRoot.Replace('\', '/')).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Could not locate Tidewater in WSL.' }
    $linuxProject = $linuxGameRoot.Substring(0, $linuxGameRoot.LastIndexOf('/'))
    $wslIP = ((& wsl.exe -d $wslDistro -- hostname -I).Trim() -split '\s+')[0]
    $parsedIP = $null
    if (-not [System.Net.IPAddress]::TryParse($wslIP, [ref]$parsedIP)) { throw 'Could not resolve the WSL service address.' }
    Write-Output 'Preparing the compiled physics service beside PX4 in WSL. First setup installs its isolated dependencies.'
    Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d', $wslDistro, '--', 'env', "TIDEWATER_LISTEN_HOST=$wslIP", 'bash', "$linuxGameRoot/simulation/start-service.sh", $linuxProject) `
        -WorkingDirectory $gameRoot -WindowStyle Hidden -RedirectStandardOutput $backendLog `
        -RedirectStandardError $backendError | Out-Null
    Start-Process -FilePath 'node' -ArgumentList @((Join-Path $gameRoot 'simulation\relay.cjs'), $wslIP) `
        -WorkingDirectory $gameRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeRoot 'relay.log') `
        -RedirectStandardError (Join-Path $runtimeRoot 'relay-error.log') | Out-Null
}

$vite = Get-NetTCPConnection -State Listen -LocalPort 5189 -ErrorAction SilentlyContinue
if (-not $vite) {
    $viteLog = Join-Path $runtimeRoot 'vite.log'
    $viteError = Join-Path $runtimeRoot 'vite-error.log'
    Start-Process -FilePath 'npm.cmd' -ArgumentList @('run', 'dev') -WorkingDirectory $appRoot `
        -WindowStyle Hidden -RedirectStandardOutput $viteLog -RedirectStandardError $viteError | Out-Null
}

$ready = $false
for ($attempt = 0; $attempt -lt 240; $attempt++) {
    try {
        $null = Invoke-WebRequest -Uri 'http://127.0.0.1:5195/api/status' -TimeoutSec 2
        $null = Invoke-WebRequest -Uri 'http://127.0.0.1:5189/' -TimeoutSec 2
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $ready) { throw 'The Tidewater services did not start. See the backend-error.log and vite-error.log files in tidewater-game/simulation/runtime.' }
Write-Output 'Tidewater services are running. Open http://127.0.0.1:5189/ yourself and wait for the original simulator camera before taking off.'
