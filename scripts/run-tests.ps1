# PowerShell script to run tests
# Gemini API Server Test Runner

Write-Host "Running Gemini API Server Tests..." -ForegroundColor Green

# Check if Docker is running
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Parse command line arguments
param(
    [switch]$Unit,
    [switch]$Integration, 
    [switch]$Coverage,
    [switch]$Verbose,
    [string]$Pattern = "",
    [switch]$Watch
)

$testArgs = @()

# Test type selection
if ($Unit) {
    $testArgs += "tests/unit/"
} elseif ($Integration) {
    $testArgs += "tests/integration/"
} else {
    $testArgs += "tests/"
}

# Add pattern if specified
if ($Pattern) {
    $testArgs += "-k", $Pattern
}

# Verbose output
if ($Verbose) {
    $testArgs += "-v"
}

# Coverage options
if ($Coverage) {
    $testArgs += "--cov=src", "--cov-report=html", "--cov-report=term-missing"
    Write-Host "Coverage report will be generated in htmlcov/" -ForegroundColor Blue
}

# Watch mode
if ($Watch) {
    Write-Host "Starting test watch mode (pytest-watch required)..." -ForegroundColor Blue
    $testArgs = @("ptw", "--") + $testArgs
} else {
    $testArgs = @("python", "-m", "pytest") + $testArgs
}

Write-Host "Test command: $($testArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

# Ensure Redis is running for tests
Write-Host "Starting Redis for tests..." -ForegroundColor Blue
docker-compose -f docker-compose.dev.yml up -d redis-dev

# Run tests in Docker container
try {
    docker-compose -f docker-compose.dev.yml run --rm test $testArgs
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "Error running tests: $_" -ForegroundColor Red
    $exitCode = 1
}

# Show coverage report location if generated
if ($Coverage -and $exitCode -eq 0) {
    Write-Host ""
    Write-Host "Coverage report available at:" -ForegroundColor Green
    Write-Host "  HTML: htmlcov/index.html" -ForegroundColor White
    
    # Try to open coverage report
    if (Test-Path "htmlcov\index.html") {
        $openReport = Read-Host "Open coverage report in browser? (y/N)"
        if ($openReport -eq "y" -or $openReport -eq "Y") {
            Start-Process "htmlcov\index.html"
        }
    }
}

# Test summary
if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "All tests passed! ✅" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Some tests failed! ❌" -ForegroundColor Red
}

# Cleanup
Write-Host "Cleaning up test containers..." -ForegroundColor Gray
docker-compose -f docker-compose.dev.yml down --remove-orphans 2>&1 | Out-Null

exit $exitCode