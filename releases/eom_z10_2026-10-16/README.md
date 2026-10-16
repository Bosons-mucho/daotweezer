# EOM Z10 firmware and GUI — 2026-10-16

This version directory is an addition. All older repository files and firmware
paths are retained unchanged.

## Files

| File | What it does | Needed for normal use? |
|---|---|---|
| [README.md](README.md) | Setup and usage instructions for this firmware/GUI pair. | Read when setting up. |
| [SHA256SUMS](SHA256SUMS) | SHA-256 checksums for verifying downloaded file integrity; not a program. | Optional integrity check. |
| [eom_fpga_trigger_gui.py](eom_fpga_trigger_gui.py) | Main GUI. Run this on the computer to configure timing, trigger, read status, and Clear. | **Yes -- this is the program to run.** |
| [red_pitaya_top.bit.bin](red_pitaya_top.bit.bin) | FPGA firmware. Load this onto the Red Pitaya Z10 separately; the GUI does not load it. | **Yes -- the board must have this firmware loaded.** |
| [test_eom_fpga_trigger_gui.py](test_eom_fpga_trigger_gui.py) | Offline automated tests using simulated connections. No board connection or hardware pulses. | **Not needed for normal use.** Run only when testing the GUI software. |

For normal operation, use the **main GUI + FPGA firmware**. The test file is for
offline software checks and does not need to be run before each experiment.

## Run

Load the custom EOM firmware separately. This GUI does not upload or flash it.
From this directory:

```sh
py -m pip install paramiko
py eom_fpga_trigger_gui.py
```

Enter SSH settings and confirm that the custom EOM image is loaded. An empty
password enables local SSH keys/agent. Unknown SSH host keys are automatically
accepted, as in the previous GUI; first-contact identity is not verified.

Enter positive DIO0 HIGH width and delay in milliseconds. They are rounded to
125 MHz cycles (8 ns). Zero cycles, nonfinite inputs, and overflow are rejected.
The delay is measured from DIO0 falling to DIO1 falling. DIO1 starts HIGH and
is expected to remain LOW after completion until Clear/Reset.

Trigger requires IDLE. The program checks status, writes and reads back both
parameters, checks IDLE again, sends Start once, and polls BUSY/DONE. It will not
trigger while BUSY or DONE. Explicitly press Clear before rearming; Trigger does
not silently abort an old sequence or release a LOW hold.

During a running task, Clear is queued and processed serially after the current
SSH operation returns. Clear is not a hard real-time emergency stop. The program
does not automatically resend Start following communication failure or timeout;
a timed-out write may already have executed. Read status or explicitly Clear.
Closing a connection with an exception still restores the GUI controls.

The custom register block is `0x40700000`: CTRL +0, DIO0 width +4, delay +8.
DIO1 width +12 is stored but unused by the state machine. Use only one controller
per board. This firmware has no identity register or command acceptance counter.

## Validation and limitations

```sh
py -B test_eom_fpga_trigger_gui.py
```

25 offline tests passed, along with a real Tk hidden-window initialization check.
Six operation sequences emitted by this updated GUI were replayed through the
final routed netlist corresponding to this binary. The same netlist also passed
358 normal timing combinations and boundary checks. That functional simulation
does not emulate Linux, the SSH network, or physical electrical behavior.

**No physical Red Pitaya validation has been performed.** Existing firmware AXI
backpressure response and error propagation defects remain. The GUI cannot repair
them. Hardware zero-count underflow and bare-Start hold release also remain;
the GUI blocks these normal-client inputs. Register status does not prove actual
pin levels. Test using measurement equipment before experimental use.

The binary was copied byte-for-byte from the original final Vivado 2020.1
`project_EOM_CLEAN` output. It is not the independent audit rebuild. Neither RTL
nor XDC was changed for this upload. The compact source build elsewhere in this
repository is not asserted to regenerate this exact binary.
