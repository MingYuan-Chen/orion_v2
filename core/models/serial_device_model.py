import sys
import time
import serial
import serial.tools.list_ports
from typing import Optional, List, Union
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLineEdit, QTextEdit, QLabel
)
from PySide6.QtGui import QKeyEvent # Import QKeyEvent for key press handling


# ============================
# QThread： Background listening serial response
# ============================
class SerialListener(QThread):
    """
    A QThread that listens for incoming data from a serial device in the background.
    """
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
                    # Read line by line, decode, and strip whitespace
                    data = self.device.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        self.received.emit(data)
                self.msleep(20)  # Small delay to prevent high CPU usage
        except serial.SerialException as e:
            # Handle cases where the device is disconnected abruptly
            self.error.emit(f"Serial error: {e}")
        except Exception as e:
            self.error.emit(f"An unexpected error occurred: {e}")

    def stop(self):
        """Stops the listener thread safely."""
        self.running = False
        self.quit()
        self.wait(500) # Wait up to 500ms for the thread to finish


class SerialDeviceModel(QObject):
    """
    A model for handling communication with a serial device.
    Inherits from QObject to support Qt's signal/slot mechanism.
    """
    # Define external signals
    connection_result = Signal(bool, str)  # Emits connection success(bool) and a message(str)
    disconnection_result = Signal(bool, str)  # Emits disconnection success(bool) and a message(str)
    data_received = Signal(str)  # Emits the received data string

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.device: Optional[serial.Serial] = None
        self.listener: Optional[SerialListener] = None

    @staticmethod
    def get_available_ports() -> List[serial.tools.list_ports_common.ListPortInfo]:
        """Returns a list of available serial ports."""
        return serial.tools.list_ports.comports()

    def is_connected(self) -> bool:
        """Check if the serial device is connected."""
        return self.device is not None and self.device.is_open

    def connect_device(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> bool:
        """
        Connects to the specified serial port.
        :return: True if connection is successful, False otherwise.
        """
        if self.is_connected():
            self.disconnect_device()
            time.sleep(0.1) # Brief pause before reconnecting

        try:
            self.device = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
            
            self.listener = SerialListener(self.device, self)
            self.listener.received.connect(self.data_received)
            self.listener.error.connect(self.on_error)
            self.listener.start()

            self.connection_result.emit(True, f"Connected to {port}")
            return True

        except serial.SerialException as e:
            self.connection_result.emit(False, f"Failed to connect to {port}: {e}")
            self.device = None
            return False

    def disconnect_device(self) -> bool:
        """Disconnects from the serial device."""
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

    def send_command(self, data: Union[str, bytes]):
        """
        Sends data to the serial device.
        - If data is a string, it's treated as a command: appends CRLF and encodes as UTF-8.
        - If data is bytes, it's sent as raw bytes.
        """
        if not self.is_connected():
            return

        try:
            if isinstance(data, str):
                payload = (data + "\r\n").encode('utf-8')
            elif isinstance(data, bytes):
                payload = data

            self.device.write(payload)

        except serial.SerialException as e:
            self.data_received.emit(f"Failed to send data: {e}")
            self.disconnect_device()
    
    def on_error(self, msg):
        self.data_received.emit(msg)
        self.disconnect_device()