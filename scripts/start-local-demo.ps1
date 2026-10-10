param(
    [ValidateSet('setup','start','info','stop-postgres')][string]$Action = 'start',
    [string]$LanAddress = '',
    [switch]$MobileHotspot,
    [switch]$Https,
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
$demoArguments = @('scripts/local_demo.py', $Action)
if ($LanAddress) { $demoArguments += @('--lan-address', $LanAddress) }
if ($Https) { $demoArguments += '--https' }
& $PythonPath @demoArguments
exit $LASTEXITCODE
