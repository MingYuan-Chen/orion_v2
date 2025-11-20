import re
import sys
import time
import serial
import serial.tools.list_ports
from collections import deque
from typing import Optional, List, Union, Tuple
from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer

class SerialListener(QThread):
    received = Signal(str)
    error = Signal(str)

    def __init__(self, device: serial.Serial, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.device = device
        self.running = True

    def run(self):
        try:
            while self.running and self.device and self.device.is_open:
                if self.device.in_waiting:
                    # Read line by line
                    data = self.device.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        ansi_csi_pattern = r'\x1b\[[0-?]*[ -/]*[@-~]'
                        data = re.sub(ansi_csi_pattern, '', data)
                        data = data.replace('\x00', '')
                        self.received.emit(data)
                self.msleep(20)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.running = False
        self.quit()
        self.wait(500)

# ============================
# Modified SerialDeviceModel
# ============================
class SerialDeviceModel(QObject):
    connection_result = Signal(bool, str)
    disconnection_result = Signal(bool, str)
    data_received = Signal(str)
    
    # 新增訊號：通知外部某個指令序列已經全部執行完畢
    queue_finished = Signal() 

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.device: Optional[serial.Serial] = None
        self.listener: Optional[SerialListener] = None
        
        # --- 新增：佇列控制變數 ---
        self.command_queue = deque()  # 儲存 (command, wait_token) 的 Tuple
        self.is_processing = False    # 是否正在處理指令中
        self.current_wait_token = None # 當前正在等待的結束關鍵字
        
        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_command_timeout)
        self.current_timeout_sec = 3.0

    @staticmethod
    def get_available_ports() -> List[serial.tools.list_ports_common.ListPortInfo]:
        return serial.tools.list_ports.comports()

    def is_connected(self) -> bool:
        return self.device is not None and self.device.is_open

    def connect_device(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> bool:
        if self.is_connected():
            self.disconnect_device()
            time.sleep(0.1)

        try:
            self.device = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
            
            self.listener = SerialListener(self.device, self)
            # 修改：這裡連線到新的處理函數 _handle_incoming_data
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
        # 斷線時清空佇列與重置狀態
        self.command_queue.clear()
        self.is_processing = False
        self.timeout_timer.stop()
        
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
    #  核心邏輯：佇列處理與發送
    # ==========================================

    def send_command_queued(self, command: str, wait_for: str = "#", timeout: float = 3.0):
        """
        將指令加入佇列。
        :param command: 要發送的指令
        :param wait_for: 發送後，必須收到此字串才算完成 (例如 "OK", ">", "DONE")
        :param timeout: 等待該指令回應的最大秒數
        """
        self.command_queue.append({
            'cmd': command, 
            'wait_for': wait_for, 
            'timeout': timeout
        })
        self._process_next_command()

    def _process_next_command(self):
        """檢查狀態並發送下一個指令"""
        if not self.is_connected():
            self.command_queue.clear()
            self.is_processing = False
            return

        # 如果目前正在忙碌 (等待上一個指令的回應)，則不動作
        if self.is_processing:
            return

        # 如果佇列空了，發出結束訊號
        if not self.command_queue:
            self.queue_finished.emit()
            return

        # 取出下一個指令
        item = self.command_queue.popleft()
        cmd = item['cmd']
        self.current_wait_token = item['wait_for']
        timeout = item['timeout']

        self.is_processing = True
        
        # 設定 Timeout (避免裝置當機導致整個佇列卡死)
        self.timeout_timer.start(int(timeout * 1000))
        
        # 發送指令
        self._raw_send(cmd)

    def _raw_send(self, data: Union[str, bytes]):
        """底層發送邏輯"""
        try:
            if isinstance(data, str):
                # 這裡可以依照需求加入 debug print
                # print(f"Sending: {data}") 
                payload = (data + "\r\n").encode('utf-8')
            elif isinstance(data, bytes):
                payload = data
            self.device.write(payload)
        except serial.SerialException as e:
            self.data_received.emit(f"Failed to send data: {e}")
            self.disconnect_device()

    def _handle_incoming_data(self, data: str):
        """
        處理接收到的資料。
        1. 將資料透過 Signal 傳給 UI 顯示。
        2. 檢查是否包含 current_wait_token，若有則觸發下一條指令。
        """
        # 先通知 UI 顯示原始資料
        self.data_received.emit(data)

        # 檢查佇列邏輯
        if self.is_processing and self.current_wait_token:
            # 判斷條件：接收到的字串是否包含等待的關鍵字
            # 您可以依據需求修改為 == 或者 regex match
            if self.current_wait_token in data:
                # print(f"Token '{self.current_wait_token}' found in '{data}'. Next.")
                self.timeout_timer.stop()
                self.is_processing = False
                self.current_wait_token = None
                # 稍微延遲一點點再發下一個，避免某些裝置處理不及 (可選)
                QTimer.singleShot(50, self._process_next_command)

    def _on_command_timeout(self):
        """當等待回應超時"""
        if self.is_processing:
            err_msg = f"[Timeout] Waiting for '{self.current_wait_token}' failed."
            self.data_received.emit(err_msg)
            
            # 策略：超時後是「放棄後面所有指令」還是「繼續下一個」？
            # 這裡示範：繼續執行下一個 (標記目前這個結束)
            self.is_processing = False
            self.current_wait_token = None
            self._process_next_command()

    def on_error(self, msg):
        self.data_received.emit(msg)
        self.disconnect_device()


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
                ("uname -a", "~#"),
                ("cat /etc/os-release", "PRETTY_NAME="),
                ("strings /dev/mtd5 | grep -E 'U-Boot [0-9]{4}\\.'", ")"),
                ("lscpu | grep 'Model name'", "name:"),
                ("free -h | grep 'Mem:'", "~#"),
                ("top -b -n 1 | head -n 5", "Swap:")
            ]
            for cmd, wait_for in cmds:
                self.model.send_command_queued(cmd, wait_for, 10)
            

        @Slot(str)
        def on_data_received(self, data):
            # 這裡顯示從裝置收到的所有原始資料
            print(f"[Device] >> {data}")

        @Slot()
        def on_all_finished(self):
            print("\n--- All Commands Processed. Exiting... ---")
            self.model.disconnect_device()
            QCoreApplication.quit() # 退出程式
    
    app = QCoreApplication(sys.argv)
    controller = TestConsole()
    QTimer.singleShot(0, controller.start)
    sys.exit(app.exec())