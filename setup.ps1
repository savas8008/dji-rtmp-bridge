<#
    MediaMTX'in en guncel Windows (amd64) surumunu GitHub release'lerinden
    indirir ve bin\mediamtx.exe olarak cikartir.
#>

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$binDir = Join-Path $root 'bin'
New-Item -ItemType Directory -Force -Path $binDir | Out-Null

Write-Host "GitHub'dan en guncel MediaMTX surumu sorgulaniyor..."
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/bluenviron/mediamtx/releases/latest' -Headers @{ 'User-Agent' = 'dji-rtmp-bridge-setup' }

$asset = $release.assets | Where-Object { $_.name -match 'windows_amd64\.zip$' } | Select-Object -First 1
if (-not $asset) {
    throw "windows_amd64.zip iceren bir surum bulunamadi. https://github.com/bluenviron/mediamtx/releases sayfasindan elle indirip bin\ klasorune cikartabilirsiniz."
}

$zipPath = Join-Path $binDir $asset.name
Write-Host "Indiriliyor: $($asset.browser_download_url)"
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath

Write-Host "Aciliyor..."
Expand-Archive -Path $zipPath -DestinationPath $binDir -Force
Remove-Item $zipPath

if (-not (Test-Path (Join-Path $binDir 'mediamtx.exe'))) {
    throw "mediamtx.exe bin\ klasorunde bulunamadi, arsiv icerigini kontrol edin."
}

Write-Host "Tamam: $binDir\mediamtx.exe hazir. Simdi start.ps1 calistirabilirsiniz." -ForegroundColor Green
