param([ValidateRange(1, 65535)][int]$Port = 3000)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv/Scripts/python.exe'
$configPath = Join-Path $repoRoot 'config/openrouter/.env'
$dataPath = Join-Path $repoRoot 'backend/data'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install backend dependencies in .venv first.' }
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'build/index.html'))) { throw 'Run npm run build first.' }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "Port $Port is already in use." }
if (-not (Test-Path -LiteralPath $configPath)) {
    Copy-Item -LiteralPath (Join-Path $repoRoot 'config/openrouter/.env.example') -Destination $configPath
}
New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
$settings = @{}
foreach ($line in Get-Content -LiteralPath $configPath) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $settings[$Matches[1]] = $Matches[2].Trim() }
}
$secretPath = Join-Path $dataPath '.webui_secret_key'
if (-not $settings['WEBUI_SECRET_KEY']) {
    if (-not (Test-Path -LiteralPath $secretPath)) {
        $secretBytes = New-Object byte[] 32
        $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $generator.GetBytes($secretBytes) } finally { $generator.Dispose() }
        [System.IO.File]::WriteAllText($secretPath, [Convert]::ToBase64String($secretBytes))
    }
    $settings['WEBUI_SECRET_KEY'] = [System.IO.File]::ReadAllText($secretPath).Trim()
}
$settings['WEBUI_SECRET_KEY_FILE'] = $secretPath
$settings['DATA_DIR'] = $dataPath
$settings['DATABASE_URL'] = 'sqlite:///' + (Join-Path $dataPath 'webui.db').Replace('\', '/')
$settings['ENABLE_DB_MIGRATIONS'] = 'true'
$settings['USE_SLIM_DOCKER'] = 'true'
$settings['OFFLINE_MODE'] = 'true'
$settings['ENV'] = 'prod'
$previous = @{}
try {
    foreach ($name in $settings.Keys) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process')
    }
    $serverProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'uvicorn', 'open_webui.main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', "$Port") -WorkingDirectory $repoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $dataPath 'openrouter-server.log') -RedirectStandardError (Join-Path $dataPath 'openrouter-server.error.log') -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline -and -not $serverProcess.HasExited) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
            if ($health.status) { $ready = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw "Server did not become ready. See $dataPath/openrouter-server.error.log" }
    # The Windows venv launcher can spawn another Python process that owns the listener.
    $listenerProcessId = (Get-NetTCPConnection -LocalPort $Port -State Listen | Select-Object -First 1).OwningProcess
    [System.IO.File]::WriteAllText((Join-Path $dataPath 'openrouter-server.pid'), "$listenerProcessId")
    Write-Output "Open WebUI ready as PID ${listenerProcessId}: http://localhost:$Port"
    Write-Output "Logs: $dataPath/openrouter-server.error.log"
} finally {
    foreach ($name in $previous.Keys) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
}
