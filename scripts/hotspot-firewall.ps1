param([switch]$Remove)
$ErrorActionPreference='Stop'
$demoRoot=Split-Path -Parent $PSScriptRoot
$demoName='QueueLessPulse-Erode-Hotspot-HTTPS-5000'
$demoIdentity=[Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]::new($demoIdentity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run this narrowly scoped firewall helper as Administrator.' }
$demoAddress=Get-NetIPAddress -AddressFamily IPv4 -IPAddress '192.168.137.1'
$demoAdapter=Get-NetAdapter -InterfaceIndex $demoAddress.InterfaceIndex
if ($demoAddress.PrefixLength -ne 24 -or $demoAdapter.Status -ne 'Up' -or $demoAdapter.InterfaceDescription -notlike '*Wi-Fi Direct Virtual*') { throw 'Expected active Windows Mobile Hotspot at 192.168.137.1/24.' }
$demoRule=Get-NetFirewallRule -Name $demoName -ErrorAction SilentlyContinue
if ($demoRule) {
    $demoPort=$demoRule | Get-NetFirewallPortFilter
    $demoIp=$demoRule | Get-NetFirewallAddressFilter
    $demoInterface=$demoRule | Get-NetFirewallInterfaceFilter
    if ($demoPort.LocalPort -ne '5000' -or $demoPort.Protocol -ne 'TCP' -or $demoIp.LocalAddress -ne '192.168.137.1' -or $demoIp.RemoteAddress -notin @('192.168.137.0/24','192.168.137.0/255.255.255.0') -or $demoRule.Profile -ne 'Private' -or $demoInterface.InterfaceAlias -ne $demoAdapter.Name) { throw 'Existing rule differs from the expected scope; left unchanged.' }
}
if ($Remove) {
    if ($demoRule) { $demoRule | Remove-NetFirewallRule }
    $demoResult=@{Removed=$true;Name=$demoName}
} else {
    if (-not $demoRule) {
        $demoRule=New-NetFirewallRule -Name $demoName -DisplayName 'QueueLess Pulse Erode demo — hotspot HTTPS only' -Direction Inbound -Action Allow -Enabled True -Protocol TCP -LocalPort 5000 -LocalAddress '192.168.137.1' -RemoteAddress '192.168.137.0/24' -InterfaceAlias $demoAdapter.Name -Profile Private -EdgeTraversalPolicy Block
    }
    $demoResult=@{Name=$demoName;Profile='Private';LocalAddress='192.168.137.1';LocalPort=5000;Protocol='TCP';RemoteAddress='192.168.137.0/24';InterfaceAlias=$demoAdapter.Name;Enabled=$true}
}
$demoResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $demoRoot '.tmp/hotspot-firewall-status.json') -Encoding UTF8
