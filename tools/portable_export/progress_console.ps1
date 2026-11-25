param([Parameter(Mandatory=$true)][string]$LogPath,[Parameter(Mandatory=$true)][string]$StatePath)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle='BAZIS - Export Cubis / Komodo / Holver'
Write-Host 'BAZIS | Export Cubis + Komodo + Holver' -ForegroundColor Cyan
Write-Host 'Terminal activ. Pregatesc exportul...'
[IO.File]::WriteAllText(($StatePath+'.opened'),'ready')
$last=0
$frames=@('|','/','-','\');$frameIndex=0;$percent=0
function Progress-Line([int]$value,[string]$spin){
    $filled=[int][Math]::Floor($value/5)
    return ('['+(([string][char]0x2588)*$filled)+(([string][char]0x2591)*(20-$filled))+'] '+$value+'% ['+$spin+']')
}
function Update-Progress([string]$line){
    $stages=@{
        'Citire placi'=5;'Citite '=10;'Citire model terminata'=20;'Citire baza de date reusita'=25;
        'Identific folderul'=30;'Raport JSON salvat'=32;'CSV salvat'=35;
        'Cubis: generare'=40;'Cubis REUSIT'=60;'Cubis EROARE'=60;
        'Komodo: generare'=65;'Komodo REUSIT'=80;'Komodo EROARE'=80;
        'Holver: generare'=85;'Holver REUSIT'=95;'Holver EROARE'=95;'Folder rezultate'=98
    }
    foreach($key in $stages.Keys){if($line.Contains($key)){$script:percent=[Math]::Max($script:percent,$stages[$key])}}
}
$animate=-not [Console]::IsOutputRedirected
function Clear-LoadingLine {if($animate){Write-Host -NoNewline ("`r"+(' '*65)+"`r")}}
$deadline=[DateTime]::UtcNow.AddMinutes(30)
try {
    while($true){
        $state=if(Test-Path -LiteralPath $StatePath){[IO.File]::ReadAllText($StatePath)}else{''}
        if(Test-Path -LiteralPath $LogPath){
            $lines=@(Get-Content -LiteralPath $LogPath -Encoding UTF8)
            if($lines.Count -gt $last){Clear-LoadingLine}
            for($i=$last;$i -lt $lines.Count;$i++){Update-Progress $lines[$i];Write-Host $lines[$i]}
            $last=$lines.Count
        }
        if($state -in @('done','error')){
            Clear-LoadingLine
            if($state -eq 'done'){Write-Host (Progress-Line 100 '|');Write-Host 'TERMINAT. Poti inchide terminalul.' -ForegroundColor Green}
            else{Write-Host 'EXPORT CU PROBLEME. Vezi detaliile de mai sus.' -ForegroundColor Red}
            break
        }
        if([DateTime]::UtcNow -gt $deadline){Clear-LoadingLine;Write-Host 'Nu s-a primit confirmarea finala in 30 de minute.' -ForegroundColor Yellow;break}
        if($animate){Write-Host -NoNewline ("`r"+(Progress-Line $percent $frames[$frameIndex%4]));$frameIndex++}
        Start-Sleep -Milliseconds 150
    }
} finally {
    Clear-LoadingLine
    foreach($file in @($LogPath,$StatePath,($StatePath+'.opened'))){
        if(Test-Path -LiteralPath $file){Remove-Item -LiteralPath $file -ErrorAction SilentlyContinue}
    }
}
if(-not [Console]::IsInputRedirected){
    Write-Host '';Write-Host 'Apasa Enter sau orice alta tasta pentru inchidere.' -ForegroundColor Cyan
    while([Console]::KeyAvailable){[void][Console]::ReadKey($true)}
    [void][Console]::ReadKey($true)
}
