$MainRepoProject = "D:/Berkeley/daotweezer/redpitaya-server/daotweezer/fpga/redpitaya_projects/daotweezer_v1"
$RedPitayaRepo = "D:/Berkeley/daotweezer/RedPitaya-FPGA"
$RedPitayaPrj = "$RedPitayaRepo/prj/daotweezer_v1"

if (-not (Test-Path $RedPitayaRepo)) {
    throw "RedPitaya-FPGA repository was not found at $RedPitayaRepo"
}

if (-not (Test-Path $MainRepoProject)) {
    throw "Main project source tree was not found at $MainRepoProject"
}

if (Test-Path $RedPitayaPrj) {
    $timestamp = Get-Date -Format yyyyMMdd_HHmmss
    $backupPath = "$RedPitayaPrj.backup_$timestamp"
    Rename-Item -Path $RedPitayaPrj -NewName (Split-Path $backupPath -Leaf)
    Write-Host "Backed up existing project folder to $backupPath"
}

Copy-Item -Path $MainRepoProject -Destination $RedPitayaPrj -Recurse -Force

Write-Host "Sync complete."
Write-Host "Next commands:"
Write-Host "cd $RedPitayaRepo"
Write-Host "make project PRJ=daotweezer_v1 MODEL=Z10"
Write-Host "make PRJ=daotweezer_v1 MODEL=Z10"
