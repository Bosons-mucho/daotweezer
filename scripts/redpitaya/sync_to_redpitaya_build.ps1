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
$ReferenceProject = Join-Path $RedPitayaRepo "prj\v0.94"
$ReferenceIpDir = Join-Path $ReferenceProject "ip"
$ReferenceRtlDir = Join-Path $ReferenceProject "rtl"
$TargetIpDir = Join-Path $RedPitayaPrj "ip"
$TargetRtlDir = Join-Path $RedPitayaPrj "rtl"
$OverlayItems = @("rtl", "sdc", "patches")

if (-not (Test-Path $RedPitayaRepo)) {
    throw "RedPitaya-FPGA repository was not found at $RedPitayaRepo"
}

if (-not (Test-Path $MainRepoProject)) {
    throw "Main project source tree was not found at $MainRepoProject"
}

if (-not (Test-Path $ReferenceIpDir)) {
    throw "Reference Red Pitaya project IP directory was not found at $ReferenceIpDir"
}

if (-not (Test-Path $ReferenceRtlDir)) {
    throw "Reference Red Pitaya project RTL directory was not found at $ReferenceRtlDir"
}

if (-not (Test-Path $RedPitayaPrj)) {
    New-Item -ItemType Directory -Path $RedPitayaPrj -Force | Out-Null
}

if (Test-Path $TargetIpDir) {
    Remove-Item -LiteralPath $TargetIpDir -Recurse -Force
}

Copy-Item -LiteralPath $ReferenceIpDir -Destination $TargetIpDir -Recurse -Force
Write-Host "Seeded project IP templates from $ReferenceIpDir"

if (Test-Path $TargetRtlDir) {
    Remove-Item -LiteralPath $TargetRtlDir -Recurse -Force
}

Copy-Item -LiteralPath $ReferenceRtlDir -Destination $TargetRtlDir -Recurse -Force
Write-Host "Seeded base project RTL from $ReferenceRtlDir"

foreach ($syncItem in $OverlayItems) {
    $sourcePath = Join-Path $MainRepoProject $syncItem
    $destinationPath = Join-Path $RedPitayaPrj $syncItem

    if (-not (Test-Path $sourcePath)) {
        throw "Expected source path was not found: $sourcePath"
    }

    if ($syncItem -ne "rtl" -and (Test-Path $destinationPath)) {
        Remove-Item -LiteralPath $destinationPath -Recurse -Force
    }

    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Recurse -Force
    Write-Host "Synced $syncItem to $destinationPath"
}

Write-Host "Sync complete."
Write-Host "What it does:"
Write-Host "- seeds the required project IP TCL files from prj\v0.94\ip"
Write-Host "- seeds the base project RTL from prj\v0.94\rtl"
Write-Host "- overlays custom source folders (rtl, sdc, patches)"
Write-Host "- does not copy Vivado-generated project artifacts"
Write-Host "- leaves the external RedPitaya-FPGA repo responsible for full project generation"
Write-Host "Next commands:"
Write-Host "cd $RepoRoot\scripts\redpitaya"
Write-Host ".\install_make.ps1"
Write-Host ".\build_project.ps1"
