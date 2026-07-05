import time
import tkinter as tk
from tkinter import messagebox
import redpitaya_scpi as scpi


def send_trigger():
    ip = ip_entry.get()

    try:
        dio0_ms = float(dio0_entry.get())
        delay_ms = float(delay_entry.get())
        dio1_ms = float(dio1_entry.get())
    except:
        messagebox.showerror("Error", "Please enter valid numbers.")
        return

    rp_s = scpi.scpi(ip)

    dio0 = "DIO0_P"
    dio1 = "DIO1_P"

    print("Connecting to Red Pitaya at " + ip)
    print("Using " + dio0 + " for PDUS trigger")
    print("Using " + dio1 + " for HV trigger")

    # set DIO pins as output
    rp_s.tx_txt("DIG:PIN:DIR OUT," + dio0)
    rp_s.tx_txt("DIG:PIN:DIR OUT," + dio1)

    # clear both pins first
    rp_s.tx_txt("DIG:PIN " + dio0 + "," + str(0))
    rp_s.tx_txt("DIG:PIN " + dio1 + "," + str(0))

    print("DIO0_P HIGH")
    rp_s.tx_txt("DIG:PIN " + dio0 + "," + str(1))
    time.sleep(dio0_ms / 1000.0)

    print("DIO0_P LOW")
    rp_s.tx_txt("DIG:PIN " + dio0 + "," + str(0))

    print("Delay " + str(delay_ms) + " ms")
    time.sleep(delay_ms / 1000.0)

    print("DIO1_P HIGH")
    rp_s.tx_txt("DIG:PIN " + dio1 + "," + str(1))
    time.sleep(dio1_ms / 1000.0)

    print("DIO1_P LOW")
    rp_s.tx_txt("DIG:PIN " + dio1 + "," + str(0))

    print("Done")

    log_box.insert(tk.END, "Sent trigger sequence\n")
    log_box.insert(tk.END, "DIO0_P pulse: " + str(dio0_ms) + " ms\n")
    log_box.insert(tk.END, "Delay: " + str(delay_ms) + " ms\n")
    log_box.insert(tk.END, "DIO1_P pulse: " + str(dio1_ms) + " ms\n\n")
    log_box.see(tk.END)


root = tk.Tk()
root.title("Red Pitaya DIO Trigger")

tk.Label(root, text="Red Pitaya IP").grid(row=0, column=0)
ip_entry = tk.Entry(root)
ip_entry.insert(0, "169.254.85.194")
ip_entry.grid(row=0, column=1)

tk.Label(root, text="DIO0_P pulse width ms").grid(row=1, column=0)
dio0_entry = tk.Entry(root)
dio0_entry.insert(0, "1.0")
dio0_entry.grid(row=1, column=1)

tk.Label(root, text="Delay between DIO0_P and DIO1_P ms").grid(row=2, column=0)
delay_entry = tk.Entry(root)
delay_entry.insert(0, "10.0")
delay_entry.grid(row=2, column=1)

tk.Label(root, text="DIO1_P pulse width ms").grid(row=3, column=0)
dio1_entry = tk.Entry(root)
dio1_entry.insert(0, "1.0")
dio1_entry.grid(row=3, column=1)

button = tk.Button(root, text="Send Trigger", command=send_trigger)
button.grid(row=4, column=0, columnspan=2, pady=10)

log_box = tk.Text(root, width=55, height=10)
log_box.grid(row=5, column=0, columnspan=2)

root.mainloop()