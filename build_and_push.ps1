$ErrorActionPreference = "Stop"

Write-Host "1. Building Docker Image..." -ForegroundColor Cyan
docker build -t ghcr.io/alphios72/bernabei:latest -f Dockerfile .
if ($LASTEXITCODE -eq 0) {
    Write-Host "Build Successful." -ForegroundColor Green
}
else {
    Write-Host "Build Failed!" -ForegroundColor Red
    exit 1
}

Write-Host "2. Pushing to GHCR..." -ForegroundColor Cyan
docker push ghcr.io/alphios72/bernabei:latest
if ($LASTEXITCODE -eq 0) {
    Write-Host "Push Successful!" -ForegroundColor Green
}
else {
    Write-Host "Push Failed! Ensure you are logged in with: docker login ghcr.io" -ForegroundColor Red
    exit 1
}
