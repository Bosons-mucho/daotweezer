import socket
import tkinter as tk
from tkinter import messagebox


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9000


def send_trigger():
    host = host_entry.get().strip()
    port_text = port_entry.get().strip()
    delay_text = delay_entry.get().strip()
    pdus_width_text = pdus_width_entry.get().strip()
    hv_width_text = hv_width_entry.get().strip()

    try:
        port = int(port_text)
        delay_ms = float(delay_text)
        pdus_width_ms = float(pdus_width_text)
        hv_width_ms = float(hv_width_text)
    except ValueError:
        messagebox.showerror("Input Error", "Port and timing values must be valid numbers.")
        return

    command = f"TRIG {delay_ms} {pdus_width_ms} {hv_width_ms}\n"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3.0)
            s.connect((host, port))
            s.sendall(command.encode())
            response = s.recv(1024).decode().strip()

        log_text.insert(tk.END, f"> {command}")
        log_text.insert(tk.END, f"< {response}\n")
        log_text.see(tk.END)

    except Exception as e:
        messagebox.showerror("Connection Error", str(e))


root = tk.Tk()
root.title("Red Pitaya PDUS-HV Trigger GUI")

frame = tk.Frame(root, padx=12, pady=12)
frame.pack()

tk.Label(frame, text="Server IP / Host").grid(row=0, column=0, sticky="w")
host_entry = tk.Entry(frame, width=20)
host_entry.insert(0, DEFAULT_HOST)
host_entry.grid(row=0, column=1)

tk.Label(frame, text="Port").grid(row=1, column=0, sticky="w")
port_entry = tk.Entry(frame, width=20)
port_entry.insert(0, str(DEFAULT_PORT))
port_entry.grid(row=1, column=1)

tk.Label(frame, text="Delay to HV trigger (ms)").grid(row=2, column=0, sticky="w")
delay_entry = tk.Entry(frame, width=20)
delay_entry.insert(0, "10.0")
delay_entry.grid(row=2, column=1)

tk.Label(frame, text="PDUS trigger width (ms)").grid(row=3, column=0, sticky="w")
pdus_width_entry = tk.Entry(frame, width=20)
pdus_width_entry.insert(0, "1.0")
pdus_width_entry.grid(row=3, column=1)

tk.Label(frame, text="HV trigger width (ms)").grid(row=4, column=0, sticky="w")
hv_width_entry = tk.Entry(frame, width=20)
hv_width_entry.insert(0, "1.0")
hv_width_entry.grid(row=4, column=1)

trigger_button = tk.Button(frame, text="Send Trigger", command=send_trigger, width=20)
trigger_button.grid(row=5, column=0, columnspan=2, pady=10)

log_text = tk.Text(frame, width=55, height=10)
log_text.grid(row=6, column=0, columnspan=2)

root.mainloop()