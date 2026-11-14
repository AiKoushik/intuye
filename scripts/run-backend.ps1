<#
.SYNOPSIS
  Sets up the 'intuye' conda environment (first run) and starts the Intuye backend,
  which also serves the web test build at http://localhost:<port>/web/.

.EXAMPLE
  .\scripts\run-backend.ps1                    # create env if needed, start on port 8000, open the web build
.EXAMPLE
  .\scripts\run-backend.ps1 -Model local       # use your OpenAI-compatible server (Hearth/Ollama) from backend\.env
.EXAMPLE
  .\scripts\run-backend.ps1 -Model anthropic   # use Claude (set ANTHROPIC_API_KEY in backend\.env)
.EXAMPLE
  .\scripts\run-backend.ps1 -Test              # run the test suite first
.EXAMPLE
  .\scripts\run-backend.ps1 -Update            # reinstall/upgrade Python dependencies
.EXAMPLE
  .\scripts\run-backend.ps1 -BindHost 0.0.0.0  # reachable from your iPhone on the same Wi-Fi
#>
[CmdletBinding()]
param(
    [string]$EnvName = "intuye",
    [int]$Port = 8000,
    [string]$BindHost = "127.0.0.1",
    [ValidateSet("", "fake", "local", "anthropic")]
    [string]$Model = "",
    [switch]$Update,
    [switch]$Test,
    [switch]$NoReload,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Note([string]$Message) { Write-Host "    $Message" -ForegroundColor DarkGray }

# --- 1. Find conda (works without `conda init`, e.g. when launched from the .bat) -----------------
function Find-Conda {
    if ($env:CONDA_EXE -and (Test-Path $env:CONDA_EXE)) { return $env:CONDA_EXE }
    $cmd = Get-Command conda.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:USERPROFILE\miniconda3", "$env:USERPROFILE\anaconda3", "$env:USERPROFILE\miniforge3", "$env:USERPROFILE\mambaforge",
        "$env:LOCALAPPDATA\miniconda3", "$env:LOCALAPPDATA\anaconda3", "$env:LOCALAPPDATA\miniforge3",
        "$env:ProgramData\miniconda3", "$env:ProgramData\anaconda3", "$env:ProgramData\miniforge3",
        "C:\miniconda3", "C:\anaconda3", "C:\miniforge3"
    )
    foreach ($base in $candidates) {
        $exe = Join-Path $base "Scripts\conda.exe"
        if (Test-Path $exe) { return $exe }
    }
    return $null
}

$Conda = Find-Conda
if (-not $Conda) {
    throw "Couldn't find conda. Install Miniconda/Miniforge, or run this from an 'Anaconda PowerShell Prompt'."
}
Write-Step "Using conda at $Conda"

# --- 2. Create the environment on first run --------------------------------------------------------
$envList = (& $Conda env list --json | Out-String | ConvertFrom-Json).envs
$envExists = $false
foreach ($p in $envList) { if ((Split-Path $p -Leaf) -eq $EnvName) { $envExists = $true } }
if (-not $envExists) {
    Write-Step "Creating conda env '$EnvName' (Python 3.12) - first run only"
    & $Conda env create -n $EnvName -f (Join-Path $Backend "environment.yml")
    if ($LASTEXITCODE -ne 0) { throw "conda env create failed." }
    $Update = $true
}

# Run the env's own python directly: no activation needed, and Ctrl+C stops the server cleanly.
$Python = (& $Conda run -n $EnvName python -c "import sys; print(sys.executable)" | Out-String).Trim().Split("`n")[-1].Trim()
if (-not (Test-Path $Python)) { throw "Couldn't locate python in env '$EnvName' (got '$Python')." }
Write-Note "python: $Python"

# --- 3. Install dependencies (first run, -Update, or if something's missing) -----------------------
# (Windows PowerShell 5.1 turns redirected native stderr into errors, so relax EAP for this probe.)
$prevEap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
& $Python -c "import fastapi, langgraph, deepagents, numpy, sqlalchemy, aiosqlite, cbor2" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { $Update = $true }
$ErrorActionPreference = $prevEap
if ($Update) {
    Write-Step "Installing backend dependencies"
    & $Python -m pip install --upgrade pip --quiet
    & $Python -m pip install -e "$Backend[dev]"
    if ($LASTEXITCODE -ne 0) { throw "pip install failed." }
}

# --- 4. Local settings -----------------------------------------------------------------------------
$EnvFile = Join-Path $Backend ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Backend ".env.development") $EnvFile
    Write-Step "Created backend\.env from .env.development"
    Write-Note "Edit backend\.env to point LLM_BASE_URL / LLM_FAST_MODEL at Hearth, then run with -Model local."
}
# Local testing clicks fast; production limits stay in config.py.
if (-not $env:RATE_LIMIT_PER_MINUTE) { $env:RATE_LIMIT_PER_MINUTE = "600" }
if (-not $env:COACH_RATE_LIMIT_PER_MINUTE) { $env:COACH_RATE_LIMIT_PER_MINUTE = "120" }
switch ($Model) {
    "fake"      { $env:LLM_PROVIDER = "fake" }
    "local"     { $env:LLM_PROVIDER = "openai_compatible" }
    "anthropic" { $env:LLM_PROVIDER = "anthropic" }
}
$provider = if ($env:LLM_PROVIDER) { $env:LLM_PROVIDER } else {
    ((Get-Content $EnvFile | Where-Object { $_ -match '^\s*LLM_PROVIDER\s*=' } | Select-Object -First 1) -replace '^\s*LLM_PROVIDER\s*=\s*', '').Trim()
}
Write-Note "model provider: $provider"

# --- 5. Tests (optional) ---------------------------------------------------------------------------
Push-Location $Backend
try {
    if ($Test) {
        Write-Step "Running tests"
        & $Python -m pytest
        if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
    }

    # --- 6. Start the server -----------------------------------------------------------------------
    $busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($busy) { throw "Port $Port is already in use (a model server, or another backend?). Try -Port 8080." }

    $url = "http://localhost:$Port/web/"
    Write-Step "Starting backend on http://${BindHost}:$Port"
    Write-Note "web test build: $url"
    Write-Note "API docs:       http://localhost:$Port/docs"
    Write-Note "Ctrl+C to stop."
    if (-not $NoBrowser) {
        Start-Job -ScriptBlock { param($u) Start-Sleep -Seconds 4; Start-Process $u } -ArgumentList $url | Out-Null
    }
    $uvArgs = @("-m", "uvicorn", "app.main:app", "--host", $BindHost, "--port", "$Port")
    if (-not $NoReload) { $uvArgs += @("--reload", "--reload-dir", "app") }
    & $Python @uvArgs
}
finally {
    Pop-Location
}
