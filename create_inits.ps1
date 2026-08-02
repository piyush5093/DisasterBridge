$base = "D:\Infosys Springboard 7.0\backend"

$inits = @(
    "app\__init__.py",
    "app\core\__init__.py",
    "app\db\__init__.py",
    "app\models\__init__.py",
    "app\schemas\__init__.py",
    "app\services\__init__.py",
    "app\api\__init__.py",
    "app\api\routes\__init__.py"
)

foreach ($f in $inits) {
    $path = Join-Path $base $f
    New-Item -Path $path -ItemType File -Force | Out-Null
    Write-Host "Created: $f"
}

# data_ingestion __init__ files
$diBase = "D:\Infosys Springboard 7.0\data_ingestion"
New-Item -Path "$diBase\__init__.py" -ItemType File -Force | Out-Null
New-Item -Path "$diBase\connectors\__init__.py" -ItemType File -Force | Out-Null
New-Item -Path "$diBase\parsers\__init__.py" -ItemType File -Force | Out-Null

Write-Host "All __init__.py created!"

# .env file
$envContent = @"
APP_NAME=AI Disaster Response Command System
APP_VERSION=1.0.0
DEBUG=True
DATABASE_URL=sqlite:///./disaster_response.db
GDACS_API_URL=https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH
USGS_API_URL=https://earthquake.usgs.gov/fdsnws/event/1/query
CRITICAL_SCORE_MIN=8.0
HIGH_SCORE_MIN=6.0
MEDIUM_SCORE_MIN=4.0
"@

Set-Content -Path "D:\Infosys Springboard 7.0\backend\.env" -Value $envContent
Write-Host ".env created!"
