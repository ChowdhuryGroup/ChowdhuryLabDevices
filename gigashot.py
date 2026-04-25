from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.parse import urlparse
import socket
import json
import time
class gigashot:
    def __init__(self, ip_addr: str = "192.168.1.1", timeout: float = 2.5):
        self.ip = ip_addr
        self.base_url = f"http://{ip_addr}/api"
        self.timeout = timeout

    def send_command(self, command_id: str, value=None, expect_repsonse=False):
        params = {"id": command_id}
        if value is not None:
            params["value"] = value

        url = f"{self.base_url}?{urlencode(params)}"

        if not expect_repsonse:
            # Fire-and-forget: send the HTTP request and do not wait for a reply.

            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or 80
            path = parsed.path + ("?" + parsed.query if parsed.query else "")

            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            ).encode("utf-8")

            try:
                with socket.create_connection((host, port), timeout=self.timeout) as sock:
                    sock.sendall(request)
                    #close the socket immediately without waiting for a response
                    time.sleep(0.25)  # Give the server a moment to process the request
                    sock.shutdown(socket.SHUT_RDWR)
                return True
            except OSError:
                return False

        req = Request(url, method="GET")
        for attempt in range(2):
            try:
                with urlopen(req, timeout=self.timeout) as response:
                    time.sleep(0.25)  # Give the server a moment to process the request
                    return response.read().decode("utf-8", errors="replace")
            except (socket.timeout, TimeoutError):
                if attempt == 1:
                    raise RuntimeError("Failed to get response after 2 attempts")
                continue

    def start(self):

        self.send_command("start")
        time.sleep(5) #laser always needs time to warm up
    
    def stop(self):
        return self.send_command("stop")

    def close_shutter(self):
        return self.send_command("close_shutter")
    def open_shutter(self):
        return self.send_command("open_shutter")

    def set_osc_driver_current(self, value: int):
        return self.send_command("osc_driver_current", value=value)
    
    def set_repetition_rate(self, value: int):
        #in Hz
        #stop laser
        self.stop()
        #set repetition rate
        self.send_command("pulser1_frequency", value=value)
    
    def get_state(self, retries: int = 5, retry_delay: float = 0.2):
        for attempt in range(retries):
            try:
                response = self.send_command("state", expect_repsonse=True)
            except RuntimeError:
                print(f"Attempt {attempt + 1}: request timed out")
                if attempt < retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise

            try:
                data = json.loads(response)
            except json.JSONDecodeError:
                data = {}

            state = data.get("data")

            print(f"Attempt {attempt + 1}: State = {state!r}")

            if isinstance(state, str) and " " not in state:
                return state

            if attempt < retries - 1:
                time.sleep(retry_delay)

        raise RuntimeError("State was not valid after retries")
if __name__ == "__main__":
    laser = gigashot("192.168.1.1")
    while True:
        cmd = input("Enter command (start, stop, open_shutter, close_shutter, set_repetition_rate <value>, set_osc_driver_current <value>, exit): ")
        if cmd == "exit":
            break
        elif cmd == "start":
            print(laser.start())
        elif cmd == "stop":
            print(laser.stop())
        elif cmd == "open_shutter":
            print(laser.open_shutter())
        elif cmd == "close_shutter":
            print(laser.close_shutter())
        elif cmd.startswith("set_repetition_rate"):
            try:
                value = int(cmd.split()[1])
                laser.set_repetition_rate(value)
                print(f"Repetition rate set to {value} Hz")
            except (IndexError, ValueError):
                print("Invalid command format. Use: set_repetition_rate <value>")
        elif cmd.startswith("set_osc_driver_current"):
            try:
                value = int(cmd.split()[1])
                print(laser.set_osc_driver_current(value))
            except (IndexError, ValueError):
                print("Invalid command format. Use: set_osc_driver_current <value>")
        elif cmd == "get_state":
            print(laser.get_state())
        else:
            print("Unknown command.")