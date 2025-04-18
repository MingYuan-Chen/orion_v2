from PySide6.QtCore import QObject, Signal, Slot
from typing import Dict, Optional, List
from core.models.device_manager_model import DeviceManagerModel
from util.logger import logger


class SerialDeviceWorker(QObject):
    """serial device worker object, handle device operations"""
    connection_result = Signal(str, bool, str)  # device_id, success, message
    disconnection_result = Signal(str, bool, str)  # device_id, success, message
    command_result = Signal(str, str, str)  # device_id, command, response
    
    def __init__(self, device_manager: DeviceManagerModel):
        super().__init__()
        self.device_manager = device_manager
        
    @Slot(str, str, int, int)
    def connect_device(self, device_id: str, port: str, baudrate: int, timeout: int):
        """connect device"""
        try:
            device = self.device_manager.create_serial_device(device_id, port, baudrate, timeout)
            if not device:
                self.connection_result.emit(device_id, False, f"can't create device {device_id}")
                return
                
            success = device.connect()
            if success:
                self.connection_result.emit(device_id, True, f"success to connect to device {device_id} on port {port}")
            else:
                self.connection_result.emit(device_id, False, f"can't connect to device {device_id} on port {port}")
        except Exception as e:
            logger.error(f"error to connect device {device_id}: {str(e)}")
            self.connection_result.emit(device_id, False, f"error to connect device {device_id}: {str(e)}")
            
    @Slot(str)
    def disconnect_device(self, device_id: str):
        """disconnect device"""
        try:
            success = self.device_manager.disconnect_device(device_id)
            if success:
                self.disconnection_result.emit(device_id, True, f"success to disconnect device {device_id}")
            else:
                self.disconnection_result.emit(device_id, False, f"can't disconnect device {device_id}")
        except Exception as e:
            logger.error(f"error to disconnect device {device_id}: {str(e)}")
            self.disconnection_result.emit(device_id, False, f"error to disconnect device {device_id}: {str(e)}")
            
    @Slot(str, str, int)
    def send_command(self, device_id: str, command: str, timeout: int = 10):
        """send command to device"""
        try:
            response = self.device_manager.send_command(device_id, command, timeout)
            self.command_result.emit(device_id, command, response)
        except Exception as e:
            logger.error(f"error to send command to device {device_id}: {str(e)}")
            self.command_result.emit(device_id, command, f"error to send command to device {device_id}: {str(e)}")
            
    @Slot()
    def disconnect_all_devices(self):
        """disconnect all devices"""
        try:
            self.device_manager.disconnect_all()
            for device_id in list(self.device_manager.devices.keys()):
                self.disconnection_result.emit(device_id, True, f"success to disconnect device {device_id}")
        except Exception as e:
            logger.error(f"error to disconnect all devices: {str(e)}") 


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from core.models.device_manager_model import DeviceManagerModel
    import sys

    # create application
    app = QApplication(sys.argv)
    
    # create necessary model and worker object
    device_manager = DeviceManagerModel()
    worker = SerialDeviceWorker(device_manager)
    
    # connect signal to slot function to display result
    def on_connection_result(device_id, success, message):
        print(f"connection result: device={device_id}, success={success}, message={message}")
        # if connection success, wait 2 seconds and send command
        if success:
            QTimer.singleShot(2000, lambda: send_test_command(device_id))
    
    def on_disconnection_result(device_id, success, message):
        print(f"disconnection result: device={device_id}, success={success}, message={message}")
        # if test finished, quit app
        QTimer.singleShot(1000, app.quit)
    
    def on_command_result(device_id, command, response):
        print(f"command result: device={device_id}")
        print(f"command: {command}")
        print(f"response: {response}")
        # if command finished, disconnect device
        QTimer.singleShot(10000, lambda: disconnect_device(device_id))
    
    def send_test_command(device_id):
        print(f"send test command to device {device_id}...")
        worker.send_command(device_id, "cat /sys/class/gpio/gpio133/value", 5)  # try to send ls command
    
    def disconnect_device(device_id):
        print(f"disconnect device {device_id}...")
        worker.disconnect_device(device_id)
    
    # connect signal
    worker.connection_result.connect(on_connection_result)
    worker.disconnection_result.connect(on_disconnection_result)
    worker.command_result.connect(on_command_result)
    
    # start test - connect device
    device_id = "test_device"
    port = "COM4"  # please modify to your actual COM port
    print(f"try to connect device {device_id} to port {port}...")
    worker.connect_device(device_id, port, 115200, 3)
    
    # if 10 seconds not finished, force quit
    QTimer.singleShot(30000, app.quit)
    
    # execute application
    sys.exit(app.exec())

