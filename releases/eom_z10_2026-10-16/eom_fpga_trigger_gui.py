"""Main GUI: run this file for normal EOM operation; requires paramiko.

Controls the existing Red Pitaya Z10 firmware. Firmware must be loaded separately.

No bitstream changes. CTRL=0x40700000, width=+4, delay=+8, cycles at 125 MHz.
SSH success and register status do not prove physical output levels. This client
does not repair the existing firmware's AXI response/error propagation defects.
"""

import math
import queue
import re
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

try:
    import paramiko
except ImportError:
    paramiko = None

BASE = 0x40700000
REG_CTRL, REG_DIO0, REG_DELAY, REG_DIO1 = (BASE + n for n in (0, 4, 8, 12))
CLK_HZ = 125_000_000
MAX_U32 = 0xFFFFFFFF
SSH_TIMEOUT = 8
POLL_INTERVAL = 0.1
COMPLETION_MARGIN = 5.0
REGISTERS = {REG_CTRL, REG_DIO0, REG_DELAY, REG_DIO1}


def validate_cycles(value):
    if type(value) is not int or not 1 <= value <= MAX_U32:
        raise ValueError("时长必须对应 1..4294967295 个时钟周期，不能为零")
    return value


def ms_to_cycles(ms):
    if not math.isfinite(ms) or ms <= 0:
        raise ValueError("请输入有限的正数时长")
    return validate_cycles(round(ms * (CLK_HZ / 1000.0)))


def parse_register(text):
    value = text.strip()
    if not re.fullmatch(r"(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})", value):
        raise RuntimeError(f"寄存器返回格式异常：{value!r}")
    number = int(value, 16 if value.lower().startswith("0x") else 10)
    if not 0 <= number <= MAX_U32:
        raise RuntimeError("寄存器返回值超出 32 位范围")
    return number


class FPGAConnection:
    def __init__(self, host, user, password, port=22):
        if paramiko is None:
            raise RuntimeError("缺少 paramiko，请运行：py -m pip install paramiko")
        self.ssh = paramiko.SSHClient()
        try:
            self.ssh.load_system_host_keys()
            # Preserve the existing GUI's first-connection policy; known key
            # mismatches still fail. Do not claim this authenticates a new host.
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(host, port=port, username=user, password=password or None,
                             timeout=SSH_TIMEOUT, auth_timeout=SSH_TIMEOUT,
                             banner_timeout=SSH_TIMEOUT, look_for_keys=not bool(password),
                             allow_agent=not bool(password))
            _, out, err = self.ssh.exec_command(
                "if command -v devmem >/dev/null 2>&1; then echo devmem; "
                "elif busybox --list 2>/dev/null | grep -qx devmem; then echo 'busybox devmem'; "
                "else echo NO_DEVMEM; fi", timeout=SSH_TIMEOUT)
            tool = out.read().decode(errors="replace").strip()
            diagnostic = err.read().decode(errors="replace").strip()
            status = out.channel.recv_exit_status()
            if status != 0 or diagnostic or tool not in ("devmem", "busybox devmem"):
                raise RuntimeError("远端没有可用的 devmem，或检测命令失败：" + diagnostic)
            self.tool = tool
        except Exception:
            try:
                self.ssh.close()
            except Exception:
                pass
            raise

    def close(self):
        self.ssh.close()

    def _command(self, addr, value=None):
        if type(addr) is not int or addr not in REGISTERS:
            raise ValueError("不支持的 EOM 寄存器地址")
        cmd = f"{self.tool} 0x{addr:08X} 32"
        if value is not None:
            cmd += f" 0x{value:08X}"
        _, stdout, stderr = self.ssh.exec_command(cmd, timeout=SSH_TIMEOUT)
        try:
            out = stdout.read().decode(errors="replace").strip()
            err = stderr.read().decode(errors="replace").strip()
            rc = stdout.channel.recv_exit_status()
            if rc != 0 or err:
                raise RuntimeError(f"寄存器访问失败：{cmd}\n{err or out}")
            return parse_register(out) if value is None else out
        finally:
            # Closing a timed-out channel does not prove a remote write stopped.
            try:
                stdout.channel.close()
            except Exception:
                pass

    def write(self, addr, value):
        if addr in (REG_DIO0, REG_DELAY):
            validate_cycles(value)
        elif addr == REG_CTRL:
            if type(value) is not int or value not in (1, 2):
                raise ValueError("CTRL 只允许单独写 Start=1 或 Clear=2")
        else:
            raise ValueError("此程序不写入该寄存器")
        return self._command(addr, value)

    def read(self, addr):
        return self._command(addr)


class ClearRequested(Exception):
    pass


class EOMController:
    """Serial operations on one connection; never retries a Start automatically."""
    def __init__(self, conn, emit, clear_requested=None, clock=time.monotonic,
                 sleep=time.sleep):
        self.conn = conn
        self.emit = emit
        self.clear_requested = clear_requested or threading.Event()
        self.clock = clock
        self.sleep = sleep

    def checkpoint(self):
        if self.clear_requested.is_set():
            raise ClearRequested()

    def status(self):
        value = self.conn.read(REG_CTRL)
        if type(value) is not int or value not in (0, 1, 2):
            raise RuntimeError(f"状态寄存器异常：{value!r}；请核对固件和连接")
        return value

    def clear(self):
        self.conn.write(REG_CTRL, 2)
        status = self.status()
        if status != 0:
            raise RuntimeError(f"Clear 后状态未归零（0x{status:08X}）；停止后续操作")
        self.emit("Clear 状态已读回：BUSY=0，DONE=0。预期 DIO0 LOW、DIO1 HIGH；参数保留。")

    def trigger(self, width, delay):
        validate_cycles(width)
        validate_cycles(delay)
        self.checkpoint()
        status = self.status()
        if status == 1:
            raise RuntimeError("FPGA 正在执行；未发送 Start。需要中断时请按 Clear。")
        if status == 2:
            raise RuntimeError("DIO1 处于 LOW 保持；请先按 Clear，再触发。未发送 Start。")
        self.checkpoint()
        self.conn.write(REG_DIO0, width)
        self.checkpoint()
        self.conn.write(REG_DELAY, delay)
        self.checkpoint()
        got_width = self.conn.read(REG_DIO0)
        self.checkpoint()
        got_delay = self.conn.read(REG_DELAY)
        if got_width != width or got_delay != delay:
            raise RuntimeError(f"参数读回不一致：宽度={got_width}，延迟={got_delay}；未发送 Start")
        self.checkpoint()
        if self.status() != 0:
            raise RuntimeError("写参数期间 FPGA 状态变化；未发送 Start，请检查其他控制程序")
        self.checkpoint()
        self.conn.write(REG_CTRL, 1)  # Exactly once. No automatic resend on failure.
        self.emit(f"Start 已发送：宽度 {width} 周期，延迟 {delay} 周期（8 ns/周期）；等待状态读回。")
        deadline = self.clock() + (width + delay + 3) / CLK_HZ + COMPLETION_MARGIN
        saw_busy = False
        while True:
            self.checkpoint()
            status = self.status()
            self.checkpoint()
            if status == 2:
                self.emit("DONE=1 已读回。预期 DIO1 保持 LOW；重新触发前请先 Clear。")
                return
            if status == 1 and not saw_busy:
                self.emit("BUSY=1 已读回。")
                saw_busy = True
            if status == 0 and saw_busy:
                raise RuntimeError("运行期间状态意外回到 IDLE；可能有 Reset/Clear 或其他控制程序介入")
            if self.clock() >= deadline:
                raise RuntimeError("等待完成超时，结果不确定；不会自动重发 Start，请读状态或 Clear")
            self.sleep(POLL_INTERVAL)


class TriggerGUI:
    def __init__(self, root):
        self.root = root
        root.title("Red Pitaya EOM 触发器 · 现有固件 · 125 MHz")
        self.events = queue.Queue()
        self.running = False
        self.active_action = None
        self.clear_requested = threading.Event()
        self.host = tk.StringVar(value="169.254.85.194")
        self.port = tk.StringVar(value="22")
        self.user = tk.StringVar(value="root")
        self.password = tk.StringVar(value="")
        self.dio0 = tk.StringVar(value="1.0")
        self.delay = tk.StringVar(value="10.0")
        self.loaded = tk.BooleanVar(value=False)
        frame = ttk.Frame(root, padding=14)
        frame.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        fields = [("Red Pitaya IP", self.host), ("SSH 端口", self.port),
                  ("SSH 用户名", self.user), ("DIO0 HIGH 时长（ms）", self.dio0),
                  ("DIO0 下降沿后的延迟（ms）", self.delay)]
        for i, (label, var) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(frame, textvariable=var, width=32).grid(row=i, column=1, sticky="ew", padx=(12, 0))
        ttk.Label(frame, text="SSH 密码（留空使用本机密钥/agent）").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.password, show="*", width=32).grid(row=5, column=1, sticky="ew", padx=(12, 0))
        ttk.Label(frame, text="DIO1 默认 HIGH，延迟后保持 LOW。Clear 会中断当前序列并恢复 HIGH。",
                  wraplength=620, foreground="#155B9A").grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 4))
        ttk.Label(frame, text="完成后必须先 Clear 再触发。状态来自寄存器，不能确认实际引脚电平。",
                  wraplength=620).grid(row=7, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(frame, variable=self.loaded, text="已加载自定义 EOM 固件（本程序不更新固件）"
                        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(10, 8))
        bar = ttk.Frame(frame)
        bar.grid(row=9, column=0, columnspan=2, sticky="ew")
        self.start_button = ttk.Button(bar, text="触发", command=lambda: self.start_task("trigger"))
        self.clear_button = ttk.Button(bar, text="Clear / 中断并恢复输出", command=lambda: self.start_task("clear"))
        self.status_button = ttk.Button(bar, text="读取状态", command=lambda: self.start_task("status"))
        for b in (self.start_button, self.clear_button, self.status_button):
            b.pack(side="left", padx=(0, 8))
        self.log = tk.Text(frame, height=15, width=90, state="disabled")
        self.log.grid(row=10, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        frame.rowconfigure(10, weight=1)
        self.log_message("使用 SSH/devmem 控制 FPGA；请保持只有一个控制程序访问该设备。")
        self.log_message("保留现有固件；GUI 不能修复其 AXI 问题，也不能验证固件身份。")
        self.log_message("Clear 按顺序执行，需等待当前 SSH 操作返回；不能用作硬实时急停。")
        root.after(100, self.flush_events)

    def log_message(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def update_buttons(self):
        self.start_button.configure(state="disabled" if self.running else "normal")
        self.status_button.configure(state="disabled" if self.running else "normal")
        clear_enabled = not self.running or (self.active_action == "trigger" and not self.clear_requested.is_set())
        self.clear_button.configure(state="normal" if clear_enabled else "disabled")

    def start_task(self, action):
        if action not in ("trigger", "clear", "status"):
            return
        if self.running:
            if action == "clear" and self.active_action == "trigger":
                self.clear_requested.set()
                self.log_message("已请求 Clear，等待当前 SSH 操作返回后按顺序处理。")
                self.update_buttons()
            return
        if not self.loaded.get():
            messagebox.showwarning("尚未确认固件", "请先加载自定义 EOM 固件，再访问寄存器。")
            return
        try:
            settings = dict(host=self.host.get().strip(), user=self.user.get().strip(),
                            password=self.password.get(), port=int(self.port.get()))
            if not settings["host"] or not settings["user"] or not 1 <= settings["port"] <= 65535:
                raise ValueError("IP、用户名或 SSH 端口无效")
            if action == "trigger":
                settings["dio0_cycles"] = ms_to_cycles(float(self.dio0.get()))
                settings["delay_cycles"] = ms_to_cycles(float(self.delay.get()))
                self.log_message(f"量化后：HIGH={settings['dio0_cycles'] * 8} ns，延迟={settings['delay_cycles'] * 8} ns。")
        except (ValueError, OverflowError) as exc:
            messagebox.showerror("参数无效", str(exc))
            return
        self.launch_task(action, settings)

    def launch_task(self, action, settings):
        self.running = True
        self.active_action = action
        self.active_settings = dict(settings)
        self.clear_requested.clear()
        self.update_buttons()
        try:
            threading.Thread(target=self.work, args=(action, settings), daemon=True).start()
        except Exception as exc:
            self.running = False
            self.active_action = None
            self.update_buttons()
            self.log_message("无法启动任务：" + str(exc))

    def work(self, action, settings):
        conn = None
        try:
            conn = FPGAConnection(settings["host"], settings["user"], settings["password"], settings["port"])
            self.events.put(f"已连接 {settings['host']}（{conn.tool}）")
            controller = EOMController(conn, self.events.put, self.clear_requested)
            if action == "trigger":
                try:
                    controller.trigger(settings["dio0_cycles"], settings["delay_cycles"])
                except ClearRequested:
                    self.clear_requested.clear()  # Consume this explicit request once.
                    controller.clear()
            elif action == "clear":
                controller.clear()
            else:
                status = controller.status()
                self.events.put(f"状态 0x{status:08X}：BUSY={status & 1}，DONE={(status >> 1) & 1}")
                self.events.put(f"宽度={conn.read(REG_DIO0)} 周期；延迟={conn.read(REG_DELAY)} 周期。")
        except Exception as exc:
            self.events.put("操作未确认完成：" + str(exc))
            self.events.put("未自动重试。发生通信错误时，远端操作可能已经执行；请读状态或 Clear。")
        finally:
            try:
                if conn is not None:
                    conn.close()
            except Exception as exc:
                self.events.put("关闭连接异常：" + str(exc))
            finally:
                # Keep UI state in the main Tk thread, even if close() fails.
                self.events.put("__IDLE__")

    def flush_events(self):
        try:
            while True:
                message = self.events.get_nowait()
                if message == "__IDLE__":
                    settings = dict(self.active_settings)
                    self.running = False
                    self.active_action = None
                    # A Clear click can race the worker's completion. Retain the
                    # queued request and run it serially after this worker closes.
                    pending_clear = self.clear_requested.is_set()
                    self.clear_requested.clear()
                    self.update_buttons()
                    if pending_clear:
                        self.launch_task("clear", settings)
                        return
                else:
                    self.log_message(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.flush_events)


if __name__ == "__main__":
    main_root = tk.Tk()
    TriggerGUI(main_root)
    main_root.mainloop()
