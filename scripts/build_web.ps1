$ErrorActionPreference = "Stop"

function Log {
    param($Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

function ErrorLog {
    param($Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ERROR: $Message" -ForegroundColor Red
}

$WorkspaceRoot = $PSScriptRoot
Set-Location $WorkspaceRoot

Log "Building SwitchCraft Web App Docker Image..."

# Check requirements
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    ErrorLog "Docker is not installed or not in PATH."
    exit 1
}

# Build
try {
    docker build -t switchcraft-web .
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed."
    }
} catch {
    ErrorLog "Build failed: $_"
    exit 1
}

Log "Docker Image 'switchcraft-web' built successfully."
Log "Run it locally with: docker run -p 8080:8080 switchcraft-web"
