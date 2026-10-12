param([ValidateSet('start','restart','status')][string]$Action='start', [Parameter(Mandatory=$true)][string]$ProfilePath, [string]$PythonPath='python', [int]$Port=5002)
$ErrorActionPreference='Stop'
$productRoot=Split-Path $PSScriptRoot -Parent
$productRunner=Join-Path $PSScriptRoot 'product_preview.py'
$productProfileFile=(Resolve-Path -LiteralPath $ProfilePath).Path
$productProfile=Get-Content -Raw -LiteralPath $productProfileFile | ConvertFrom-Json
if($productProfile.host -ne '127.0.0.1' -or $productProfile.port -ne 55436 -or $productProfile.database -ne 'queueless_product_demo'){throw 'Only the isolated product-preview profile is accepted'}
$productPrivate=Split-Path $productProfileFile -Parent
$productData=Join-Path $productPrivate 'postgres18-data'
if(!(Test-Path -LiteralPath (Join-Path $productData 'PG_VERSION'))){throw 'The dedicated product PostgreSQL cluster is missing; no schema creation or fallback is attempted'}
$productPgCtl='C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe'
$productProcesses=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -and $_.CommandLine -match [regex]::Escape($productRunner) })
if($Action -eq 'status'){Write-Output "Local application processes: $($productProcesses.Count). URL: http://127.0.0.1:$Port/app/"; & $productPgCtl -D $productData status; exit $LASTEXITCODE}
if($Action -eq 'restart'){foreach($productProcess in $productProcesses){Stop-Process -Id $productProcess.ProcessId -ErrorAction SilentlyContinue}}
elseif($productProcesses.Count){Write-Output "Already running: http://127.0.0.1:$Port/app/";exit 0}
if(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue){throw "Port $Port is already owned by another process. No unrelated server was stopped."}
& $productPgCtl -D $productData status *> $null
if($LASTEXITCODE){& $productPgCtl -D $productData -l (Join-Path $productPrivate 'postgres.log') -o '-h 127.0.0.1 -p 55436' start -w *> $null;if($LASTEXITCODE){throw 'Dedicated local PostgreSQL could not start. No other server was selected.'}}
Start-Process -FilePath $PythonPath -ArgumentList "`"$productRunner`" --profile `"$productProfileFile`" --port $Port" -WorkingDirectory $productRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $productPrivate 'flask-out.log') -RedirectStandardError (Join-Path $productPrivate 'flask-error.log') | Out-Null
$productReady=$false
for($attempt=0;$attempt -lt 20;$attempt++){
    try{$productHealth=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2;if($productHealth.status -eq 'ok'){$productReady=$true;break}}catch{}
    Start-Sleep -Milliseconds 500
}
if(!$productReady){throw "Preview did not become healthy. Inspect private logs in $productPrivate; no fallback or hosted service was changed."}
Write-Output "Healthy isolated preview: http://127.0.0.1:$Port/app/; PostgreSQL remains 127.0.0.1:55436. Private logs: $productPrivate"
