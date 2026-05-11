param(
    [switch]$WhatIf
)

$items = @(
    "app.log",
    "logs\\*.log",
    "backups",
    "ssss",
    "ne",
    "__pycache__",
    ".pytest_cache"
)

foreach ($item in $items) {
    if (Test-Path $item) {
        if ($WhatIf) {
            Write-Host "Would remove $item"
        } else {
            Remove-Item -Force -Recurse $item -ErrorAction SilentlyContinue
            Write-Host "Removed $item"
        }
    }
}
