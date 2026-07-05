# Red Pitaya project migration notes

## What changed

The dao_tweezer repository keeps only the essential custom Red Pitaya pulse-delay project sources under fpga/redpitaya_projects/daotweezer_v1 instead of tracking the entire embedded RedPitaya-FPGA repository or a full generated Vivado project.

## Preserved files

The following custom sources were preserved and copied into the new project tree:

- pulse_delay_demo and pulse_delay_reg RTL modules
- the modified red_pitaya_top.sv integration point based on RedPitaya-FPGA/prj/v0.94/rtl/red_pitaya_top.sv
- the Red Pitaya constraint file used for this project
- the Python GUI and control scripts for triggering and bitstream loading

## Where the official repository should live

The official RedPitaya-FPGA checkout should live outside the dao_tweezer repository, for example alongside it in a sibling directory, and the sync scripts will copy only the custom source folders into RedPitaya-FPGA/prj/daotweezer_v1.

## Reproducing the Vivado project

1. Place the official RedPitaya-FPGA repository outside this repository.
2. If PowerShell blocks local scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the current terminal before the helper scripts below. This only affects the current PowerShell session.
3. Run scripts/redpitaya/sync_to_redpitaya_build.ps1.
4. Run `scripts/redpitaya/install_make.ps1` if `make` is not already installed on Windows.
5. Run `scripts/redpitaya/build_project.ps1`.
6. Open `RedPitaya-FPGA/prj/daotweezer_v1/project/redpitaya.xpr` in Vivado.
7. If you want a local copy of the generated project for inspection, run `scripts/redpitaya/build_project.ps1 -MirrorLocalProject`. This mirrors into `_generated_project/`, which is not source of truth.

## What should and should not be committed

The following should be committed in dao_tweezer:

- fpga/redpitaya_projects/daotweezer_v1/rtl/
- fpga/redpitaya_projects/daotweezer_v1/sdc/
- fpga/redpitaya_projects/daotweezer_v1/patches/
- software/python_gui/
- scripts/redpitaya/

Generated Vivado artifacts such as project/, _generated_project/, out/, tmp/, .runs/, .cache/, .hw/, .ip_user_files/, .sim/, .gen/, .srcs/, and .data/ should not be committed.

## Notes on uncertainty

If a file could not be confidently distinguished between a base Red Pitaya generated artifact and a custom modification, it was preserved in the backup and documented here rather than deleted.
