param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "== Production Preflight ==" -ForegroundColor Cyan

$requiredEnv = @(
    "SECRET_KEY",
    "BACKUP_SIGNING_KEY",
    "DEFAULT_STUDENT_PASSWORD",
    "DEFAULT_TEACHER_PASSWORD",
    "DATABASE_URL"
)

$missing = @()
foreach ($name in $requiredEnv) {
    $val = [Environment]::GetEnvironmentVariable($name, "Process")
    if ([string]::IsNullOrWhiteSpace($val)) {
        $val = [Environment]::GetEnvironmentVariable($name, "Machine")
    }
    if ([string]::IsNullOrWhiteSpace($val)) {
        $val = [Environment]::GetEnvironmentVariable($name, "User")
    }
    if ([string]::IsNullOrWhiteSpace($val)) {
        $missing += $name
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing required environment variables:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    throw "Preflight failed: missing environment variables."
}

$allowInsecure = [Environment]::GetEnvironmentVariable("ALLOW_INSECURE_DEFAULTS", "Process")
if ([string]::IsNullOrWhiteSpace($allowInsecure)) {
    $allowInsecure = [Environment]::GetEnvironmentVariable("ALLOW_INSECURE_DEFAULTS", "Machine")
}
if ([string]::IsNullOrWhiteSpace($allowInsecure)) {
    $allowInsecure = [Environment]::GetEnvironmentVariable("ALLOW_INSECURE_DEFAULTS", "User")
}
if (-not [string]::IsNullOrWhiteSpace($allowInsecure) -and $allowInsecure.Trim().ToLower() -in @("1","true","yes")) {
    throw "ALLOW_INSECURE_DEFAULTS must be disabled in production."
}

Write-Host "Running syntax check..." -ForegroundColor Yellow
& $PythonExe -m py_compile student_scor.py

Write-Host "Running migrations..." -ForegroundColor Yellow
& $PythonExe migrate.py

Write-Host "Running DB health check with fixes..." -ForegroundColor Yellow
& $PythonExe student_scor.py --db-health-check --apply-fixes --include-startup-ddl

Write-Host "Preflight completed successfully." -ForegroundColor Green

