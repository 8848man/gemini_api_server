# PowerShell script to start development environment
# Gemini API Server Development Startup Script

Write-Host "Starting Gemini API Server Development Environment..." -ForegroundColor Green

# Check if Docker is running
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Check if .env file exists
if (-Not (Test-Path ".env")) {
    Write-Host "Creating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Please edit .env file with your configuration before continuing." -ForegroundColor Yellow
    Write-Host "Especially set your GEMINI_API_KEY." -ForegroundColor Yellow
    
    $response = Read-Host "Continue anyway? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        exit 1
    }
}

# Create necessary directories
Write-Host "Creating directories..." -ForegroundColor Blue
$directories = @("logs", "data", "config\ssl")
foreach ($dir in $directories) {
    if (-Not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created directory: $dir" -ForegroundColor Gray
    }
}

# Generate self-signed SSL certificates for development
$certPath = "config\ssl\cert.pem"
$keyPath = "config\ssl\key.pem"

if (-Not (Test-Path $certPath) -or -Not (Test-Path $keyPath)) {
    Write-Host "Generating self-signed SSL certificates..." -ForegroundColor Blue
    
    # Check if OpenSSL is available
    $opensslAvailable = $false
    try {
        openssl version | Out-Null
        $opensslAvailable = $true
    } catch {
        Write-Host "OpenSSL not found. Trying alternative method..." -ForegroundColor Yellow
    }
    
    if ($opensslAvailable) {
        openssl req -x509 -newkey rsa:4096 -keyout $keyPath -out $certPath -days 365 -nodes -subj "/CN=localhost"
        Write-Host "SSL certificates generated successfully." -ForegroundColor Green
    } else {
        # Create dummy certificates for development
        Write-Host "Creating dummy certificates (HTTPS will not work properly)..." -ForegroundColor Yellow
        "DUMMY CERTIFICATE" | Out-File -FilePath $certPath -Encoding ASCII
        "DUMMY KEY" | Out-File -FilePath $keyPath -Encoding ASCII
    }
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Blue
docker-compose -f docker-compose.dev.yml down --remove-orphans 2>&1 | Out-Null

# Build and start development services
Write-Host "Building and starting development services..." -ForegroundColor Blue
docker-compose -f docker-compose.dev.yml up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "Development environment started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services available at:" -ForegroundColor Cyan
    Write-Host "  API Server: http://localhost:8000" -ForegroundColor White
    Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  Redis: localhost:6380" -ForegroundColor White
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Cyan
    Write-Host "  View logs: docker-compose -f docker-compose.dev.yml logs -f" -ForegroundColor White
    Write-Host "  Run tests: docker-compose -f docker-compose.dev.yml run test" -ForegroundColor White
    Write-Host "  Stop services: docker-compose -f docker-compose.dev.yml down" -ForegroundColor White
    Write-Host ""
    Write-Host "Press Ctrl+C to view logs or run 'docker-compose -f docker-compose.dev.yml logs -f' in another terminal"
    
    # Show logs
    docker-compose -f docker-compose.dev.yml logs -f
} else {
    Write-Host "Failed to start development environment. Check the logs above." -ForegroundColor Red
    exit 1
}