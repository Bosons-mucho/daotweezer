import socket
from datetime import datetime

HOST = "127.0.0.1"
PORT = 5000

VALID_PINS = {
    "DIO0_P", "DIO1_P", "DIO2_P", "DIO3_P",
    "DIO4_P", "DIO5_P", "DIO6_P", "DIO7_P",
    "DIO0_N", "DIO1_N", "DIO2_N", "DIO3_N",
    "DIO4_N", "DIO5_N", "DIO6_N", "DIO7_N",
    "LED0", "LED1", "LED2", "LED3", "LED4", "LED5", "LED6", "LED7"
}

pin_direction = {pin: "IN" for pin in VALID_PINS}
pin_state = {pin: 0 for pin in VALID_PINS}


def now():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def normalize_command(cmd: str) -> str:
    return cmd.strip().replace("\r", "").replace("\n", "")


def parse_pin_state_value(value: str) -> int:
    value = value.strip().upper()

    if value in ["1", "ON", "HIGH", "TRUE"]:
        return 1

    if value in ["0", "OFF", "LOW", "FALSE"]:
        return 0

    raise ValueError(f"Invalid pin state: {value}")


def handle_scpi_command(cmd: str) -> str | None:
    """
    Supported mock commands:

    *IDN?
    SYST:ERR?
    DIG:PIN:DIR OUT,DIO0_P
    DIG:PIN DIO0_P,1
    DIG:PIN? DIO0_P

    Return:
    - string response for query commands
    - None for normal set commands
    """

    cmd = normalize_command(cmd)

    if not cmd:
        return None

    print(f"[{now()}] RX: {cmd}")

    upper = cmd.upper()

    # Identification query
    if upper == "*IDN?":
        return "MOCK,RED_PITAYA_SCPI_SERVER,LOCAL,0.1"

    # Error query
    if upper == "SYST:ERR?":
        return '0,"No error"'

    # Direction set:
    # DIG:PIN:DIR OUT,DIO0_P
    if upper.startswith("DIG:PIN:DIR "):
        payload = cmd[len("DIG:PIN:DIR "):].strip()

        if "," not in payload:
            return 'ERROR,"Expected DIG:PIN:DIR <IN|OUT>,<PIN>"'

        direction, pin = payload.split(",", 1)
        direction = direction.strip().upper()
        pin = pin.strip().upper()

        if direction not in ["IN", "OUT"]:
            return f'ERROR,"Invalid direction {direction}"'

        if pin not in VALID_PINS:
            return f'ERROR,"Invalid pin {pin}"'

        pin_direction[pin] = direction
        print(f"[{now()}] SET DIR: {pin} = {direction}")
        return None

    # Pin state query:
    # DIG:PIN? DIO0_P
    if upper.startswith("DIG:PIN? "):
        pin = cmd[len("DIG:PIN? "):].strip().upper()

        if pin not in VALID_PINS:
            return f'ERROR,"Invalid pin {pin}"'

        value = pin_state[pin]
        print(f"[{now()}] QUERY PIN: {pin} = {value}")
        return str(value)

    # Pin state set:
    # DIG:PIN DIO0_P,1
    if upper.startswith("DIG:PIN "):
        payload = cmd[len("DIG:PIN "):].strip()

        if "," not in payload:
            return 'ERROR,"Expected DIG:PIN <PIN>,<0|1>"'

        pin, value = payload.split(",", 1)
        pin = pin.strip().upper()

        if pin not in VALID_PINS:
            return f'ERROR,"Invalid pin {pin}"'

        if pin_direction[pin] != "OUT":
            return f'ERROR,"Pin {pin} is not configured as OUT"'

        try:
            state = parse_pin_state_value(value)
        except ValueError as e:
            return f'ERROR,"{e}"'

        old_state = pin_state[pin]
        pin_state[pin] = state

        edge = ""
        if old_state == 0 and state == 1:
            edge = " RISING_EDGE"
        elif old_state == 1 and state == 0:
            edge = " FALLING_EDGE"

        print(f"[{now()}] SET PIN: {pin} = {state}{edge}")

        # 这里专门把你项目里的两个 pin 打印成语义化事件
        if pin == "DIO0_P":
            print(f"[{now()}]   -> MOCK PDUS_TRIGGER = {state}")

        if pin == "DIO1_P":
            print(f"[{now()}]   -> MOCK HV_TRIGGER = {state}")

        return None

    return f'ERROR,"Unsupported command: {cmd}"'


def handle_client(conn: socket.socket, addr):
    print(f"[{now()}] Client connected: {addr}")

    buffer = ""

    with conn:
        while True:
            data = conn.recv(1024)

            if not data:
                break

            buffer += data.decode(errors="replace")

            # SCPI commands are normally newline terminated
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                cmd = line.strip()

                response = handle_scpi_command(cmd)

                # Red Pitaya SCPI set commands often do not need a response.
                # Query commands return response.
                if response is not None:
                    conn.sendall((response + "\n").encode())

    print(f"[{now()}] Client disconnected: {addr}")


def main():
    print("Mock Red Pitaya SCPI server")
    print(f"Listening on {HOST}:{PORT}")
    print()
    print("Supported examples:")
    print("  *IDN?")
    print("  SYST:ERR?")
    print("  DIG:PIN:DIR OUT,DIO0_P")
    print("  DIG:PIN DIO0_P,1")
    print("  DIG:PIN DIO0_P,0")
    print("  DIG:PIN? DIO0_P")
    print()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(5)

        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)


if __name__ == "__main__":
    main()