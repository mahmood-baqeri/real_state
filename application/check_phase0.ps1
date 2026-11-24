[CmdletBinding()]
param(
    [switch]$SkipBaseSuite,
    [switch]$IncludeBaseSuite,
    [switch]$SkipDatabaseChecks,
    [switch]$SkipLegacyMediaDryRun,
    [switch]$NoColor,
    [string]$LogDirectory = 'validation-reports\phase0'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DjangoDir = Join-Path $Root 'backend\django_core'
$FastApiDir = Join-Path $Root 'backend\fastapi_core'
$ReportsRoot = Join-Path $Root $LogDirectory
$RunDir = Join-Path $ReportsRoot (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
$script:Results = New-Object System.Collections.Generic.List[object]
$Python = $null
$Npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $Npm) { $Npm = Get-Command npm -ErrorAction SilentlyContinue }
$PowerShellExe = Join-Path $PSHOME $(if ($PSVersionTable.PSEdition -eq 'Core') { 'pwsh.exe' } else { 'powershell.exe' })

$pythonCandidates = @(
    (Join-Path $Root '.venv\Scripts\python.exe'),
    (Join-Path $Root 'venv\Scripts\python.exe'),
    (Join-Path $DjangoDir '.venv\Scripts\python.exe')
)
foreach ($candidate in $pythonCandidates) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $Python = $candidate; break }
}
if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source }
}

function Add-Check {
    param([string]$Name, [string]$Status, [int]$ExitCode = 0, [string]$Details = '')
    $script:Results.Add([pscustomobject]@{ name = $Name; status = $Status; exit_code = $ExitCode; details = $Details })
    $color = if ($Status -eq 'PASS') { 'Green' } elseif ($Status -eq 'FAIL') { 'Red' } else { 'Yellow' }
    if ($NoColor) { Write-Host "[$Status] $Name $Details" } else { Write-Host "[$Status] $Name $Details" -ForegroundColor $color }
}

function Invoke-Logged {
    param([string]$Name, [string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory, [switch]$Optional)
    $safe = $Name -replace '[^A-Za-z0-9_-]', '_'
    $out = Join-Path $RunDir ($safe + '.stdout.log')
    $err = Join-Path $RunDir ($safe + '.stderr.log')
    if (-not (Test-Path -LiteralPath $WorkingDirectory -PathType Container)) {
        Add-Check $Name $(if ($Optional) { 'SKIP' } else { 'FAIL' }) 1 "Missing directory: $WorkingDirectory"; return
    }
    if (-not $FilePath -or (-not (Test-Path -LiteralPath $FilePath -PathType Leaf) -and -not (Get-Command $FilePath -ErrorAction SilentlyContinue))) {
        Add-Check $Name $(if ($Optional) { 'SKIP' } else { 'FAIL' }) 1 "Executable not found: $FilePath"; return
    }
    try {
        $argLine = ($Arguments | ForEach-Object { '"' + ([string]$_ -replace '"', '\"') + '"' }) -join ' '
        $proc = Start-Process -FilePath $FilePath -ArgumentList $argLine -WorkingDirectory $WorkingDirectory -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -Wait
        if ($proc.ExitCode -eq 0) { Add-Check $Name 'PASS' 0 "Logs: $safe" }
        else { Add-Check $Name 'FAIL' $proc.ExitCode "See $safe stdout/stderr logs" }
    } catch { Add-Check $Name 'FAIL' 1 $_.Exception.Message }
}

Write-Host '============================================================'
Write-Host ' PHASE 0 | SECURITY, TENANT ISOLATION, FINANCE & REGRESSION'
Write-Host " Root: $Root"
Write-Host ' .env contents are not read, printed, or changed by this script.'
Write-Host '============================================================'

if (-not $Python) { Add-Check 'Python interpreter' 'FAIL' 1 'Python not found.' }
else {
    Add-Check 'Python interpreter' 'PASS' 0 $Python
    Invoke-Logged 'Phase 0 static release gates' $Python @('scripts/check_phase0_static.py') $Root
    Invoke-Logged 'Django Phase 0 focused tests' $Python @('-m','pytest','tests/test_phase0_hardening.py','tests/test_phase0_security_hardening.py','tests/test_phase0_additional_controls.py','-q') $DjangoDir
    Invoke-Logged 'Django migration drift' $Python @('manage.py','makemigrations','--check','--dry-run') $DjangoDir
    Invoke-Logged 'Django system checks' $Python @('manage.py','check') $DjangoDir
    if (-not $SkipDatabaseChecks) {
        # Report the pending schema plan before running checks that depend on it.
        Invoke-Logged 'Django migration plan' $Python @('manage.py','migrate','--plan') $DjangoDir
        Invoke-Logged 'PostgreSQL tenant RLS verification' $Python @('manage.py','verify_tenant_rls') $DjangoDir
        Invoke-Logged 'Private storage verification' $Python @('manage.py','verify_storage_security') $DjangoDir
    } else {
        Add-Check 'PostgreSQL tenant RLS verification' 'SKIP' 0 'Disabled by -SkipDatabaseChecks.'
        Add-Check 'Private storage verification' 'SKIP' 0 'Disabled by -SkipDatabaseChecks.'
        Add-Check 'Django migration plan' 'SKIP' 0 'Disabled by -SkipDatabaseChecks.'
    }
    if (-not $SkipLegacyMediaDryRun -and -not $SkipDatabaseChecks) {
        # These commands read newly-added model columns. Do not run them against a
        # database whose migration plan still contains unapplied migrations.
        Push-Location $DjangoDir
        try {
            $planOutput = & $Python 'manage.py' 'showmigrations' '--plan' 2>&1
            $planExit = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        $pendingMigrations = ($planOutput | Out-String) -match '(?m)^\s*\[ \]'
        if ($planExit -ne 0) {
            Add-Check 'Legacy documents private migration dry-run' 'SKIP' 0 'Could not verify migration state; apply/inspect migrations before running the data dry-run.'
            Add-Check 'Legacy property media private migration dry-run' 'SKIP' 0 'Could not verify migration state; apply/inspect migrations before running the data dry-run.'
        } elseif ($pendingMigrations) {
            Add-Check 'Legacy documents private migration dry-run' 'SKIP' 0 'Database has unapplied migrations; run only after backup and approved schema migration.'
            Add-Check 'Legacy property media private migration dry-run' 'SKIP' 0 'Database has unapplied migrations; run only after backup and approved schema migration.'
        } else {
            Invoke-Logged 'Legacy documents private migration dry-run' $Python @('manage.py','migrate_private_documents','--dry-run') $DjangoDir
            Invoke-Logged 'Legacy property media private migration dry-run' $Python @('manage.py','migrate_private_property_media','--dry-run') $DjangoDir
        }
    } else {
        Add-Check 'Legacy media migration dry-runs' 'SKIP' 0 'Disabled by selected switches.'
    }
}

if ($IncludeBaseSuite -and -not $SkipBaseSuite) {
    $childArgs = @('-NoProfile','-File',(Join-Path $Root 'check_project.ps1'),'-Mode','Full','-Strict','-LogDirectory',(Join-Path $LogDirectory 'base-suite'))
    if ($NoColor) { $childArgs += '-NoColor' }
    if ($SkipDatabaseChecks) { $childArgs += '-SkipDatabaseChecks' }
    try {
        $proc = Start-Process -FilePath $PowerShellExe -ArgumentList $childArgs -WorkingDirectory $Root -PassThru -Wait -NoNewWindow
        Add-Check 'Full project regression suite (check_project.ps1)' $(if ($proc.ExitCode -eq 0) { 'PASS' } else { 'FAIL' }) $proc.ExitCode 'See validation-reports/base-suite.'
    } catch { Add-Check 'Full project regression suite (check_project.ps1)' 'FAIL' 1 $_.Exception.Message }
} else { Add-Check 'Full project regression suite (check_project.ps1)' 'SKIP' 0 'Not run by default. Use -IncludeBaseSuite to opt in.' }

$failed = @($script:Results | Where-Object { $_.status -eq 'FAIL' })
$summary = [pscustomobject]@{
    phase = '0'
    started_at = (Get-Date).ToString('o')
    result = $(if ($failed.Count) { 'FAILED' } else { 'COMPLETED' })
    counts = [pscustomobject]@{
        passed = @($script:Results | Where-Object status -eq 'PASS').Count
        failed = $failed.Count
        skipped = @($script:Results | Where-Object status -eq 'SKIP').Count
    }
    checks = @($script:Results.ToArray())
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $RunDir 'phase0-summary.json') -Encoding UTF8
$script:Results | Format-Table -AutoSize | Out-String | Set-Content -LiteralPath (Join-Path $RunDir 'phase0-summary.txt') -Encoding UTF8
Write-Host "Phase 0 report: $RunDir"
if ($failed.Count) { exit 1 }
exit 0
