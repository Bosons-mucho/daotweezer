import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import paramiko
except ImportError:
    paramiko = None


# =========================
# Red Pitaya register map
# =========================
BASE_ADDR = 0x40700000

CTRL_ADDR   = BASE_ADDR + 0x00
DIO0_W_ADDR = BASE_ADDR + 0x04
DELAY_ADDR  = BASE_ADDR + 0x08
DIO1_W_ADDR = BASE_ADDR + 0x0C


def int_to_hex32(value: int) -> str:
    return f"0x{value:08X}"


class RedPitayaSSH:
    def __init__(self, host: str, user: str = "root", password: str = ""):
        self.host = host
        self.user = user
        self.password = password

    @property
    def target(self) -> str:
        return f"{self.user}@{self.host}"

    def require_paramiko(self):
        if paramiko is None:
            raise RuntimeError(
                "Password mode requires Paramiko. Install it with: py -m pip install paramiko"
            )

    def run_ssh_password(self, command: str) -> str:
        self.require_paramiko()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                self.host,
                username=self.user,
                password=self.password,
                look_for_keys=False,
                allow_agent=False,
                timeout=20,
            )
            stdin, stdout, stderr = client.exec_command(command, timeout=120)
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode(errors="replace").strip()
            err = stderr.read().decode(errors="replace").strip()
        finally:
            client.close()

        if exit_status != 0:
            raise RuntimeError(err or out)

        return out

    def scp_to_rp_password(self, local_path: str, remote_path: str) -> str:
        self.require_paramiko()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                self.host,
                username=self.user,
                password=self.password,
                look_for_keys=False,
                allow_agent=False,
                timeout=20,
            )
            sftp = client.open_sftp()
            try:
                sftp.put(local_path, remote_path)
            finally:
                sftp.close()
        finally:
            client.close()

        return "Upload finished."

    def run_ssh(self, command: str) -> str:
        if self.password:
            return self.run_ssh_password(command)
        result = subprocess.run(
            ["ssh", self.target, command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())

        return result.stdout.strip()

    def scp_to_rp(self, local_path: str, remote_path: str) -> str:
        if self.password:
            return self.scp_to_rp_password(local_path, remote_path)
        result = subprocess.run(
            ["scp", local_path, f"{self.target}:{remote_path}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())

        return result.stdout.strip()

    def load_fpga_fpgautil(self, remote_bitstream_path: str) -> str:
        return self.run_ssh(f"/opt/redpitaya/bin/fpgautil -b {remote_bitstream_path}")

    def load_fpga_overlay_custom(self, project_name: str, remote_bitstream_path: str) -> str:
        return self.run_ssh(
            f"/opt/redpitaya/sbin/overlay.sh {project_name} {remote_bitstream_path}"
        )

    def load_prebuilt_overlay(self, project_name: str) -> str:
        return self.run_ssh(f"/opt/redpitaya/sbin/overlay.sh {project_name}")

    def monitor_write(self, address: int, value: int) -> str:
        return self.run_ssh(f"/opt/redpitaya/bin/monitor {int_to_hex32(address)} {int_to_hex32(value)}")

    def monitor_read(self, address: int) -> int:
        out = self.run_ssh(f"/opt/redpitaya/bin/monitor {int_to_hex32(address)}")

        for token in out.replace("\n", " ").split():
            if token.startswith("0x") or token.startswith("0X"):
                return int(token, 16)

        raise RuntimeError(f"Could not parse monitor output: {out}")

    def read_status(self):
        value = self.monitor_read(CTRL_ADDR)

        # Your Verilog:
        # sysr_data <= {30'd0, done, busy};
        busy = bool(value & 0x1)
        done = bool(value & 0x2)

        return value, busy, done

    def set_widths(self, dio0_width: int, delay_width: int, dio1_width: int):
        self.monitor_write(DIO0_W_ADDR, dio0_width)
        self.monitor_write(DELAY_ADDR, delay_width)
        self.monitor_write(DIO1_W_ADDR, dio1_width)

    def trigger(self):
        self.monitor_write(CTRL_ADDR, 1)


class PulseUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Red Pitaya DIO Pulse Delay Controller")

        self.bitstream_path = tk.StringVar(value="")
        self.host = tk.StringVar(value="169.254.85.194")
        self.user = tk.StringVar(value="root")
        self.password = tk.StringVar(value="")
        self.remote_path = tk.StringVar(value="/root/red_pitaya_top.bit.bin")
        self.overlay_project = tk.StringVar(value="v0.94")

        # Default assumes 125 MHz FPGA clock.
        # 125000 clocks = 1 ms
        # 1250000 clocks = 10 ms
        self.dio0_width = tk.StringVar(value="125000")
        self.delay_width = tk.StringVar(value="1250000")
        self.dio1_width = tk.StringVar(value="125000")

        self.status_text = tk.StringVar(value="Status: not connected")
        self.log_text = None

        self.build_ui()

    def build_ui(self):
        row = 0

        tk.Label(self.root, text="Red Pitaya host").grid(row=row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.host, width=35).grid(row=row, column=1, sticky="we")
        row += 1

        tk.Label(self.root, text="SSH user").grid(row=row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.user, width=35).grid(row=row, column=1, sticky="we")
        row += 1

        tk.Label(self.root, text="SSH password").grid(row=row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.password, show="*", width=35).grid(row=row, column=1, sticky="we")
        row += 1

        tk.Label(self.root, text="Local bitstream").grid(row=row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.bitstream_path, width=60).grid(row=row, column=1, sticky="we")
        tk.Button(self.root, text="Browse", command=self.browse_bitstream).grid(row=row, column=2, sticky="we")
        row += 1

        tk.Label(self.root, text="Remote bitstream path").grid(row=row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.remote_path, width=60).grid(row=row, column=1, sticky="we")
        row += 1

        tk.Label(self.root, text="Overlay project name").grid(row=row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.overlay_project, width=35).grid(row=row, column=1, sticky="we")
        row += 1

        tk.Label(self.root, text="DIO0 width, clocks").grid(row=row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.dio0_width, width=35).grid(row=row, column=1, sticky="we")
        row += 1

        tk.Label(self.root, text="Delay width, clocks").grid(row=row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.delay_width, width=35).grid(row=row, column=1, sticky="we")
        row += 1

        tk.Label(self.root, text="DIO1 width, clocks").grid(row=row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.dio1_width, width=35).grid(row=row, column=1, sticky="we")
        row += 1

        tk.Button(self.root, text="Upload bitstream", command=self.upload_bitstream).grid(row=row, column=0, sticky="we")
        tk.Button(self.root, text="Load FPGA: fpgautil", command=self.load_fpgautil).grid(row=row, column=1, sticky="we")
        tk.Button(self.root, text="Load FPGA: overlay custom", command=self.load_overlay_custom).grid(row=row, column=2, sticky="we")
        row += 1

        tk.Button(self.root, text="Load prebuilt project", command=self.load_prebuilt).grid(row=row, column=0, sticky="we")
        tk.Button(self.root, text="Set widths", command=self.set_widths).grid(row=row, column=1, sticky="we")
        tk.Button(self.root, text="Trigger", command=self.trigger).grid(row=row, column=2, sticky="we")
        row += 1

        tk.Button(self.root, text="Read status", command=self.read_status).grid(row=row, column=0, sticky="we")
        tk.Button(self.root, text="Set widths + Trigger", command=self.set_widths_and_trigger).grid(row=row, column=1, sticky="we")
        row += 1

        tk.Label(self.root, textvariable=self.status_text).grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        self.log_text = tk.Text(self.root, height=16, width=100)
        self.log_text.grid(row=row, column=0, columnspan=3, sticky="nsew")

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(row, weight=1)

    def rp(self) -> RedPitayaSSH:
        return RedPitayaSSH(
            host=self.host.get().strip(),
            user=self.user.get().strip(),
            password=self.password.get(),
        )

    def browse_bitstream(self):
        path = filedialog.askopenfilename(
            title="Select Red Pitaya .bit.bin file",
            filetypes=[
                ("Bit bin files", "*.bit.bin"),
                ("All files", "*.*"),
            ],
        )

        if path:
            self.bitstream_path.set(path)

    def log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def run_background(self, name: str, func):
        def worker():
            try:
                self.status_text.set(f"Status: {name} running...")
                self.log(f"> {name}")

                result = func()

                if result:
                    self.log(str(result))

                self.status_text.set(f"Status: {name} done")

            except Exception as e:
                self.status_text.set(f"Status: {name} failed")
                self.log(f"ERROR: {e}")
                messagebox.showerror(name, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def get_width_values(self):
        dio0 = int(self.dio0_width.get(), 0)
        delay = int(self.delay_width.get(), 0)
        dio1 = int(self.dio1_width.get(), 0)

        # Your Verilog does not protect width = 0.
        # Therefore the Python UI blocks 0 here.
        if dio0 < 1 or delay < 1 or dio1 < 1:
            raise ValueError("All widths must be >= 1 clock.")

        if dio0 > 0xFFFFFFFF or delay > 0xFFFFFFFF or dio1 > 0xFFFFFFFF:
            raise ValueError("All widths must fit in 32 bits.")

        return dio0, delay, dio1

    # =========================
    # FPGA loading functions
    # =========================

    def upload_bitstream(self):
        def task():
            local = self.bitstream_path.get().strip()
            remote = self.remote_path.get().strip()

            if not local:
                raise ValueError("Choose a local .bit.bin file first.")

            return self.rp().scp_to_rp(local, remote)

        self.run_background("upload bitstream", task)

    def load_fpgautil(self):
        def task():
            remote = self.remote_path.get().strip()
            return self.rp().load_fpga_fpgautil(remote)

        self.run_background("load FPGA with fpgautil", task)

    def load_overlay_custom(self):
        def task():
            project = self.overlay_project.get().strip()
            remote = self.remote_path.get().strip()
            return self.rp().load_fpga_overlay_custom(project, remote)

        self.run_background("load FPGA with overlay custom", task)

    def load_prebuilt(self):
        def task():
            project = self.overlay_project.get().strip()
            return self.rp().load_prebuilt_overlay(project)

        self.run_background("load prebuilt project", task)

    # =========================
    # Register control functions
    # =========================

    def read_status(self):
        def task():
            value, busy, done = self.rp().read_status()

            return (
                f"CTRL={int_to_hex32(value)}\n"
                f"busy={busy}\n"
                f"done={done}"
            )

        self.run_background("read status", task)

    def set_widths(self):
        def task():
            dio0, delay, dio1 = self.get_width_values()
            rp = self.rp()

            status_value, busy, done = rp.read_status()

            if busy:
                return (
                    "Blocked width write because FPGA is busy.\n"
                    f"CTRL={int_to_hex32(status_value)}, busy={busy}, done={done}"
                )

            # busy = 0, so writing widths is allowed.
            # done can be 0 initially or 1 after a previous completed pulse.
            # Both are allowed.
            rp.set_widths(dio0, delay, dio1)

            status_value, busy, done = rp.read_status()

            return (
                "Widths written successfully.\n"
                f"DIO0  = {dio0} clocks\n"
                f"Delay = {delay} clocks\n"
                f"DIO1  = {dio1} clocks\n"
                f"CTRL={int_to_hex32(status_value)}, busy={busy}, done={done}"
            )

        self.run_background("set widths", task)

    def trigger(self):
        def task():
            rp = self.rp()

            status_value, busy, done = rp.read_status()

            if busy:
                return (
                    "Blocked trigger because FPGA is busy.\n"
                    f"CTRL={int_to_hex32(status_value)}, busy={busy}, done={done}"
                )

            # busy = 0, so trigger is allowed.
            # done = 0 is allowed for the first trigger after reset/load.
            # done = 1 is allowed for later triggers; Verilog clears done on start.
            rp.trigger()

            status_value, busy, done = rp.read_status()

            return (
                "Trigger sent successfully.\n"
                f"CTRL={int_to_hex32(status_value)}, busy={busy}, done={done}"
            )

        self.run_background("trigger", task)

    def set_widths_and_trigger(self):
        def task():
            dio0, delay, dio1 = self.get_width_values()
            rp = self.rp()

            status_value, busy, done = rp.read_status()

            if busy:
                return (
                    "Blocked width write + trigger because FPGA is busy.\n"
                    f"CTRL={int_to_hex32(status_value)}, busy={busy}, done={done}"
                )

            # Width write is allowed because busy = 0.
            rp.set_widths(dio0, delay, dio1)

            # Check again before trigger.
            status_value, busy, done = rp.read_status()

            if busy:
                return (
                    "Widths were written, but trigger was blocked because FPGA became busy.\n"
                    f"CTRL={int_to_hex32(status_value)}, busy={busy}, done={done}"
                )

            rp.trigger()

            status_value, busy, done = rp.read_status()

            return (
                "Widths written and trigger sent successfully.\n"
                f"DIO0  = {dio0} clocks\n"
                f"Delay = {delay} clocks\n"
                f"DIO1  = {dio1} clocks\n"
                f"CTRL={int_to_hex32(status_value)}, busy={busy}, done={done}"
            )

        self.run_background("set widths and trigger", task)


if __name__ == "__main__":
    root = tk.Tk()
    app = PulseUI(root)
    root.mainloop()