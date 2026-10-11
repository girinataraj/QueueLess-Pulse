param([ValidateSet('Verification','Staging')][string]$Variant='Verification', [string]$StagingOrigin)
$ErrorActionPreference='Stop'
$demoCandidateRoot=Split-Path $PSScriptRoot -Parent
$privateDirectory=Join-Path $demoCandidateRoot '.tmp\android-signing'
New-Item -ItemType Directory -Force $privateDirectory | Out-Null
$currentSid=([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value
& icacls.exe $privateDirectory /inheritance:r /grant:r "*${currentSid}:(OI)(CI)(F)" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not protect private signing directory' }
$profilePath=Join-Path $privateDirectory 'private-signing.json'
$keystorePath=Join-Path $privateDirectory 'evaluation-signing.jks'
if (!(Test-Path -LiteralPath $profilePath)) {
    $randomBytes=New-Object byte[] 48
    $generator=[System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
    $generatedPassword=[Convert]::ToBase64String($randomBytes)
    @{store_password=$generatedPassword;key_password=$generatedPassword} | ConvertTo-Json | Set-Content -LiteralPath $profilePath
}
$privateSigning=Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
$env:QUEUELESS_ANDROID_KEYSTORE=$keystorePath
$env:QUEUELESS_ANDROID_KEYSTORE_PASSWORD=$privateSigning.store_password
$env:QUEUELESS_ANDROID_KEY_PASSWORD=$privateSigning.key_password
if (!$env:ANDROID_HOME) { $env:ANDROID_HOME='C:\Android' }
if (!$env:JAVA_HOME) { $env:JAVA_HOME='C:\Program Files\Microsoft\jdk-21.0.12.8-hotspot' }
try {
    if (!(Test-Path -LiteralPath $keystorePath)) {
        & "$env:JAVA_HOME\bin\keytool.exe" -genkeypair -keystore $keystorePath -alias queueless-evaluation -storetype JKS -keyalg RSA -keysize 3072 -validity 3650 -dname 'CN=QueueLess Pulse Evaluation Build' -storepass:env QUEUELESS_ANDROID_KEYSTORE_PASSWORD -keypass:env QUEUELESS_ANDROID_KEY_PASSWORD
        if ($LASTEXITCODE -ne 0) { throw 'Evaluation signing key generation failed' }
    }
    if ($Variant -eq 'Staging') {
        if (!$StagingOrigin) { throw 'StagingOrigin must identify the approved and verified deployment' }
        $env:QUEUELESS_STAGING_ORIGIN=$StagingOrigin
    } else { Remove-Item Env:\QUEUELESS_STAGING_ORIGIN -ErrorAction SilentlyContinue }
    Push-Location (Join-Path $demoCandidateRoot 'mobile')
    try { & npx.cmd --yes pnpm@11.25.0 install --frozen-lockfile --strict-peer-dependencies; if ($LASTEXITCODE) { throw 'Mobile install failed' }; & npx.cmd --yes pnpm@11.25.0 run sync; if ($LASTEXITCODE) { throw 'Capacitor sync failed' } } finally { Pop-Location }
    Push-Location (Join-Path $demoCandidateRoot 'mobile\android')
    try {
        & .\gradlew.bat "test${Variant}DebugUnitTest" "lint${Variant}Release" "assemble${Variant}Release" exportRuntimeDependencies --console=plain
        if ($LASTEXITCODE) { throw 'Android checks/build failed' }
    } finally { Pop-Location }
    & 'E:\Internship\New folder\DR\.venv\Scripts\python.exe' (Join-Path $PSScriptRoot 'audit-android-dependencies.py')
    if ($LASTEXITCODE) { throw 'Android runtime dependency security check failed' }
    $flavor=$Variant.ToLowerInvariant()
    $source=Join-Path $demoCandidateRoot "mobile\android\app\build\outputs\apk\$flavor\release\app-$flavor-release.apk"
    $artifacts=Join-Path $demoCandidateRoot 'evidence\android'
    New-Item -ItemType Directory -Force $artifacts | Out-Null
    $artifact=Join-Path $artifacts "QueueLess-Pulse-$Variant.apk"
    Copy-Item -LiteralPath $source -Destination $artifact
    $signer=Join-Path $env:ANDROID_HOME 'build-tools\35.0.0\apksigner.bat'
    & $signer verify --verbose --print-certs $artifact
    if ($LASTEXITCODE) { throw 'APK signature verification failed' }
    Get-FileHash -Algorithm SHA256 -LiteralPath $artifact | Select-Object Algorithm,Hash,Path
    Write-Output "Private signing/rebuild credentials: $profilePath"
} finally {
    Remove-Item Env:\QUEUELESS_ANDROID_KEYSTORE,Env:\QUEUELESS_ANDROID_KEYSTORE_PASSWORD,Env:\QUEUELESS_ANDROID_KEY_PASSWORD,Env:\QUEUELESS_STAGING_ORIGIN -ErrorAction SilentlyContinue
}
