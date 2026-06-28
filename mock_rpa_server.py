import socket
import time
from datetime import datetime

HOST = "127.0.0.1"
PORT = 9000


def now():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def run_sequence(delay_ms: float, pdus_width_ms: float, hv_width_ms: float):
    print(f"[{now()}] PDUS_TRIGGER HIGH")
    time.sleep(pdus_width_ms / 1000.0)

    print(f"[{now()}] PDUS_TRIGGER LOW")

    print(f"[{now()}] WAIT {delay_ms:.3f} ms")
    time.sleep(delay_ms / 1000.0)

    print(f"[{now()}] HV_TRIGGER HIGH")
    time.sleep(hv_width_ms / 1000.0)

    print(f"[{now()}] HV_TRIGGER LOW")
    print(f"[{now()}] SEQUENCE DONE")


def handle_command(command: str) -> str:
    """
    Command format:
    TRIG delay_ms pdus_width_ms hv_width_ms

    Example:
    TRIG 10.0 1.0 1.0
    """

    parts = command.strip().split()

    if len(parts) != 4:
        return "ERROR: Use TRIG delay_ms pdus_width_ms hv_width_ms\n"

    if parts[0].upper() != "TRIG":
        return "ERROR: Command must start with TRIG\n"

    try:
        delay_ms = float(parts[1])
        pdus_width_ms = float(parts[2])
        hv_width_ms = float(parts[3])
    except ValueError:
        return "ERROR: delay and widths must be numbers\n"

    if delay_ms < 0 or pdus_width_ms <= 0 or hv_width_ms <= 0:
        return "ERROR: invalid timing values\n"

    run_sequence(delay_ms, pdus_width_ms, hv_width_ms)

    return "OK\n"


def main():
    print(f"Mock Red Pitaya server listening on {HOST}:{PORT}")
    print("Command format: TRIG delay_ms pdus_width_ms hv_width_ms")
    print("Example: TRIG 10.0 1.0 1.0")
    print()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)

        while True:
            conn, addr = server.accept()

            with conn:
                data = conn.recv(1024).decode().strip()
                print(f"[{now()}] Received from {addr}: {data}")

                response = handle_command(data)
                conn.sendall(response.encode())


if __name__ == "__main__":
    main()