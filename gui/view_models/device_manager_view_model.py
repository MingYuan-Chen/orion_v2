from PySide6.QtCore import QObject, QThread, Signal, Slot
from typing import Dict, Optional, List
from core.models.device_manager_model import DeviceManagerModel
from core.workers.serial_device_worker import SerialDeviceWorker
from util.logger import logger


class DeviceManagerViewModel(QObject):
    """device manager view model"""
    device_connected = Signal(str, bool, str)  # device_id, success, message
    device_disconnected = Signal(str, bool, str)  # device_id, success, message
    command_completed = Signal(str, str, str)  # device_id, command, response
    
    def __init__(self):
        super().__init__()
        self.device_manager = DeviceManagerModel()
        
        # create worker thread
        self.worker_thread = QThread()
        self.worker = SerialDeviceWorker(self.device_manager)
        self.worker.moveToThread(self.worker_thread)
        
        # connect signals
        self.worker.connection_result.connect(self.device_connected)
        self.worker.disconnection_result.connect(self.device_disconnected)
        self.worker.command_result.connect(self.command_completed)
        
        # start thread
        self.worker_thread.start()
        
    def connect_serial_device(self, device_id: str, port: str, baudrate: int = 115200, timeout: int = 3):
        """connect serial device"""
        self.worker.connect_device(device_id, port, baudrate, timeout)
        
    def disconnect_device(self, device_id: str):
        """disconnect device"""
        self.worker.disconnect_device(device_id)
        
    def send_command(self, device_id: str, command: str, timeout: int = 10):
        """send command to device"""
        self.worker.send_command(device_id, command, timeout)
        
    def disconnect_all_devices(self):
        """disconnect all devices"""
        self.worker.disconnect_all_devices()
        
    def get_connected_devices(self) -> List[str]:
        """get connected device ids"""
        return [device_id for device_id, device in self.device_manager.devices.items() 
                if device.is_connected]
                
    def is_device_connected(self, device_id: str) -> bool:
        """check if device is connected"""
        device = self.device_manager.get_device(device_id)
        return device is not None and device.is_connected
        
    def cleanup_resources(self):
        """cleanup resources (call when app closed)"""
        # disconnect all devices
        self.disconnect_all_devices()
        
        # stop thread
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer

    # create application
    app = QApplication([])
    view_model = DeviceManagerViewModel()

    # connect signal to handler function
    def on_device_connected(device_id, success, message):
        print(f"device connected: {device_id}, success: {success}, message: {message}")
        
    def on_device_disconnected(device_id, success, message):
        print(f"device disconnected: {device_id}, success: {success}, message: {message}")
        app.quit()  # quit app after disconnected

    view_model.device_connected.connect(on_device_connected)
    view_model.device_disconnected.connect(on_device_disconnected)

    # connect device
    view_model.connect_serial_device("device_1", "COM4", 115200, 3)

    # 3 seconds later, disconnect device
    QTimer.singleShot(3000, lambda: view_model.disconnect_device("device_1"))

    # enter event loop
    app.exec()

    # cleanup resources
    view_model.cleanup_resources()
    print("program finished")

