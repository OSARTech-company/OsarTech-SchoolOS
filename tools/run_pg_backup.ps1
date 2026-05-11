param(
    [string]$BackupDir = ".\\backups\\postgres",
    [int]$RetentionDays = 30,
    [string]$PgDumpPath = ""
)

$ErrorActionPreference = "Stop"

function Get-EnvValue([string]$Name) {
    $v = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v }
    $v = [Environment]::GetEnvironmentVariable($Name, "User")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v }
    $v = [Environment]::GetEnvironmentVariable($Name, "Machine")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v }
    return ""
}

$databaseUrl = (Get-EnvValue "DATABASE_URL")
if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
    $envPath = Join-Path (Get-Location) ".env"
    if (Test-Path $envPath) {
        $line = Get-Content $envPath | Where-Object { $_ -match "^\s*DATABASE_URL\s*=" } | Select-Object -First 1
        if ($line) {
            $databaseUrl = (($line -split "=", 2)[1]).Trim().Trim('"').Trim("'")
        }
    }
}

if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
    throw "DATABASE_URL is required (Process/User/Machine env or .env)."
}

if ([string]::IsNullOrWhiteSpace($PgDumpPath)) {
    $cmd = Get-Command pg_dump -ErrorAction SilentlyContinue
    if ($cmd) {
        $PgDumpPath = $cmd.Source
    }
}

if ([string]::IsNullOrWhiteSpace($PgDumpPath)) {
    $candidateRoots = @(
        "C:\Program Files\PostgreSQL",
        "C:\Program Files (x86)\PostgreSQL"
    )
    foreach ($root in $candidateRoots) {
        if (-not (Test-Path $root)) { continue }
        $found = Get-ChildItem -Path $root -Filter pg_dump.exe -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($found) {
            $PgDumpPath = $found.FullName
            break
        }
    }
}

if ([string]::IsNullOrWhiteSpace($PgDumpPath) -or -not (Test-Path $PgDumpPath)) {
    throw "pg_dump not found. Install PostgreSQL client tools or pass -PgDumpPath 'C:\Path\to\pg_dump.exe'."
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outfile = Join-Path $BackupDir ("school_result_" + $timestamp + ".dump")

Write-Host "Creating backup: $outfile"
& "$PgDumpPath" --format=custom --no-owner --no-privileges --file "$outfile" "$databaseUrl"

if ($LASTEXITCODE -ne 0) {
    throw "pg_dump failed with exit code $LASTEXITCODE"
}

Write-Host "Backup created successfully."

# Retention cleanup
$cutoff = (Get-Date).AddDays(-1 * [Math]::Max(1, $RetentionDays))
Get-ChildItem -Path $BackupDir -File -Filter "*.dump" |
    Where-Object { $_.LastWriteTime -lt $cutoff } |
    Remove-Item -Force

Write-Host "Retention cleanup complete (older than $RetentionDays days removed)."
