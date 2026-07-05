param(
    [string]$MainRepoProject,
    [string]$RedPitayaRepo
)

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$WorkspaceRoot = Split-Path $RepoRoot -Parent

if (-not $MainRepoProject) {
    $MainRepoProject = Join-Path $RepoRoot "fpga\redpitaya_projects\daotweezer_v1"
}

if (-not $RedPitayaRepo) {
    $RedPitayaRepo = Join-Path $WorkspaceRoot "RedPitaya-FPGA"
}

$RedPitayaPrj = Join-Path $RedPitayaRepo "prj\daotweezer_v1"
$SyncItems = @("rtl", "sdc", "patches")

if (-not (Test-Path $RedPitayaRepo)) {
    throw "RedPitaya-FPGA repository was not found at $RedPitayaRepo"
}

if (-not (Test-Path $MainRepoProject)) {
    throw "Main project source tree was not found at $MainRepoProject"
}

if (-not (Test-Path $RedPitayaPrj)) {
    New-Item -ItemType Directory -Path $RedPitayaPrj -Force | Out-Null
}

foreach ($syncItem in $SyncItems) {
    $sourcePath = Join-Path $MainRepoProject $syncItem
    $destinationPath = Join-Path $RedPitayaPrj $syncItem

    if (-not (Test-Path $sourcePath)) {
        throw "Expected source path was not found: $sourcePath"
    }

    if (Test-Path $destinationPath) {
        Remove-Item -LiteralPath $destinationPath -Recurse -Force
    }

    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Recurse -Force
    Write-Host "Synced $syncItem to $destinationPath"
}

Write-Host "Sync complete."
Write-Host "What it does:"
Write-Host "- copies only custom source folders (rtl, sdc, patches)"
Write-Host "- does not copy Vivado-generated project artifacts"
Write-Host "- leaves the external RedPitaya-FPGA repo responsible for full project generation"
Write-Host "Next commands:"
Write-Host "cd $RepoRoot\scripts\redpitaya"
Write-Host ".\install_make.ps1"
Write-Host ".\build_project.ps1"
