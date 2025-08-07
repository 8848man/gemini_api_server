# PowerShell script for production deployment
# Gemini API Server Production Deployment Script

param(
    [string]$Environment = "production",
    [switch]$Monitoring,
    [switch]$UpdateOnly,
    [switch]$Rollback
)

Write-Host "Gemini API Server Deployment Script" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Cyan

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Blue

# Docker check
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running." -ForegroundColor Red
    exit 1
}

# Docker Compose check
docker-compose --version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker Compose is not installed." -ForegroundColor Red
    exit 1
}

# Environment file check
if (-Not (Test-Path ".env")) {
    Write-Host "Error: .env file not found. Please create it from .env.example" -ForegroundColor Red
    exit 1
}

# Load environment variables
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)\s*$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

# Validate required environment variables
$requiredVars = @("SECRET_KEY", "API_KEY", "JWT_SECRET_KEY", "GEMINI_API_KEY")
$missingVars = @()

foreach ($var in $requiredVars) {
    if (-not [Environment]::GetEnvironmentVariable($var)) {
        $missingVars += $var
    }
}

if ($missingVars.Count -gt 0) {
    Write-Host "Error: Missing required environment variables:" -ForegroundColor Red
    $missingVars | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    exit 1
}

# Security check for default values
$defaultValues = @{
    "SECRET_KEY" = "your-secret-key-change-in-production"
    "API_KEY" = "your-api-key-for-authentication" 
    "JWT_SECRET_KEY" = "your-jwt-secret-key-here"
}

foreach ($var in $defaultValues.Keys) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if ($value -eq $defaultValues[$var]) {
        Write-Host "Warning: $var is using default value. Please change it for security." -ForegroundColor Yellow
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            exit 1
        }
    }
}

# Rollback functionality
if ($Rollback) {
    Write-Host "Rolling back to previous deployment..." -ForegroundColor Yellow
    
    if (Test-Path "docker-compose.backup.yml") {
        Copy-Item "docker-compose.backup.yml" "docker-compose.yml" -Force
        Write-Host "Configuration restored from backup." -ForegroundColor Green
    }
    
    docker-compose down
    docker-compose up -d --force-recreate
    
    Write-Host "Rollback completed." -ForegroundColor Green
    exit 0
}

# Backup current configuration
if (Test-Path "docker-compose.yml") {
    Copy-Item "docker-compose.yml" "docker-compose.backup.yml" -Force
    Write-Host "Current configuration backed up." -ForegroundColor Gray
}

# Create necessary directories
Write-Host "Creating directories..." -ForegroundColor Blue
$directories = @("logs", "data", "config\ssl", "logs\nginx")
foreach ($dir in $directories) {
    if (-Not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# SSL Certificate handling
Write-Host "Checking SSL certificates..." -ForegroundColor Blue
$certPath = "config\ssl\cert.pem"
$keyPath = "config\ssl\key.pem"

if (-Not (Test-Path $certPath) -or -Not (Test-Path $keyPath)) {
    Write-Host "SSL certificates not found. Generating self-signed certificates..." -ForegroundColor Yellow
    Write-Host "For production, please replace with real certificates." -ForegroundColor Yellow
    
    try {
        openssl req -x509 -newkey rsa:4096 -keyout $keyPath -out $certPath -days 365 -nodes -subj "/CN=localhost"
        Write-Host "Self-signed certificates generated." -ForegroundColor Green
    } catch {
        Write-Host "Error: Could not generate SSL certificates. OpenSSL may not be installed." -ForegroundColor Red
        exit 1
    }
}

# Run tests before deployment
if (-not $UpdateOnly) {
    Write-Host "Running tests before deployment..." -ForegroundColor Blue
    
    docker-compose -f docker-compose.dev.yml up -d redis-dev
    $testResult = docker-compose -f docker-compose.dev.yml run --rm test python -m pytest tests/ --cov=src
    docker-compose -f docker-compose.dev.yml down
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Tests failed. Deployment aborted." -ForegroundColor Red
        exit 1
    }
    Write-Host "All tests passed!" -ForegroundColor Green
}

# Build production images
Write-Host "Building production images..." -ForegroundColor Blue
docker-compose build --no-cache

if ($LASTEXITCODE -ne 0) {
    Write-Host "Image build failed." -ForegroundColor Red
    exit 1
}

# Stop existing services
Write-Host "Stopping existing services..." -ForegroundColor Blue
docker-compose down --remove-orphans

# Start services
$composeFiles = @("docker-compose.yml")
if ($Monitoring) {
    Write-Host "Including monitoring services..." -ForegroundColor Blue
    $composeCommand = "docker-compose --profile monitoring up -d"
} else {
    $composeCommand = "docker-compose up -d"
}

Write-Host "Starting production services..." -ForegroundColor Blue
Invoke-Expression $composeCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services:" -ForegroundColor Cyan
    Write-Host "  API Server: https://localhost" -ForegroundColor White
    Write-Host "  Health Check: https://localhost/api/v1/health" -ForegroundColor White
    
    if ($Monitoring) {
        Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor White
        Write-Host "  Grafana: http://localhost:3000" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "Deployment logs:" -ForegroundColor Cyan
    Write-Host "  Application: logs/app.log" -ForegroundColor White
    Write-Host "  Nginx: logs/nginx/" -ForegroundColor White
    
    # Health check
    Write-Host ""
    Write-Host "Performing health check..." -ForegroundColor Blue
    Start-Sleep -Seconds 10
    
    try {
        $healthResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 30
        if ($healthResponse.status -eq "healthy") {
            Write-Host "Health check passed!" -ForegroundColor Green
        } else {
            Write-Host "Health check failed: $($healthResponse.status)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Health check failed: $_" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Cyan
    Write-Host "  View logs: docker-compose logs -f" -ForegroundColor White
    Write-Host "  Scale API: docker-compose up -d --scale api=3" -ForegroundColor White
    Write-Host "  Update: .\scripts\deploy.ps1 -UpdateOnly" -ForegroundColor White
    Write-Host "  Rollback: .\scripts\deploy.ps1 -Rollback" -ForegroundColor White
    
} else {
    Write-Host "Deployment failed. Check logs for details." -ForegroundColor Red
    docker-compose logs
    exit 1
}