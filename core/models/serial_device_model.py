import re
import sys
import time
import serial
import serial.tools.list_ports
from collections import deque
from typing import Optional, List, Union
from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer, QEventLoop


class SerialListener(QThread):
    received = Signal(str)
    error = Signal(str)

    CONTROL_CHARS = re.compile(
        r'[\x00-\x08\x0B\x0C\x0E\x0F\x10-\x1F\x7F]'
    )

    ANSI_ESCAPE = re.compile(
        r'\x1b\[[0-?]*[ -/]*[@-~]'
    )

    def __init__(self, device: serial.Serial, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.device = device
        self.running = True

    def run(self):
        try:
            while self.running and self.device and self.device.is_open:
                if self.device.in_waiting:
                    raw = self.device.readline()
                    try:
                        data = raw.decode('utf-8', errors='ignore').strip()
                    except:
                        continue

                    if data:
                        # Remove ANSI CSI sequences
                        data = re.sub(self.ANSI_ESCAPE, '', data)

                        # Remove C0 control characters (except tab, newline, carriage return)
                        data = re.sub(self.CONTROL_CHARS, '', data)

                        # Remove NULL (if any)
                        data = data.replace('\x00', '')

                        if data:
                            self.received.emit(data)

                self.msleep(15)

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.running = False
        self.quit()
        self.wait(500)


class SerialDeviceModel(QObject):
    connection_result = Signal(bool, str)
    disconnection_result = Signal(bool, str)
    data_received = Signal(str)

    queue_finished = Signal()
    # Single command completion: command, response_lines
    command_finished = Signal(str, list)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.device: Optional[serial.Serial] = None
        self.listener: Optional[SerialListener] = None

        # Queue control
        self.command_queue = deque()   # Each item: {cmd, wait_for, timeout}
        self.is_processing = False
        self.current_wait_token = None  # str or re.Pattern

        # Outer timeout: maximum alive time for the entire command
        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_command_timeout)
        self.current_timeout_sec = 3.0

        # Inner settle timer: output stability detection
        self.settle_timer = QTimer(self)
        self.settle_timer.setSingleShot(True)
        self.settle_timer.timeout.connect(self._on_settle_timeout)
        self.settle_delay_ms = 80  # Basic delay, can be dynamically adjusted

        # Prompt detection and state
        self.prompt_regex = re.compile(r"^[\w@:\-\.]+[:~][\w/]*[>#\$] ?")
        self.has_matched_token = False
        self.line_times: List[float] = []

        # Current command state
        self.current_cmd: Optional[str] = None
        self.current_response_lines: List[str] = []

    # ============================
    # Utilities
    # ============================
    @staticmethod
    def get_available_ports() -> List[serial.tools.list_ports_common.ListPortInfo]:
        return serial.tools.list_ports.comports()

    def is_connected(self) -> bool:
        return self.device is not None and self.device.is_open

    # ============================
    # Connection management
    # ============================
    def connect_device(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> bool:
        if self.is_connected():
            self.disconnect_device()
            time.sleep(0.1)

        try:
            self.device = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)

            self.listener = SerialListener(self.device, self)
            self.listener.received.connect(self._handle_incoming_data)
            self.listener.error.connect(self.on_error)
            self.listener.start()

            self.connection_result.emit(True, f"Connected to {port}")
            return True

        except serial.SerialException as e:
            self.connection_result.emit(False, f"Failed to connect to {port}: {e}")
            self.device = None
            return False

    def disconnect_device(self) -> bool:
        # Clear all states
        self.command_queue.clear()
        self.is_processing = False

        self.timeout_timer.stop()
        self.settle_timer.stop()

        self.current_cmd = None
        self.current_wait_token = None
        self.current_response_lines = []
        self.has_matched_token = False
        self.line_times.clear()

        if not self.is_connected():
            return True
        try:
            if self.listener:
                self.listener.stop()
                self.listener = None
            if self.device:
                port = self.device.port
                self.device.close()
                self.device = None
                self.disconnection_result.emit(True, f"Disconnected from {port}")
            return True
        except Exception as e:
            self.disconnection_result.emit(False, f"Error disconnecting: {e}")
            return False

    # ==========================================
    #  Command queue & execution
    # ==========================================
    def send_command_queued(self, command: str, wait_for: Union[str, re.Pattern] = "#", timeout: float = 3.0):
        """
        Add a command to the queue.
        :param command: The command to send (e.g. "fdisk -l /dev/mmcblk0")
        :param wait_for:
            Determine the token to judge whether the command has entered the tail state, support:
              - str: direct string comparison (in data)
              - re.Pattern: regular expression comparison (search)
            When the wait_for is first matched, the settle_timer is started,
            and the command is finally ended when there is no new data for a period of time.
        :param timeout: The maximum execution time of the entire command (outer timeout)
        """
        self.command_queue.append({
            "cmd": command,
            "wait_for": wait_for,
            "timeout": timeout,
        })
        self._process_next_command()

    def _process_next_command(self):
        """Check state and send the next command"""
        if not self.is_connected():
            self.command_queue.clear()
            self.is_processing = False
            return

        if self.is_processing:
            return

        if not self.command_queue:
            self.queue_finished.emit()
            return

        # Ensure the settle state of the previous command is cleared
        self.settle_timer.stop()
        self.has_matched_token = False
        self.line_times.clear()

        item = self.command_queue.popleft()
        cmd = item["cmd"]
        wait_for = item["wait_for"]
        timeout = item["timeout"]

        # normalize wait token
        if isinstance(wait_for, str):
            wait_token = wait_for
        elif isinstance(wait_for, re.Pattern):
            wait_token = wait_for
        else:
            raise TypeError("wait_for must be str or re.Pattern")

        self.current_wait_token = wait_token
        self.current_cmd = cmd
        self.current_response_lines = []
        self.is_processing = True

        # Outer timeout
        self.timeout_timer.start(int(timeout * 1000))

        # Pre-flush：Clear any residual data to avoid background noise from the previous command
        try:
            if self.device and self.device.in_waiting:
                _ = self.device.read(self.device.in_waiting)
        except Exception:
            # If flush fails, don't let the entire process hang
            pass

        # Send the command
        self._raw_send(cmd)

    def _raw_send(self, data: Union[str, bytes]):
        """Low-level send logic"""
        try:
            if isinstance(data, str):
                payload = (data + "\r\n").encode("utf-8")
            elif isinstance(data, bytes):
                payload = data
            else:
                raise TypeError("data must be str or bytes")
            self.device.write(payload)
        except serial.SerialException as e:
            self.data_received.emit(f"Failed to send data: {e}")
            self.disconnect_device()

    # ==========================================
    #  Incoming data handling + advanced settle
    # ==========================================
    def _handle_incoming_data(self, data: str):
        """
        Handle incoming data.
        1. Send the data to UI via data_received.
        2. If there is a command being processed, accumulate it to current_response_lines.
        3. Determine when the command is truly completed using wait_for + settle_timer.
        """
        # Notify UI to display the original data
        self.data_received.emit(data)

        if not self.is_processing:
            return

        # -----------------------------
        # Echo filtering: Exclude "prompt + command" line
        # Example: "root@box:~# fdisk -l /dev/mmcblk0"
        # -----------------------------
        if self.prompt_regex.match(data) and self.current_cmd != "root":
            if isinstance(self.current_cmd, str) and self.current_cmd and self.current_cmd in data:
                return

        # Accumulate this line of output
        self.current_response_lines.append(data)

        # Record time to determine burst output
        now = time.time()
        self.line_times.append(now)
        if len(self.line_times) > 16:
            self.line_times.pop(0)

        # If already in the 'tail stage' (i.e. matched the token once),
        # restart the settle_timer every time new data arrives
        if self.has_matched_token:
            self._restart_settle_timer()
            return

        # If not yet matched wait_for → try to match
        token = self.current_wait_token
        if not token:
            return

        if isinstance(token, str):
            matched = token in data
        elif isinstance(token, re.Pattern):
            matched = bool(token.search(data))
        else:
            matched = False

        if matched:
            # First match to wait_for, enter 'tail stage'
            self.has_matched_token = True
            self._restart_settle_timer()

    def _restart_settle_timer(self):
        """
        Smartly restart settle_timer, including simple adaptive adjustment:
        - If recent lines of output are very dense, it's burst output, then extend settle time.
        """
        adaptive_delay = self.settle_delay_ms

        if len(self.line_times) >= 4:
            dt = self.line_times[-1] - self.line_times[-4]
            # Example: 30ms within 4 lines →视为 burst, extend settle time
            if dt < 0.03:
                adaptive_delay = max(adaptive_delay, 150)

        self.settle_timer.start(adaptive_delay)

    def _on_settle_timeout(self):
        """
        When in the 'tail stage' for a period without new data, determine that the output has stabilized,
        declare the command completed.
        """
        if not self.is_processing:
            return

        # If it's a prompt-based wait_for scenario, and the last line doesn't look like a prompt, wait a bit longer
        last_line = self.current_response_lines[-1] if self.current_response_lines else ""

        want_prompt_check = (
            isinstance(self.current_wait_token, str)
            and any(ch in self.current_wait_token for ch in ["#", "$", ">"])
        )

        if want_prompt_check and self.prompt_regex and not self.prompt_regex.match(last_line):
            # Looks like it hasn't returned to the prompt, give it a bit longer
            self.settle_timer.start(self.settle_delay_ms)
            return

        # Arrived here, means output has stabilized, declare command completed
        self.timeout_timer.stop()
        self.is_processing = False

        self.command_finished.emit(self.current_cmd, self.current_response_lines.copy())

        # Reset state
        self.current_cmd = None
        self.current_wait_token = None
        self.current_response_lines = []
        self.has_matched_token = False
        self.line_times.clear()

        QTimer.singleShot(50, self._process_next_command)

    def _on_command_timeout(self):
        """When the entire command wait timeout (outer timeout)"""
        if not self.is_processing:
            return

        # Regardless of whether partial data has been received, return the current buffer

        # Stop related timers, reset state
        self.timeout_timer.stop()
        self.settle_timer.stop()

        self.is_processing = False
        self.current_cmd = None
        self.current_wait_token = None
        self.current_response_lines = []
        self.has_matched_token = False
        self.line_times.clear()

        QTimer.singleShot(50, self._process_next_command)

    def on_error(self, msg):
        self.data_received.emit(msg)
        self.disconnect_device()

    # ==========================================
    #  Synchronous API
    # ==========================================
    def send_command_sync(self, cmd: str,
                          wait_for: Union[str, re.Pattern] = "#",
                          timeout: float = 5.0) -> List[str]:
        """
        Execute command synchronously.
        Returns: Complete response (list of lines)
        """
        if not self.is_connected():
            return ["[ERROR] Device not connected"]

        loop = QEventLoop()
        result_holder = {"response": []}

        # 1. Normal completion handler
        def on_finished(finished_cmd, response_lines):
            if finished_cmd == cmd:
                result_holder["response"] = response_lines
                if loop.isRunning():
                    loop.quit()

        # 2. Disconnection handler
        def on_disconnected(success, msg):
            result_holder["response"] = ["[ERROR] Device disconnected during command execution"]
            if loop.isRunning():
                loop.quit()
        
        # 3. Safety timer (fallback)
        # Set slightly longer than the command timeout to give the command logic a chance to timeout first
        safety_timer = QTimer()
        safety_timer.setSingleShot(True)
        
        def on_safety_timeout():
            if loop.isRunning():
                # If we hit this, it means the model's internal timeout logic failed or hung
                # We should try to stop the command manually
                result_holder["response"] = ["[ERROR] Command execution timed out (Safety Timer)"]
                # Send Ctrl+C to stop the command processing, ensure no residual output
                self._raw_send(b'\x03')
                loop.quit()

        safety_timer.timeout.connect(on_safety_timeout)

        # Connect signals
        self.command_finished.connect(on_finished)
        self.disconnection_result.connect(on_disconnected)

        # Enqueue the command
        self.send_command_queued(cmd, wait_for, timeout)
        
        # Start safety timer (timeout + 0.5s buffer)
        safety_timer.start(int((timeout + 0.5) * 1000))

        # Block until the command is finished (or timeout/disconnect)
        loop.exec()

        # Cleanup
        if safety_timer.isActive():
            safety_timer.stop()
            
        self.command_finished.disconnect(on_finished)
        self.disconnection_result.disconnect(on_disconnected)

        return result_holder["response"]


if __name__ == "__main__":
    from PySide6.QtCore import QCoreApplication

    class TestConsole(QObject):
        def __init__(self):
            super().__init__()
            self.model = SerialDeviceModel()
            
            # Connect signals
            self.model.data_received.connect(self.on_data_received)
            self.model.queue_finished.connect(self.on_all_finished)
            
        def start(self):
            # 1. Connect to the device
            self.model.connect_device("COM8")
            
            print("\n--- Starting Test Sequence ---")
            
            cmds = [
                ("fdisk -l /dev/mmcblk0", "~#"),
                ("uname -a", "Linux"),
                ("cat /etc/os-release", "PRETTY_NAME="),
                ("strings /dev/mtd5 | grep -E 'U-Boot [0-9]{4}\\.'", ")"),
                ("lscpu | grep 'Model name'", "name:"),
                ("free -h | grep 'Mem:'", r"Mem:\s+\S+\s+\S+\s+\S+"),
                ("top -b -n 1 | head -n 5", "Swap:")
            ]
            for cmd, wait_for in cmds:
                response = self.model.send_command_sync(cmd, wait_for, 10)
                print(f"[Command] {cmd}")
                for res in response:
                    print(f"[R] {res}")
            

        @Slot(str)
        def on_data_received(self, data):
            # Here displays all original data received from the device
            # print(f"[Device] >> {data}")
            pass

        @Slot()
        def on_all_finished(self):
            print("\n--- All Commands Processed. Exiting... ---")
            self.model.disconnect_device()
            QCoreApplication.quit() # Exit the application
    
    app = QCoreApplication(sys.argv)
    controller = TestConsole()
    QTimer.singleShot(0, controller.start)
    sys.exit(app.exec())