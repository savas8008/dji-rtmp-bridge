<#
    app.py'yi tek dosyalik, konsolsuz bir .exe olarak paketler
    (PyInstaller). Cift tiklayarak calistirilabilir, Python kurulu
    olmasi gerekmez.

    Kullanim:  .\build_exe.ps1
    Cikti:     dist\DJI-RTMP-Koprusu.exe
               Bu exe'yi hotspot.ps1, mediamtx.yml ve bin\ klasoruyle
               AYNI klasorde tutun (dist\ altina kopyalanir).
#>

# Native araclarin (python, pyinstaller) stderr'e yazdigi satirlar
# PowerShell 5.1'de 'Stop' altinda sonlandirici hataya donusebiliyor;
# bu yuzden native cagrilardan sonra hatayi $LASTEXITCODE ile kendimiz
# kontrol ediyoruz, cmdlet hatalari (Copy-Item vb.) icin ise 'Stop' kaliyor.
$ErrorActionPreference = 'Continue'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m pip show pyinstaller *> $null
$pyinstallerInstalled = ($LASTEXITCODE -eq 0)

if (-not $pyinstallerInstalled) {
    Write-Host 'PyInstaller kuruluyor...'
    python -m pip install --quiet pyinstaller
    if ($LASTEXITCODE -ne 0) { throw 'pyinstaller kurulamadi.' }
}

python -m PyInstaller --onefile --noconsole --name "DJI-RTMP-Koprusu" app.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller derlemesi basarisiz oldu.' }

$ErrorActionPreference = 'Stop'

foreach ($item in 'hotspot.ps1', 'mediamtx.yml') {
    Copy-Item $item -Destination 'dist' -Force
}
New-Item -ItemType Directory -Force -Path 'dist\bin' | Out-Null
if (Test-Path 'bin\mediamtx.exe') {
    Copy-Item 'bin\mediamtx.exe' -Destination 'dist\bin' -Force
} else {
    Write-Warning "bin\mediamtx.exe yok - dist icindeki uygulama ilk acilista 'Kur' butonuyla indirecek."
}

Write-Host ''
Write-Host "Tamam: dist\DJI-RTMP-Koprusu.exe hazir." -ForegroundColor Green
Write-Host "dist\ klasorunun tamamini kullaniciya verin (exe tek basina yeterli degil)." -ForegroundColor Yellow
