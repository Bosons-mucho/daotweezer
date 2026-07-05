# daotweezer_v1

Project: daotweezer_v1
Board: Red Pitaya STEMlab 125-14 Gen 2
Model flag: Z10
Base project: RedPitaya-FPGA/prj/v0.94
Vivado version: 2020.1

## Build workflow

1. Clone the official RedPitaya-FPGA repository outside this dao_tweezer repository.
2. Run scripts/redpitaya/sync_to_redpitaya_build.ps1 from this repository.
3. Change into the external RedPitaya-FPGA checkout.
4. Run `make project PRJ=daotweezer_v1 MODEL=Z10`.
5. Open RedPitaya-FPGA/prj/daotweezer_v1/project/redpitaya.xpr in Vivado.
6. Generate the bitstream from the GUI, or run `make PRJ=daotweezer_v1 MODEL=Z10` for the non-project flow.

## Notes

- The custom RTL and Python control sources are preserved in this project tree.
- Generated Vivado output such as project/, out/, tmp/, .runs/, .cache/, .ip_user_files/, .sim/, .gen/, and .srcs/ is intentionally not committed.
- The final bitstream appears under RedPitaya-FPGA/prj/daotweezer_v1/out/red_pitaya.bit in the non-project flow and under RedPitaya-FPGA/prj/daotweezer_v1/project/ in the project flow.
