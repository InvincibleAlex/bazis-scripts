$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Security
Write-Host 'Configurare acces la baza BAZIS RG:14357 pentru acest utilizator Windows.'
Write-Host 'Parola este salvata criptat in profilul local, niciodata in folderul comun.'
$secure=Read-Host 'Parola Firebird pentru utilizatorul SYSDBA' -AsSecureString
$pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $bytes=[Text.Encoding]::UTF8.GetBytes($plain)
    try {
        $encrypted=[Security.Cryptography.ProtectedData]::Protect($bytes,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
        $credentialFolder=Join-Path $env:APPDATA 'BazisExport'
        New-Item -ItemType Directory -Path $credentialFolder -Force | Out-Null
        [IO.File]::WriteAllBytes((Join-Path $credentialFolder 'firebird-password.dpapi'),$encrypted)
    } finally { [Array]::Clear($bytes,0,$bytes.Length);$plain=$null }
} finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer);$secure.Dispose() }
Write-Host 'Parola a fost salvata. Verific conexiunea in mod read-only...'
$python=Join-Path $PSScriptRoot 'runtime\python\python.exe'
$reader=Join-Path $PSScriptRoot 'tools\read_material_designations.py'
'[]' | & $python $reader
if($LASTEXITCODE -ne 0){throw 'Verificarea nu a reusit. Repetati configurarea cu parola corecta.'}
Write-Host 'Configurare reusita. Puteti rula Export Cubis.js in BAZIS.'
Read-Host 'Apasati Enter pentru inchidere'
