<#
    MediaMTX'i baslatir. Once Windows Mobile Hotspot'un acik oldugundan emin
    olun (Ayarlar > Ag ve Internet > Mobil hotspot). Bu betik hotspot IP'sini
    bulup DJI Fly / VLC / QGroundControl'e girilecek URL'leri ekrana basar ve
    gerekli portlar icin (varsa yonetici izniyle) guvenlik duvari kurali ekler.
#>

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'bin\mediamtx.exe'
$config = Join-Path $root 'mediamtx.yml'

if (-not (Test-Path $exe)) {
    throw "bin\mediamtx.exe bulunamadi. Once .\setup.ps1 calistirin."
}

# Windows Mobile Hotspot'un sanal adaptörü genelde 192.168.137.x IP'sini kullanir.
$hotspotIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -like '192.168.137.*' } |
    Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $hotspotIp) {
    Write-Warning "192.168.137.x adresli bir hotspot arayuzu bulunamadi. Mobil Hotspot'u actiginizdan emin olun."
    Write-Warning "Asagida makinedeki tum IPv4 adresleri listeleniyor, dogru olani siz secin:"
    Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' } |
        Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize
    $hotspotIp = '<HOTSPOT-IP>'
}

# 1935 (RTMP), 8554 (RTSP), 8888 (HLS) icin gelen baglantilara izin ver.
foreach ($port in 1935, 8554, 8888) {
    $ruleName = "dji-rtmp-bridge-$port"
    try {
        if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow | Out-Null
            Write-Host "Guvenlik duvari kurali eklendi: $ruleName (TCP $port)"
        }
    } catch {
        Write-Warning "Guvenlik duvari kurali eklenemedi (yonetici olarak calistirmayi deneyin): $port"
    }
}

Write-Host ''
Write-Host '--- DJI Fly icin RTMP adresi (Transmission > Live Streaming Platforms > RTMP) ---' -ForegroundColor Cyan
Write-Host "  rtmp://$hotspotIp`:1935/dji"
Write-Host ''
Write-Host '--- VLC / QGroundControl icin RTSP adresi ---' -ForegroundColor Cyan
Write-Host "  rtsp://$hotspotIp`:8554/dji"
Write-Host ''
Write-Host 'MediaMTX baslatiliyor... (durdurmak icin Ctrl+C)' -ForegroundColor Green
Write-Host ''

& $exe $config
