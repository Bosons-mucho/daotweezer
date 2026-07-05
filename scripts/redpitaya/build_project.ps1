# Build the Vivado project for the daotweezer_v1 Red Pitaya target.
# This generates the Vivado GUI project under RedPitaya-FPGA/prj/daotweezer_v1/project/.

$RedPitayaRepo = "D:/Berkeley/daotweezer/RedPitaya-FPGA"

if (-not (Test-Path $RedPitayaRepo)) {
    throw "RedPitaya-FPGA repository was not found at $RedPitayaRepo"
}

Set-Location $RedPitayaRepo
make project PRJ=daotweezer_v1 MODEL=Z10
