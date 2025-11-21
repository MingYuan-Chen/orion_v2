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
                        # 移除 ANSI CSI sequences
                        data = re.sub(self.ANSI_ESCAPE, '', data)

                        # 移除 C0 控制字符（除了 tab、newline、carriage return）
                        data = re.sub(self.CONTROL_CHARS, '', data)

                        # 移除 NULL（如果有殘留）
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
    # 單一指令完成：command, response_lines
    command_finished = Signal(str, list)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.device: Optional[serial.Serial] = None
        self.listener: Optional[SerialListener] = None

        # 佇列控制
        self.command_queue = deque()   # 每個 item: {cmd, wait_for, timeout}
        self.is_processing = False
        self.current_wait_token = None  # str or re.Pattern

        # 外層 timeout：整個指令最大存活時間
        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_command_timeout)
        self.current_timeout_sec = 3.0

        # 內層 settle timer：輸出穩定偵測
        self.settle_timer = QTimer(self)
        self.settle_timer.setSingleShot(True)
        self.settle_timer.timeout.connect(self._on_settle_timeout)
        self.settle_delay_ms = 80  # 基本延遲，可動態調整

        # Prompt 偵測與狀態
        self.prompt_regex = re.compile(r"^[\w@:\-\.]+[:~][\w/]*[>#\$] ?")
        self.has_matched_token = False
        self.line_times: List[float] = []

        # 當前指令狀態
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
        # 清所有狀態
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
        將指令加入佇列。
        :param command: 要發送的指令 (例如 "fdisk -l /dev/mmcblk0")
        :param wait_for:
            判斷指令是否進入收尾狀態的 token，支援：
              - str: 直接字串比對 (in data)
              - re.Pattern: 正規表示式比對 (search)
            當首次 match 到 wait_for 時，啟動 settle_timer，
            並在「一段時間內沒有新資料」後才真正結束該指令。
        :param timeout: 整個指令的最大執行秒數 (外層 timeout)
        """
        self.command_queue.append({
            "cmd": command,
            "wait_for": wait_for,
            "timeout": timeout,
        })
        self._process_next_command()

    def _process_next_command(self):
        """檢查狀態並發送下一個指令"""
        if not self.is_connected():
            self.command_queue.clear()
            self.is_processing = False
            return

        if self.is_processing:
            return

        if not self.command_queue:
            self.queue_finished.emit()
            return

        # 確保上一個指令相關的 settle 狀態清乾淨
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

        # 外層 timeout
        self.timeout_timer.start(int(timeout * 1000))

        # Pre-flush：清掉可能存在的殘留資料，避免前一個指令的背景 noise 汙染
        try:
            if self.device and self.device.in_waiting:
                _ = self.device.read(self.device.in_waiting)
        except Exception:
            # 若 flush 出錯，不要讓整個流程掛掉
            pass

        # 發送指令
        self._raw_send(cmd)

    def _raw_send(self, data: Union[str, bytes]):
        """底層發送邏輯"""
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
        處理接收到的資料。
        1. 先透過 data_received 送給 UI。
        2. 若有正在處理的指令，則累積到 current_response_lines。
        3. 利用 wait_for + settle_timer 決定指令何時真正完成。
        """
        # 先通知 UI 顯示原始資料
        self.data_received.emit(data)

        if not self.is_processing:
            return

        # -----------------------------
        # Echo 過濾：排除 "prompt + command" 那一行
        # 例如: "root@box:~# fdisk -l /dev/mmcblk0"
        # -----------------------------
        if self.prompt_regex.match(data):
            if isinstance(self.current_cmd, str) and self.current_cmd and self.current_cmd in data:
                return

        # 累積這一行輸出
        self.current_response_lines.append(data)

        # 記錄時間，用來判斷 burst 輸出
        now = time.time()
        self.line_times.append(now)
        if len(self.line_times) > 16:
            self.line_times.pop(0)

        # 若已經進入「收尾階段」（也就是已 match 過一次 token）
        # 則每次有新資料都重新啟動 settle_timer
        if self.has_matched_token:
            self._restart_settle_timer()
            return

        # 尚未 match wait_for → 嘗試 match
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
            # 第一次 match 到 wait_for，進入「收尾階段」
            self.has_matched_token = True
            self._restart_settle_timer()

    def _restart_settle_timer(self):
        """
        智慧型重新啟動 settle_timer，包含簡單的 adaptive 調整：
        - 如果最近幾行輸出非常密集，代表是 burst output，則延長 settle time。
        """
        adaptive_delay = self.settle_delay_ms

        if len(self.line_times) >= 4:
            dt = self.line_times[-1] - self.line_times[-4]
            # 例如 30ms 內連續 4 行 → 視為 burst，延長 settle 時間
            if dt < 0.03:
                adaptive_delay = max(adaptive_delay, 150)

        self.settle_timer.start(adaptive_delay)

    def _on_settle_timeout(self):
        """
        當在「收尾階段」中一段時間沒有新資料時，判斷輸出已經穩定，
        宣告該指令完成。
        """
        if not self.is_processing:
            return

        # 如果是以 prompt 為 wait_for 的情境，最後一行若不像 prompt，可以再等一下
        last_line = self.current_response_lines[-1] if self.current_response_lines else ""

        want_prompt_check = (
            isinstance(self.current_wait_token, str)
            and any(ch in self.current_wait_token for ch in ["#", "$", ">"])
        )

        if want_prompt_check and self.prompt_regex and not self.prompt_regex.match(last_line):
            # 看起來還沒回到 prompt，再給一點時間
            self.settle_timer.start(self.settle_delay_ms)
            return

        # 走到這裡，代表輸出已經穩定，可以宣告指令完成
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
        """當整個指令等待超時（外層 timeout）"""
        if not self.is_processing:
            return

        # 無論有沒有收到部分資料，都回傳現在的 buffer
        self.command_finished.emit(self.current_cmd, self.current_response_lines.copy())

        # 停掉相關 timer，重置狀態
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
                          timeout: float = 10.0) -> List[str]:
        """
        同步阻塞方式執行 command。
        回傳：完整 response (list of lines)
        """
        if not self.is_connected():
            return ["[ERROR] Device not connected"]

        loop = QEventLoop()
        result_holder = {"response": []}

        def on_finished(finished_cmd, response_lines):
            if finished_cmd == cmd:
                result_holder["response"] = response_lines
                loop.quit()

        self.command_finished.connect(on_finished)

        # 將指令排入佇列
        self.send_command_queued(cmd, wait_for, timeout)

        # 阻塞直到該指令完成（或 timeout）
        loop.exec()

        self.command_finished.disconnect(on_finished)

        return result_holder["response"]


if __name__ == "__main__":
    from PySide6.QtCore import QCoreApplication

    class TestConsole(QObject):
        def __init__(self):
            super().__init__()
            self.model = SerialDeviceModel()
            
            # 連接訊號
            self.model.data_received.connect(self.on_data_received)
            self.model.queue_finished.connect(self.on_all_finished)
            
        def start(self):
            # 1. 連接模擬裝置
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
            # 這裡顯示從裝置收到的所有原始資料
            # print(f"[Device] >> {data}")
            pass

        @Slot()
        def on_all_finished(self):
            print("\n--- All Commands Processed. Exiting... ---")
            self.model.disconnect_device()
            QCoreApplication.quit() # 退出程式
    
    app = QCoreApplication(sys.argv)
    controller = TestConsole()
    QTimer.singleShot(0, controller.start)
    sys.exit(app.exec())