[CmdletBinding()]
param(
    [ValidateSet('Quick', 'Standard', 'Full')]
    [string]$Mode = 'Standard',

    [ValidateRange(30, 7200)]
    [int]$CommandTimeoutSeconds = 900,

    [string]$LogDirectory = 'validation-reports',

    [switch]$SkipDjangoTests,
    [switch]$SkipFastApiTests,
    [switch]$SkipFrontendBuild,
    [switch]$SkipDatabaseChecks,
    [switch]$RunSecurityAudit,
    [switch]$Strict,
    [switch]$NoColor
)

# -----------------------------------------------------------------------------
# Real State project validator
# Compatible with Windows PowerShell 5.1 and PowerShell 7+
# Read-only validation: this script never runs migrate, makemigrations without
# --check, npm install, database reset, or any command that changes app data.
# -----------------------------------------------------------------------------

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DjangoDir = Join-Path $Root 'backend\django_core'
$FastApiDir = Join-Path $Root 'backend\fastapi_core'
$FrontendDir = Join-Path $Root 'frontend'
$ReportsDir = Join-Path $Root $LogDirectory
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$RunDir = Join-Path $ReportsDir $Timestamp
$script:Results = New-Object System.Collections.Generic.List[object]
$script:PythonExe = $null
$script:NpmExe = $null
$script:StartedAt = Get-Date
$script:UseColor = -not $NoColor

New-Item -ItemType Directory -Path $RunDir -Force | Out-Null

function Write-Status {
    param([string]$Message, [string]$Color = 'Gray')
    if ($script:UseColor) { Write-Host $Message -ForegroundColor $Color }
    else { Write-Host $Message }
}

function Add-Result {
    param(
        [string]$Name,
        [string]$Status,
        [int]$ExitCode = 0,
        [double]$DurationSeconds = 0,
        [string]$Details = '',
        [string]$StdOut = '',
        [string]$StdErr = ''
    )
    $item = [pscustomobject]@{
        name = $Name
        status = $Status
        exit_code = $ExitCode
        duration_seconds = [math]::Round($DurationSeconds, 2)
        details = $Details
        stdout_log = $StdOut
        stderr_log = $StdErr
    }
    $script:Results.Add($item)
    $color = switch ($Status) {
        'PASS' { 'Green' }
        'FAIL' { 'Red' }
        'WARN' { 'Yellow' }
        default { 'DarkYellow' }
    }
    Write-Status (('[{0}] {1} ({2}s)' -f $Status, $Name, $item.duration_seconds)) $color
    if ($Details) { Write-Status ('       ' + $Details) 'DarkGray' }
}

function Add-Skipped {
    param([string]$Name, [string]$Reason, [string]$Status = 'SKIP')
    Add-Result -Name $Name -Status $Status -Details $Reason
}

function Quote-NativeArgument {
    param([AllowEmptyString()][string]$Value)
    if ($null -eq $Value) { return '""' }
    if ($Value.Length -eq 0) { return '""' }
    if ($Value -notmatch '[\s"]') { return $Value }
    # Windows command-line quoting (CommandLineToArgvW compatible).
    $builder = New-Object System.Text.StringBuilder
    [void]$builder.Append('"')
    $slashes = 0
    foreach ($ch in $Value.ToCharArray()) {
        if ($ch -eq [char]92) { $slashes++; continue }
        if ($ch -eq [char]34) {
            if ($slashes -gt 0) { [void]$builder.Append(([string][char]92) * (2 * $slashes)) }
            [void]$builder.Append([char]92)
            [void]$builder.Append([char]34)
            $slashes = 0
            continue
        }
        if ($slashes -gt 0) { [void]$builder.Append(([string][char]92) * $slashes); $slashes = 0 }
        [void]$builder.Append($ch)
    }
    if ($slashes -gt 0) { [void]$builder.Append(([string][char]92) * (2 * $slashes)) }
    [void]$builder.Append('"')
    return $builder.ToString()
}

function Resolve-Executables {
    $pythonCandidates = @(
        (Join-Path $Root '.venv\Scripts\python.exe'),
        (Join-Path $Root 'venv\Scripts\python.exe'),
        (Join-Path $Root 'backend\.venv\Scripts\python.exe'),
        (Join-Path $DjangoDir '.venv\Scripts\python.exe'),
        (Join-Path $FastApiDir '.venv\Scripts\python.exe')
    )
    foreach ($candidate in $pythonCandidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { $script:PythonExe = $candidate; break }
    }
    if (-not $script:PythonExe) {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) { $script:PythonExe = $cmd.Source }
    }
    if (-not $script:PythonExe) {
        $cmd = Get-Command python3 -ErrorAction SilentlyContinue
        if ($cmd) { $script:PythonExe = $cmd.Source }
    }

    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($npm) { $script:NpmExe = $npm.Source }
    if (-not $script:NpmExe) {
        $npm = Get-Command npm -ErrorAction SilentlyContinue
        if ($npm) { $script:NpmExe = $npm.Source }
    }
}

function Invoke-ExternalCheck {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [int]$TimeoutSeconds = $CommandTimeoutSeconds,
        [switch]$Optional
    )

    if (-not (Test-Path -LiteralPath $WorkingDirectory -PathType Container)) {
        Add-Skipped -Name $Name -Reason ("Working directory not found: {0}" -f $WorkingDirectory) -Status $(if ($Optional) { 'SKIP' } else { 'FAIL' })
        return
    }
    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf) -and -not (Get-Command $FilePath -ErrorAction SilentlyContinue)) {
        Add-Skipped -Name $Name -Reason ("Executable not found: {0}" -f $FilePath) -Status $(if ($Optional) { 'SKIP' } else { 'FAIL' })
        return
    }

    $safeName = ($Name -replace '[^A-Za-z0-9_-]', '_')
    $stdoutPath = Join-Path $RunDir ($safeName + '.stdout.log')
    $stderrPath = Join-Path $RunDir ($safeName + '.stderr.log')
    $argLine = (($Arguments | ForEach-Object { Quote-NativeArgument ([string]$_) }) -join ' ')
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $process = $null
    try {
        $startParams = @{
            FilePath = $FilePath
            ArgumentList = $argLine
            WorkingDirectory = $WorkingDirectory
            RedirectStandardOutput = $stdoutPath
            RedirectStandardError = $stderrPath
            PassThru = $true
        }
        if ($env:OS -eq 'Windows_NT') { $startParams['WindowStyle'] = 'Hidden' }
        $process = Start-Process @startParams
        $finished = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $finished) {
            try {
                if ($env:OS -eq 'Windows_NT') {
                    & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null
                } else {
                    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                }
            } catch { }
            $timer.Stop()
            Add-Result -Name $Name -Status 'FAIL' -ExitCode 124 -DurationSeconds $timer.Elapsed.TotalSeconds `
                -Details ("Timed out after {0} seconds; process was terminated." -f $TimeoutSeconds) `
                -StdOut $stdoutPath -StdErr $stderrPath
            return
        }
        $process.WaitForExit()
        $timer.Stop()
        $exit = [int]$process.ExitCode
        if ($exit -eq 0) {
            Add-Result -Name $Name -Status 'PASS' -ExitCode 0 -DurationSeconds $timer.Elapsed.TotalSeconds -StdOut $stdoutPath -StdErr $stderrPath
        } else {
            Add-Result -Name $Name -Status 'FAIL' -ExitCode $exit -DurationSeconds $timer.Elapsed.TotalSeconds `
                -Details ("See log files: {0} and {1}" -f (Split-Path -Leaf $stdoutPath), (Split-Path -Leaf $stderrPath)) `
                -StdOut $stdoutPath -StdErr $stderrPath
        }
    } catch {
        $timer.Stop()
        Add-Result -Name $Name -Status 'FAIL' -ExitCode 1 -DurationSeconds $timer.Elapsed.TotalSeconds `
            -Details $_.Exception.Message -StdOut $stdoutPath -StdErr $stderrPath
    } finally {
        if ($process) { $process.Dispose() }
    }
}

function Invoke-PythonCheck {
    param([string]$Name, [string[]]$Arguments, [string]$WorkingDirectory, [switch]$Optional)
    if (-not $script:PythonExe) {
        Add-Skipped -Name $Name -Reason 'Python interpreter was not found. Activate the project virtual environment or install Python.' -Status $(if ($Optional) { 'SKIP' } else { 'FAIL' })
        return
    }
    Invoke-ExternalCheck -Name $Name -FilePath $script:PythonExe -Arguments $Arguments -WorkingDirectory $WorkingDirectory -Optional:$Optional
}

function Invoke-NpmCheck {
    param([string]$Name, [string[]]$Arguments, [switch]$Optional)
    if (-not $script:NpmExe) {
        Add-Skipped -Name $Name -Reason 'npm was not found. Install Node.js and npm.' -Status $(if ($Optional) { 'SKIP' } else { 'FAIL' })
        return
    }
    Invoke-ExternalCheck -Name $Name -FilePath $script:NpmExe -Arguments $Arguments -WorkingDirectory $FrontendDir -Optional:$Optional
}

function Test-PackageScript {
    param([string]$ScriptName)
    $packagePath = Join-Path $FrontendDir 'package.json'
    if (-not (Test-Path $packagePath)) { return $false }
    try {
        $package = Get-Content -LiteralPath $packagePath -Raw | ConvertFrom-Json
        return ($null -ne $package.scripts -and $null -ne $package.scripts.$ScriptName)
    } catch { return $false }
}

function Write-Reports {
    $ended = Get-Date
    $failed = @($script:Results | Where-Object { $_.status -eq 'FAIL' })
    $warnings = @($script:Results | Where-Object { $_.status -eq 'WARN' })
    $skipped = @($script:Results | Where-Object { $_.status -eq 'SKIP' })
    $passed = @($script:Results | Where-Object { $_.status -eq 'PASS' })
    $summary = [pscustomobject]@{
        project = 'real_state'
        mode = $Mode
        started_at = $script:StartedAt.ToString('o')
        finished_at = $ended.ToString('o')
        duration_seconds = [math]::Round(($ended - $script:StartedAt).TotalSeconds, 2)
        result = $(if ($failed.Count -gt 0 -or ($Strict -and $warnings.Count -gt 0)) { 'FAILED' } else { 'COMPLETED' })
        counts = [pscustomobject]@{ passed = $passed.Count; failed = $failed.Count; warnings = $warnings.Count; skipped = $skipped.Count }
        checks = @($script:Results.ToArray())
    }
    $jsonPath = Join-Path $RunDir 'summary.json'
    $mdPath = Join-Path $RunDir 'summary.md'
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('# Real State - Validation Report')
    $lines.Add('')
    $lines.Add(('- Mode: **{0}**' -f $Mode))
    $lines.Add(('- Result: **{0}**' -f $summary.result))
    $lines.Add(('- Started: `{0}`' -f $summary.started_at))
    $lines.Add(('- Finished: `{0}`' -f $summary.finished_at))
    $lines.Add(('- Duration: **{0}s**' -f $summary.duration_seconds))
    $lines.Add('')
    $lines.Add('| Status | Count |')
    $lines.Add('|---|---:|')
    $lines.Add(('| PASS | {0} |' -f $passed.Count))
    $lines.Add(('| FAIL | {0} |' -f $failed.Count))
    $lines.Add(('| WARN | {0} |' -f $warnings.Count))
    $lines.Add(('| SKIP | {0} |' -f $skipped.Count))
    $lines.Add('')
    $lines.Add('| Check | Status | Exit | Duration (s) | Details |')
    $lines.Add('|---|---|---:|---:|---|')
    foreach ($item in $script:Results) {
        $detail = ([string]$item.details -replace '\|', '\|' -replace '[\r\n]+', ' ')
        $lines.Add(('| {0} | {1} | {2} | {3} | {4} |' -f $item.name, $item.status, $item.exit_code, $item.duration_seconds, $detail))
    }
    $lines.Add('')
    $lines.Add('## Logs')
    $lines.Add('')
    $lines.Add('Each executed check has separate `.stdout.log` and `.stderr.log` files in this report directory.')
    $lines.Add('No `.env` values or credentials are collected or written to the report.')
    $lines | Set-Content -LiteralPath $mdPath -Encoding UTF8
    return [pscustomobject]@{ Json = $jsonPath; Markdown = $mdPath; Failed = $failed.Count; Warnings = $warnings.Count }
}

# --- Start -------------------------------------------------------------------
Write-Status '============================================================' 'Cyan'
Write-Status ' REAL STATE | PROJECT VALIDATION' 'Cyan'
Write-Status (' Mode: {0} | Timeout per command: {1}s' -f $Mode, $CommandTimeoutSeconds) 'Cyan'
Write-Status (' Root: {0}' -f $Root) 'DarkGray'
Write-Status '============================================================' 'Cyan'

# Preflight: expected project layout.
foreach ($pathInfo in @(
    @{ Name = 'Django project directory'; Path = $DjangoDir },
    @{ Name = 'FastAPI project directory'; Path = $FastApiDir },
    @{ Name = 'Frontend project directory'; Path = $FrontendDir }
)) {
    if (Test-Path -LiteralPath $pathInfo.Path -PathType Container) {
        Add-Result -Name ('Preflight: ' + $pathInfo.Name) -Status 'PASS'
    } else {
        Add-Result -Name ('Preflight: ' + $pathInfo.Name) -Status 'FAIL' -ExitCode 1 -Details $pathInfo.Path
    }
}

Resolve-Executables
if ($script:PythonExe) { Add-Result -Name 'Preflight: Python interpreter' -Status 'PASS' -Details $script:PythonExe }
else { Add-Result -Name 'Preflight: Python interpreter' -Status 'FAIL' -ExitCode 1 -Details 'Python was not found on PATH or in common project virtual-environment locations.' }
if ($script:NpmExe) { Add-Result -Name 'Preflight: npm' -Status 'PASS' -Details $script:NpmExe }
else { Add-Skipped -Name 'Preflight: npm' -Reason 'Node.js/npm not found; frontend checks cannot run.' -Status 'WARN' }

if (Test-Path (Join-Path $Root '.env.example')) {
    Add-Result -Name 'Preflight: .env.example' -Status 'PASS'
} else {
    Add-Skipped -Name 'Preflight: .env.example' -Reason '.env.example was not found.' -Status 'WARN'
}
if (Test-Path (Join-Path $Root '.env')) {
    Add-Result -Name 'Preflight: local .env file' -Status 'PASS' -Details 'File exists; its contents were not read or logged.'
} else {
    Add-Skipped -Name 'Preflight: local .env file' -Reason 'No root .env file detected. Environment may be supplied externally.' -Status 'WARN'
}

# Python source syntax validation without generating __pycache__ files.
$syntaxCode = @'
import ast, pathlib, sys
root = pathlib.Path(sys.argv[1])
files = [p for p in root.rglob("*.py") if not any(x in {".venv", "venv", "__pycache__", ".pytest_cache", "site-packages"} for x in p.parts)]
errors = []
for path in files:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as exc:
        errors.append((path, exc))
for path, exc in errors:
    print(f"SYNTAX ERROR: {path}: {exc}")
print(f"Checked {len(files)} Python source files; syntax errors: {len(errors)}")
sys.exit(1 if errors else 0)
'@
if ($script:PythonExe) {
    Invoke-PythonCheck -Name 'Python syntax: Django source' -Arguments @('-c', $syntaxCode, $DjangoDir) -WorkingDirectory $Root
    Invoke-PythonCheck -Name 'Python syntax: FastAPI source' -Arguments @('-c', $syntaxCode, $FastApiDir) -WorkingDirectory $Root
} else {
    Add-Skipped -Name 'Python source syntax checks' -Reason 'Python interpreter unavailable.' -Status 'FAIL'
}

# Django checks.
if ((Test-Path (Join-Path $DjangoDir 'manage.py')) -and $script:PythonExe) {
    Invoke-PythonCheck -Name 'Django system checks' -Arguments @('manage.py', 'check') -WorkingDirectory $DjangoDir
    if ($Mode -ne 'Quick') {
        Invoke-PythonCheck -Name 'Django migration drift (read-only)' -Arguments @('manage.py', 'makemigrations', '--check', '--dry-run') -WorkingDirectory $DjangoDir
        if ($SkipDatabaseChecks) {
            Add-Skipped -Name 'Django migration plan' -Reason 'Disabled by -SkipDatabaseChecks.'
            Add-Skipped -Name 'Django database schema diagnostic' -Reason 'Disabled by -SkipDatabaseChecks.'
        } else {
            Invoke-PythonCheck -Name 'Django migration plan (read-only)' -Arguments @('manage.py', 'migrate', '--plan') -WorkingDirectory $DjangoDir
            $diagnostic = Join-Path $DjangoDir 'apps\settings\management\commands\diagnose_schema.py'
            if (Test-Path $diagnostic) {
                Invoke-PythonCheck -Name 'Django database schema diagnostic (read-only)' -Arguments @('manage.py', 'diagnose_schema') -WorkingDirectory $DjangoDir
            } else {
                Add-Skipped -Name 'Django database schema diagnostic' -Reason 'Custom diagnose_schema management command is not present.' -Status 'WARN'
            }
        }
    } else {
        Add-Skipped -Name 'Django migration drift (read-only)' -Reason 'Not included in Quick mode.'
        Add-Skipped -Name 'Django migration plan' -Reason 'Not included in Quick mode.'
        Add-Skipped -Name 'Django database schema diagnostic' -Reason 'Not included in Quick mode.'
    }
    if ($Mode -eq 'Full' -and -not $SkipDjangoTests) {
        Invoke-PythonCheck -Name 'Django pytest suite' -Arguments @('-m', 'pytest', 'tests', '-q') -WorkingDirectory $DjangoDir
    } else {
        Add-Skipped -Name 'Django pytest suite' -Reason $(if ($SkipDjangoTests) { 'Disabled by -SkipDjangoTests.' } else { 'Run with -Mode Full.' })
    }
} else {
    Add-Skipped -Name 'Django checks' -Reason 'Django manage.py or Python interpreter is unavailable.' -Status 'FAIL'
}

# FastAPI checks and tests.
if ((Test-Path (Join-Path $FastApiDir 'app')) -and $script:PythonExe) {
    if ($Mode -eq 'Full' -and -not $SkipFastApiTests) {
        Invoke-PythonCheck -Name 'FastAPI pytest suite' -Arguments @('-m', 'pytest', 'tests', '-q') -WorkingDirectory $FastApiDir
    } else {
        Add-Skipped -Name 'FastAPI pytest suite' -Reason $(if ($SkipFastApiTests) { 'Disabled by -SkipFastApiTests.' } else { 'Run with -Mode Full.' })
    }
} else {
    Add-Skipped -Name 'FastAPI pytest suite' -Reason 'FastAPI app directory or Python interpreter is unavailable.' -Status 'WARN'
}

# Frontend checks. This repository defines lint=tsc --noEmit and has no test script.
$nodeModules = Join-Path $FrontendDir 'node_modules'
$packageJson = Join-Path $FrontendDir 'package.json'
if ((Test-Path $packageJson) -and $script:NpmExe) {
    if (Test-Path $nodeModules) {
        Invoke-NpmCheck -Name 'Frontend TypeScript (npm run lint)' -Arguments @('run', 'lint')
        if ($Mode -eq 'Full' -and -not $SkipFrontendBuild) {
            Invoke-NpmCheck -Name 'Frontend production build' -Arguments @('run', 'build')
        } else {
            Add-Skipped -Name 'Frontend production build' -Reason $(if ($SkipFrontendBuild) { 'Disabled by -SkipFrontendBuild.' } else { 'Run with -Mode Full.' })
        }
        if (Test-PackageScript -ScriptName 'test:ci') {
            if ($Mode -eq 'Full') { Invoke-NpmCheck -Name 'Frontend automated tests' -Arguments @('run', 'test:ci') }
            else { Add-Skipped -Name 'Frontend automated tests' -Reason 'A test:ci script exists; run with -Mode Full.' }
        } else {
            Add-Skipped -Name 'Frontend automated tests' -Reason 'No test:ci script is defined in frontend/package.json; no test command was guessed.' -Status 'WARN'
        }
    } else {
        Add-Skipped -Name 'Frontend TypeScript (npm run lint)' -Reason 'frontend/node_modules is absent. Run npm ci manually before validation.' -Status 'WARN'
        Add-Skipped -Name 'Frontend production build' -Reason 'frontend/node_modules is absent.' -Status 'WARN'
        Add-Skipped -Name 'Frontend automated tests' -Reason 'frontend/node_modules is absent.' -Status 'WARN'
    }
} else {
    Add-Skipped -Name 'Frontend checks' -Reason 'package.json or npm is unavailable.' -Status 'WARN'
}

# Optional dependency/security audits (network access may be required).
if ($RunSecurityAudit) {
    if ($script:PythonExe) {
        $pipAudit = Get-Command pip-audit -ErrorAction SilentlyContinue
        if ($pipAudit) {
            Invoke-ExternalCheck -Name 'Python dependency audit: Django requirements' -FilePath $pipAudit.Source -Arguments @('-r', (Join-Path $DjangoDir 'requirements.txt')) -WorkingDirectory $DjangoDir
            Invoke-ExternalCheck -Name 'Python dependency audit: FastAPI requirements' -FilePath $pipAudit.Source -Arguments @('-r', (Join-Path $FastApiDir 'requirements.txt')) -WorkingDirectory $FastApiDir
        } else {
            Add-Skipped -Name 'Python dependency audit (pip-audit)' -Reason 'pip-audit is not installed.' -Status 'WARN'
        }
    }
    if ($script:NpmExe -and (Test-Path (Join-Path $FrontendDir 'package-lock.json')) -and (Test-Path $nodeModules)) {
        Invoke-NpmCheck -Name 'Frontend dependency audit (npm audit)' -Arguments @('audit', '--omit=dev')
    } else {
        Add-Skipped -Name 'Frontend dependency audit (npm audit)' -Reason 'npm, package-lock.json, or node_modules is unavailable.' -Status 'WARN'
    }
} else {
    Add-Skipped -Name 'Dependency security audits' -Reason 'Optional; enable with -RunSecurityAudit.'
}

# Git whitespace/conflict check; no repository state is changed.
$git = Get-Command git -ErrorAction SilentlyContinue
if ($git -and (Test-Path (Join-Path $Root '.git'))) {
    Invoke-ExternalCheck -Name 'Git whitespace check (diff --check)' -FilePath $git.Source -Arguments @('diff', '--check') -WorkingDirectory $Root
} else {
    Add-Skipped -Name 'Git whitespace check (diff --check)' -Reason 'Git executable or .git directory not found.' -Status 'WARN'
}

$report = Write-Reports
Write-Status ''
Write-Status '======================= SUMMARY ===========================' 'Cyan'
$passCount = @($script:Results | Where-Object { $_.status -eq 'PASS' }).Count
$failCount = @($script:Results | Where-Object { $_.status -eq 'FAIL' }).Count
$warnCount = @($script:Results | Where-Object { $_.status -eq 'WARN' }).Count
$skipCount = @($script:Results | Where-Object { $_.status -eq 'SKIP' }).Count
Write-Status ('PASS: {0} | FAIL: {1} | WARN: {2} | SKIP: {3}' -f $passCount, $failCount, $warnCount, $skipCount) 'Cyan'
Write-Status ('Reports: {0}' -f $RunDir) 'Gray'
Write-Status ('JSON: {0}' -f $report.Json) 'Gray'
Write-Status ('Markdown: {0}' -f $report.Markdown) 'Gray'

if ($report.Failed -gt 0 -or ($Strict -and $report.Warnings -gt 0)) {
    Write-Status 'Validation completed with failures. Review the report and individual logs.' 'Red'
    exit 1
}
Write-Status 'Validation completed. Review WARN/SKIP items before treating the project as fully verified.' 'Green'
exit 0
