$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$net = Join-Path $ProjectRoot "net\robust.net.xml"
$inDir = Join-Path $ProjectRoot "process\trips_xml"
$outDir = Join-Path $ProjectRoot "process\routes_raw"
$logDir = Join-Path $ProjectRoot "process\logs_duarouter"

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Get-ChildItem $inDir -Filter "porto_20131128.trips.xml" | Sort-Object Name | ForEach-Object {
    $inFile = $_.FullName
    $base = $_.BaseName.Replace(".trips", "")
    $outFile = Join-Path $outDir ($base + ".rou.xml")
    $logFile = Join-Path $logDir ($base + ".log.txt")

    Write-Host ""
    Write-Host "=== duarouter $base ==="
    Write-Host "[IN ] $inFile"

    duarouter -n $net -r $inFile -o $outFile `
        --ignore-errors true `
        --repair true `
        --routing-algorithm dijkstra `
        --weights.random-factor 0 `
        --verbose true 2>&1 | Tee-Object -FilePath $logFile

    Write-Host "[OUT] $outFile"
    Write-Host "[LOG] $logFile"
}
