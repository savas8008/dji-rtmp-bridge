<#
    app.py'yi tek dosyalik, konsolsuz bir .exe olarak paketler
    (PyInstaller). Cift tiklayarak calistirilabilir, Python kurulu
    olmasi gerekmez.

    Kullanim:  .\build_exe.ps1
    Cikti:     dist\DJI-RTMP-Koprusu.exe
               Bu exe'yi hotspot.ps1, mediamtx.yml ve bin\ klasoruyle
               AYNI klasorde tutun (dist\ altina kopyalanir).
#>

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'PyInstaller kuruluyor...'
    python -m pip install --quiet pyinstaller
}

python -m PyInstaller --onefile --noconsole --name "DJI-RTMP-Koprusu" app.py

foreach ($item in 'hotspot.ps1', 'mediamtx.yml') {
    Copy-Item $item -Destination 'dist' -Force
}
New-Item -ItemType Directory -Force -Path 'dist\bin' | Out-Null
if (Test-Path 'bin\mediamtx.exe') {
    Copy-Item 'bin\mediamtx.exe' -Destination 'dist\bin' -Force
} else {
    Write-Warning "bin\mediamtx.exe yok — dist icindeki uygulama ilk acilista 'Kur' butonuyla indirecek."
}

Write-Host ''
Write-Host "Tamam: dist\DJI-RTMP-Koprusu.exe hazir." -ForegroundColor Green
Write-Host "dist\ klasorunun tamamini kullaniciya verin (exe tek basina yeterli degil)." -ForegroundColor Yellow
