param(
    [ValidateSet('setup','start','restart','info','stop-postgres')][string]$Action = 'start',
    [string]$LanAddress = '',
    [switch]$MobileHotspot,
    [switch]$Https,
    [int]$Port=0,
    [string]$PythonPath = ''
)
$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $demoRoot
if (-not $PythonPath) {
    $demoGitCommon = (& git rev-parse --path-format=absolute --git-common-dir).Trim()
    $PythonPath = Join-Path (Split-Path -Parent $demoGitCommon) '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $PythonPath)) { throw 'Pass -PythonPath with the Python environment containing requirements-test.txt.' }
if ($LanAddress) {
    $demoAddress = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LanAddress -ErrorAction Stop
    if ($MobileHotspot) {
        $demoAdapter=Get-NetAdapter -InterfaceIndex $demoAddress.InterfaceIndex
        if ($demoAdapter.Status -ne 'Up' -or $demoAdapter.InterfaceDescription -notlike '*Wi-Fi Direct Virtual*' -or $demoAddress.PrefixLength -ne 24 -or $LanAddress -ne '192.168.137.1') { throw 'Expected the active, isolated Windows Mobile Hotspot at 192.168.137.1/24.' }
        $hotspotState = & "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command '$null=[Windows.Networking.Connectivity.NetworkInformation,Windows,ContentType=WindowsRuntime]; $null=[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows,ContentType=WindowsRuntime]; $p=[Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile(); $m=[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($p); $m.TetheringOperationalState.ToString()'
        if ($LASTEXITCODE -ne 0 -or ($hotspotState | Out-String).Trim() -ne 'On') { throw 'Windows Mobile Hotspot is not confirmed active.' }
    } else {
        $demoNetwork = Get-NetConnectionProfile -InterfaceIndex $demoAddress.InterfaceIndex -ErrorAction Stop
        if ($demoNetwork.NetworkCategory -ne 'Private') { throw 'LAN mode requires a trusted Windows Private network. No firewall or network settings were changed.' }
    }
}
$demoScript = Join-Path $demoRoot 'scripts\local_demo.py'
if ($Action -eq 'restart') {
    $demoPidFile = Join-Path $demoRoot '.tmp\flask-demo-process.json'
    if (Test-Path -LiteralPath $demoPidFile) {
        $demoRecord = Get-Content -LiteralPath $demoPidFile -Raw | ConvertFrom-Json
        if ([System.IO.Path]::GetFullPath($demoRecord.root) -ne [System.IO.Path]::GetFullPath($demoRoot)) { throw 'Process record belongs to another workspace.' }
        $demoProcess = Get-Process -Id $demoRecord.pid -ErrorAction SilentlyContinue
        if ($demoProcess) {
            $demoCommand = (Get-CimInstance Win32_Process -Filter "ProcessId=$($demoRecord.pid)").CommandLine
            if ($demoProcess.StartTime.ToUniversalTime().Ticks.ToString() -ne $demoRecord.process_start_ticks -or $demoCommand -notlike "*$demoScript*") { throw 'Process identity changed; no process was stopped.' }
            $demoListeners = @(Get-NetTCPConnection -State Listen -LocalPort $demoRecord.port -ErrorAction SilentlyContinue)
            if (-not $demoListeners -or @($demoListeners | Where-Object { $_.OwningProcess -ne $demoRecord.pid -or $_.LocalAddress -ne $demoRecord.address }).Count) { throw 'Listener identity changed; no process was stopped.' }
            Stop-Process -Id $demoRecord.pid -ErrorAction Stop
            Wait-Process -Id $demoRecord.pid -Timeout 10 -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $demoPidFile
    }
    $Action = 'start'
}
$demoArguments = @($demoScript, $Action)
if ($LanAddress) { $demoArguments += @('--lan-address', $LanAddress) }
if ($Https) { $demoArguments += '--https' }
if ($Port) { $demoArguments += @('--port', [string]$Port) }
& $PythonPath @demoArguments
exit $LASTEXITCODE
