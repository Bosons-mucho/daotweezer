# Build the non-project Red Pitaya bitstream for daotweezer_v1.
# The official non-project flow writes the bitstream to RedPitaya-FPGA/prj/daotweezer_v1/out/red_pitaya.bit.

$RedPitayaRepo = "D:/Berkeley/daotweezer/RedPitaya-FPGA"

if (-not (Test-Path $RedPitayaRepo)) {
    throw "RedPitaya-FPGA repository was not found at $RedPitayaRepo"
}

Set-Location $RedPitayaRepo
make PRJ=daotweezer_v1 MODEL=Z10
