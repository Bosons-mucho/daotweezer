# Build the Vivado project for the daotweezer_v1 Red Pitaya target.
# This generates the Vivado GUI project under the external RedPitaya-FPGA checkout
# and mirrors it into this repository's project tree.

$MainRepoProject = "D:/Berkeley/daotweezer/redpitaya-server/daotweezer/fpga/redpitaya_projects/daotweezer_v1"
$RedPitayaRepo = "D:/Berkeley/daotweezer/RedPitaya-FPGA"
$LocalProjectDir = "$MainRepoProject/project"
$CandidateProjectDirs = @(
    "$RedPitayaRepo/prj/daotweezer_v1/project",
    "$RedPitayaRepo/prj/v0.94/project",
    "$RedPitayaRepo/prj/project"
)

if (-not (Test-Path $RedPitayaRepo)) {
    throw "RedPitaya-FPGA repository was not found at $RedPitayaRepo"
}

if (-not (Test-Path $MainRepoProject)) {
    throw "Main project source tree was not found at $MainRepoProject"
}

Set-Location $RedPitayaRepo
make project PRJ=daotweezer_v1 MODEL=Z10

$ExternalProjectDir = $CandidateProjectDirs | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $ExternalProjectDir) {
    throw "No Vivado project directory was found under the expected Red Pitaya project locations."
}

if (Test-Path $LocalProjectDir) {
    Remove-Item -Path $LocalProjectDir -Recurse -Force
}

New-Item -ItemType Directory -Path $LocalProjectDir -Force | Out-Null
Get-ChildItem -Path $ExternalProjectDir -Force | Copy-Item -Destination $LocalProjectDir -Recurse -Force

Write-Host "Mirrored generated Vivado project to $LocalProjectDir"
