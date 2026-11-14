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
        # Rebuild when the package is missing or any source/asset is newer than it.
        $stale = -not (Test-Path 'dist/index.html')
        if (-not $stale) {
            $built = (Get-Item 'dist/index.html').LastWriteTimeUtc
            $sources = @('src', 'public', 'index.html', 'vite.config.js', 'scripts') | Where-Object { Test-Path $_ }
            $newer = Get-ChildItem -Path $sources -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTimeUtc -gt $built } | Select-Object -First 1
            if ($newer) { Write-Output "Sources changed ($($newer.Name)); rebuilding Tidewater."; $stale = $true }
        }
        if ($stale) {
            if (-not (Test-Path 'node_modules')) { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' } }
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Tidewater build failed.' }
        }
        & node (Join-Path $appRoot 'scripts/serve-static.mjs')
    }
    if ($LASTEXITCODE -ne 0) { throw 'Tidewater static server stopped with an error.' }
} finally { Pop-Location }
