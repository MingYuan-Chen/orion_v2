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
        
        # 存儲每個設備的worker和線程
        self.device_workers = {}  # {device_id: (worker, thread)}
        
    def create_device_worker(self, device_id):
        # 為新設備創建專屬worker和線程
        worker_thread = QThread()
        worker = SerialDeviceWorker(self.device_manager, device_id)
        worker.moveToThread(worker_thread)
        
        # 連接信號（需要在信號中傳遞設備ID以區分來源）
        worker.connection_result.connect(self.device_connected)
        worker.disconnection_result.connect(self.device_disconnected)
        worker.command_result.connect(self.command_completed)
        
        # 存儲引用
        self.device_workers[device_id] = (worker, worker_thread)
        logger.info(f"create device worker: {device_id} with thread: {worker_thread}")
        
        # 啟動線程
        worker_thread.start()
        
        return worker
        
    def connect_serial_device(self, device_id, port, baudrate, latency):
        """使用用戶指定的 device_id 連接設備"""
        worker = self.create_device_worker(device_id)
        
        # 使用worker連接設備
        worker.connect_device(device_id, port, baudrate, latency)
        
    def disconnect_device(self, device_id):
        if device_id in self.device_workers:
            worker, thread = self.device_workers[device_id]
            worker.disconnect_device(device_id)
            
            # 可選：斷開連接後清理worker
            thread.quit()
            thread.wait()
            del self.device_workers[device_id]
            logger.info(f"disconnect device: {device_id} with thread: {thread}")
        
    def send_command(self, device_id: str, command: str, timeout: int = 10):
        """send command to device"""
        if device_id in self.device_workers:
            worker, _ = self.device_workers[device_id]
            worker.send_command(device_id, command, timeout)
        
    def disconnect_all_devices(self):
        """disconnect all devices"""
        for device_id, (worker, thread) in self.device_workers.items():
            worker.disconnect_device(device_id)
            logger.info(f"disconnect device: {device_id} with thread: {thread}")
        
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
        
        # stop threads
        for device_id, (_, thread) in self.device_workers.items():
            if thread.isRunning():
                thread.quit()
                thread.wait()

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
    view_model.connect_serial_device("COM4", 115200, 0)

    # 3 seconds later, disconnect device
    QTimer.singleShot(3000, lambda: view_model.disconnect_device("device_COM4"))

    # enter event loop
    app.exec()

    # cleanup resources
    view_model.cleanup_resources()
    print("program finished")

