param([Parameter(Mandatory=$true)][string]$LogPath,[Parameter(Mandatory=$true)][string]$StatePath)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle='BAZIS - Export Cubis / Komodo / Holver'
Write-Host 'BAZIS | Export Cubis + Komodo + Holver' -ForegroundColor Cyan
Write-Host 'Terminal activ. Pregatesc exportul...'
[IO.File]::WriteAllText(($StatePath+'.opened'),'ready')
$last=0
$frames=@('|','/','-','\');$frameIndex=0
$animate=-not [Console]::IsOutputRedirected
function Clear-LoadingLine {if($animate){Write-Host -NoNewline ("`r"+(' '*65)+"`r")}}
$deadline=[DateTime]::UtcNow.AddMinutes(30)
try {
    while($true){
        $state=if(Test-Path -LiteralPath $StatePath){[IO.File]::ReadAllText($StatePath)}else{''}
        if(Test-Path -LiteralPath $LogPath){
            $lines=@(Get-Content -LiteralPath $LogPath -Encoding UTF8)
            if($lines.Count -gt $last){Clear-LoadingLine}
            for($i=$last;$i -lt $lines.Count;$i++){Write-Host $lines[$i]}
            $last=$lines.Count
        }
        if($state -in @('done','error')){
            Clear-LoadingLine
            if($state -eq 'done'){Write-Host 'TERMINAT. Poti inchide terminalul.' -ForegroundColor Green}
            else{Write-Host 'EXPORT CU PROBLEME. Vezi detaliile de mai sus.' -ForegroundColor Red}
            break
        }
        if([DateTime]::UtcNow -gt $deadline){Clear-LoadingLine;Write-Host 'Nu s-a primit confirmarea finala in 30 de minute.' -ForegroundColor Yellow;break}
        if($animate){Write-Host -NoNewline ("`r["+$frames[$frameIndex%4]+'] Se lucreaza...');$frameIndex++}
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
