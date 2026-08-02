$base = "d:\Infosys Springboard 7.0"

$folders = @(
    "frontend",
    "frontend\public",
    "frontend\src",
    "frontend\src\components",
    "frontend\src\components\Map",
    "frontend\src\components\Dashboard",
    "frontend\src\components\Alerts",
    "frontend\src\components\ResourceCards",
    "frontend\src\components\FieldTeams",
    "frontend\src\pages",
    "frontend\src\services",
    "frontend\src\hooks",
    "frontend\src\utils",
    "frontend\src\assets",
    "backend",
    "backend\app",
    "backend\app\api",
    "backend\app\api\routes",
    "backend\app\models",
    "backend\app\schemas",
    "backend\app\services",
    "backend\app\core",
    "backend\app\db",
    "backend\tests",
    "ml_engine",
    "ml_engine\data",
    "ml_engine\data\raw",
    "ml_engine\data\processed",
    "ml_engine\notebooks",
    "ml_engine\models",
    "ml_engine\models\saved",
    "ml_engine\scripts",
    "ml_engine\evaluation",
    "database",
    "database\migrations",
    "database\seeds",
    "database\schemas",
    "optimizer",
    "optimizer\algorithms",
    "optimizer\tests",
    "data_ingestion",
    "data_ingestion\feeds",
    "data_ingestion\parsers",
    "data_ingestion\connectors",
    "docs",
    "docs\architecture",
    "docs\api_reference",
    "docs\flowcharts",
    "docs\deployment",
    "tests",
    "tests\integration",
    "tests\e2e",
    "scripts",
    "config"
)

foreach ($f in $folders) {
    $path = Join-Path $base $f
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    Write-Host "Created: $f"
}

# README files
$readmes = @{
    "frontend"       = "# Frontend - React.js + Leaflet.js Dashboard`n`nReact + Leaflet.js based command dashboard."
    "backend"        = "# Backend - FastAPI Python Server`n`nFastAPI REST API for disaster data and demand prediction."
    "ml_engine"      = "# ML Engine - Resource Demand Prediction`n`nRegression model predicting resource demand per disaster zone."
    "database"       = "# Database - PostgreSQL + PostGIS`n`nGeospatial database for zones, depots, and field records."
    "optimizer"      = "# Optimizer - OR-Tools Resource Allocation`n`nLinear programming model for optimal resource allocation."
    "data_ingestion" = "# Data Ingestion - GDACS, USGS, NDMA, Satellite Feeds`n`nReal-time disaster data connectors and parsers."
    "docs"           = "# Documentation`n`nArchitecture, API reference, deployment guides."
}

foreach ($key in $readmes.Keys) {
    $path = Join-Path $base "$key\README.md"
    Set-Content -Path $path -Value $readmes[$key]
    Write-Host "Created README: $key\README.md"
}

# Root-level files
Set-Content -Path "$base\README.md" -Value "# AI-Based Disaster Response Management System`n`nInfosys Springboard 7.0 Project"
Set-Content -Path "$base\.gitignore" -Value "node_modules/`n__pycache__/`n*.pyc`n.env`n*.db`ndist/`nbuild/`n.venv/`n*.egg-info/"
Set-Content -Path "$base\docker-compose.yml" -Value "# Docker Compose - to be configured`nversion: '3.8'`nservices:`n  db:`n    image: postgis/postgis`n  backend:`n    build: ./backend`n  frontend:`n    build: ./frontend"
Set-Content -Path "$base\.env.example" -Value "# Environment Variables`nGDACS_API_KEY=`nUSGS_API_KEY=`nNDMA_API_KEY=`nDB_URL=postgresql://user:pass@localhost/disasterdb`nSECRET_KEY=`nDEBUG=True"

Write-Host ""
Write-Host "All folders and files created successfully!" -ForegroundColor Green
