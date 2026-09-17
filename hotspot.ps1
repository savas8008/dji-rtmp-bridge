<#
    Windows Mobil Etkin Nokta'yi (Mobile Hotspot) WinRT
    NetworkOperatorTetheringManager API'si uzerinden kontrol eder.
    app.py tarafindan cagrilir; sonucu tek satir JSON olarak yazdirir.

    Kullanim:
      powershell -NoProfile -STA -ExecutionPolicy Bypass -File hotspot.ps1 -Action status
      powershell -NoProfile -STA -ExecutionPolicy Bypass -File hotspot.ps1 -Action start
      powershell -NoProfile -STA -ExecutionPolicy Bypass -File hotspot.ps1 -Action stop
      powershell -NoProfile -STA -ExecutionPolicy Bypass -File hotspot.ps1 -Action info
#>

param(
    [ValidateSet('status', 'start', 'stop', 'info')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms | Out-Null

[Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType = WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking.NetworkOperators, ContentType = WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringAccessPointConfiguration, Windows.Networking.NetworkOperators, ContentType = WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult, Windows.Networking.NetworkOperators, ContentType = WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.TetheringOperationalState, Windows.Networking.NetworkOperators, ContentType = WindowsRuntime] | Out-Null

function Await-WinRT($WinRtTask, $ResultType) {
    if ($null -eq $script:asTaskGeneric) {
        $script:asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
            Where-Object { $_.Name -eq 'AsTask' -and
                           $_.GetParameters().Count -eq 1 -and
                           $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
    }
    $asTask  = $script:asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while (-not $netTask.IsCompleted) {
        [System.Windows.Forms.Application]::DoEvents()
        [System.Threading.Thread]::Sleep(30)
        if ($sw.Elapsed.TotalSeconds -ge 30) {
            throw 'Mobil Etkin Nokta islemi 30 saniyede tamamlanmadi (zaman asimi).'
        }
    }
    if ($netTask.IsFaulted) { throw $netTask.Exception.InnerException }
    $netTask.Result
}

function Write-Result($obj) {
    $obj | ConvertTo-Json -Compress
}

try {
    $connProfile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
    if (-not $connProfile) {
        Write-Result @{
            ok    = $false
            error = 'Aktif bir ag baglantisi bulunamadi. Mobil Etkin Nokta, paylasacagi bir Wi-Fi/Ethernet baglantisi ister; internete (ya da en azindan bagli bir aga) sahip olmadan acilamaz.'
        }
        exit 1
    }

    $mgr = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($connProfile)

    switch ($Action) {
        'status' {
            Write-Result @{ ok = $true; state = $mgr.TetheringOperationalState.ToString() }
        }
        'start' {
            if ($mgr.TetheringOperationalState.ToString() -ne 'On') {
                $res = Await-WinRT ($mgr.StartTetheringAsync()) ([Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult])
                if ($res.Status.ToString() -notin @('Success')) {
                    Write-Result @{ ok = $false; error = "Baslatilamadi: $($res.Status)" }
                    exit 1
                }
            }
            $cfg = $mgr.GetCurrentAccessPointConfiguration()
            Write-Result @{
                ok         = $true
                state      = $mgr.TetheringOperationalState.ToString()
                ssid       = $cfg.Ssid
                passphrase = $cfg.Passphrase
            }
        }
        'stop' {
            if ($mgr.TetheringOperationalState.ToString() -eq 'On') {
                Await-WinRT ($mgr.StopTetheringAsync()) ([Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult]) | Out-Null
            }
            Write-Result @{ ok = $true; state = $mgr.TetheringOperationalState.ToString() }
        }
        'info' {
            $cfg = $mgr.GetCurrentAccessPointConfiguration()
            Write-Result @{
                ok         = $true
                state      = $mgr.TetheringOperationalState.ToString()
                ssid       = $cfg.Ssid
                passphrase = $cfg.Passphrase
            }
        }
    }
} catch {
    Write-Result @{ ok = $false; error = $_.Exception.Message }
    exit 1
}
