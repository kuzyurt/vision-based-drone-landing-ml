param([switch]$Dev)
$ErrorActionPreference = 'Stop'
$appRoot = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'app'
Push-Location $appRoot
try {
    if ($Dev) {
        if (-not (Test-Path 'node_modules')) { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' } }
        Write-Output 'Open http://127.0.0.1:5189/ manually. Physics runs in your browser.'
        & npm.cmd run dev
    } else {
        if (-not (Test-Path 'dist/index.html')) {
            if (-not (Test-Path 'node_modules')) { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' } }
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Tidewater build failed.' }
        }
        & node (Join-Path $appRoot 'scripts/serve-static.mjs')
    }
    if ($LASTEXITCODE -ne 0) { throw 'Tidewater static server stopped with an error.' }
} finally { Pop-Location }
