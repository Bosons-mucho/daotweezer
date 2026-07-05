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
2. Copy or sync the custom project tree from this repo into the RedPitaya-FPGA build tree if needed.
3. Open the project file at [fpga/redpitaya_projects/daotweezer_v1/project/redpitaya.xpr](fpga/redpitaya_projects/daotweezer_v1/project/redpitaya.xpr) in Vivado.
4. Run Synthesis, Implementation, and Generate Bitstream.

## Where the bitstream goes

After successful implementation, the generated bitstream is written to:
- [fpga/redpitaya_projects/daotweezer_v1/project/redpitaya.runs/impl_1/red_pitaya_top.bit](fpga/redpitaya_projects/daotweezer_v1/project/redpitaya.runs/impl_1/red_pitaya_top.bit)

## About make and the scripts

- `make` can be used if your environment has the Red Pitaya build tools available.
- The helper scripts in [scripts/redpitaya](scripts/redpitaya) are convenience scripts for syncing/building the project and are not required for Vivado itself.
- The custom RTL and Python GUI sources live under [fpga/redpitaya_projects/daotweezer_v1](fpga/redpitaya_projects/daotweezer_v1) and [software/python_gui](software/python_gui).

## Practical use case

In this experiment, the Red Pitaya FPGA acts as a reliable timing controller. The first output starts the ultrasonic driver, and the second output triggers the EO-AM high-voltage pulse driver after a programmable delay. The delay is then swept around the expected particle-arrival time to find the best capture timing.
