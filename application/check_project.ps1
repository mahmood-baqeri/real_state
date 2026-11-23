$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DjangoDir = Join-Path $Root 'backend\django_core'
$FastApiDir = Join-Path $Root 'backend\fastapi_core'
$FrontendDir = Join-Path $Root 'frontend'

function Run-Check([string]$Title, [scriptblock]$Command) {
    Write-Host "`n===== $Title =====" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Title (exit $LASTEXITCODE)" -ForegroundColor Red
        $script:Failures += $Title
    } else {
        Write-Host "PASSED: $Title" -ForegroundColor Green
    }
}

$Failures = @()
Push-Location $DjangoDir
Run-Check 'Django system checks' { python manage.py check }
Run-Check 'Model/migration drift check' { python manage.py makemigrations --check --dry-run }
Run-Check 'Read-only database schema check' { python manage.py diagnose_schema }
Run-Check 'Django migration plan' { python manage.py migrate --plan }
Run-Check 'Django tests' { python manage.py test }
Pop-Location

if (Test-Path (Join-Path $FrontendDir 'node_modules')) {
    Push-Location $FrontendDir
    Run-Check 'Frontend TypeScript check' { npm run lint }
    Pop-Location
} else {
    Write-Host "`nSKIPPED: Frontend TypeScript check (frontend/node_modules is absent; run npm ci first)." -ForegroundColor Yellow
}

Write-Host "`n===== SUMMARY =====" -ForegroundColor Cyan
if ($Failures.Count -eq 0) {
    Write-Host 'All executed checks passed. Review skipped checks above.' -ForegroundColor Green
    exit 0
}
Write-Host ("Failed checks: " + ($Failures -join ', ')) -ForegroundColor Red
exit 1
