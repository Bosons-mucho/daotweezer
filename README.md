# daotweezer_v1

Project: daotweezer_v1
Board: Red Pitaya STEMlab 125-14 Gen 2
Model flag: Z10
Vivado version: 2020.1

## What this FPGA application does

This project builds a custom Red Pitaya FPGA image for a fixed-delay particle-capture experiment. The FPGA provides a hardware-timed trigger sequence that starts an ultrasonic drive and, after a programmable delay, triggers a second output for a high-voltage optical modulation stage. The goal is to create repeatable timing with low jitter so the delay between ultrasonic particle generation and laser-power increase can be swept and optimized experimentally.

The design uses a simple register interface so software can set the pulse widths and delay values, start the sequence, and read busy/done status. The Python GUI in [software/python_gui](software/python_gui) provides a convenient interface for uploading the bitstream and controlling the settings.

## Quick start

1. Clone the official RedPitaya-FPGA repository outside this repo, for example as a sibling folder next to dao_tweezer.
2. If PowerShell blocks local scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the current terminal before the helper scripts below. This only affects the current PowerShell session.
3. Run [scripts/redpitaya/sync_to_redpitaya_build.ps1](scripts/redpitaya/sync_to_redpitaya_build.ps1) to copy the custom project sources and required IP TCL templates into the external `RedPitaya-FPGA/prj/daotweezer_v1` tree.
4. Run [scripts/redpitaya/install_make.ps1](scripts/redpitaya/install_make.ps1) if `make` is not available on Windows.
5. Run [scripts/redpitaya/build_project.ps1](scripts/redpitaya/build_project.ps1) to generate the full Vivado project in the external `RedPitaya-FPGA` checkout.
6. Open `RedPitaya-FPGA/prj/daotweezer_v1/project/redpitaya.xpr` in Vivado and continue with synthesis, implementation, and bitstream generation as needed.
7. If you make meaningful custom RTL or constraint changes in the external `RedPitaya-FPGA/prj/daotweezer_v1` tree, run [scripts/redpitaya/sync_from_redpitaya_build.ps1](scripts/redpitaya/sync_from_redpitaya_build.ps1) to copy the differences relative to `prj/v0.94` back into this repo and regenerate the `red_pitaya_top.patch` file.

## Where the bitstream goes

After successful implementation, the generated bitstream is written to:
- `RedPitaya-FPGA/prj/daotweezer_v1/out/red_pitaya.bit`

## If synthesis fails

The most common cause is an incomplete sync into `RedPitaya-FPGA/prj/daotweezer_v1`. This project does not use only the custom `rtl/`, `sdc/`, and `patches/` files. It also depends on base Red Pitaya project files such as `ip/systemZ10.tcl` and `rtl/red_pitaya_ps.sv`. If those files are missing, Vivado may generate a project shell but fail later with errors such as `module 'red_pitaya_ps' not found`.

If that happens, rerun [scripts/redpitaya/sync_to_redpitaya_build.ps1](scripts/redpitaya/sync_to_redpitaya_build.ps1) before rebuilding, and make sure you launched the script from a PowerShell session where local scripts are allowed for the current process.

## About make and the scripts

- `make` can be used if your environment has the Red Pitaya build tools available.
- The helper scripts in [scripts/redpitaya](scripts/redpitaya) are the intended workflow for syncing the compact source-only repo into the official Red Pitaya build repo and generating the full Vivado project there.
- The custom RTL, constraints, and patch sources live under [fpga/redpitaya_projects/daotweezer_v1](fpga/redpitaya_projects/daotweezer_v1), while the Python GUI lives under [software/python_gui](software/python_gui).

## Practical use case

In this experiment, the Red Pitaya FPGA acts as a reliable timing controller. The first output starts the ultrasonic driver, and the second output triggers the EO-AM high-voltage pulse driver after a programmable delay. The delay is then swept around the expected particle-arrival time to find the best capture timing.
