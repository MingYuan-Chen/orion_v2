#!/usr/bin/env python
"""
Device Connection View

Handle the display of device connection UI and connection process
"""

import os
import sys
import time
import random
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication, QVBoxLayout
from PySide6.QtCore import QFile, Signal, Slot, QIODevice
from PySide6.QtUiTools import QUiLoader
from util.logger import logger


class DeviceConnectionDialog(QDialog):
    """Device connection dialog class"""
    
    def __init__(self, parent=None):
        """Initialize device connection dialog
        
        Args:
            parent: parent window
        """
        super().__init__(parent)
        
        # Connected device information (to be returned to caller)
        self.connected_device = None
        
        # Load UI
        self._load_ui_direct()
        
        # Setup connections
        self._setup_connections()
        
        # Additional setup - populate combo boxes with sample data
        self._setup_ui()
        
        # Set initial state - show Serial page
        self._on_connection_type_changed(0)
    
    def _load_ui_direct(self):
        """Load UI with a more direct approach"""
        try:
            # Get UI file path - support PyInstaller
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
                ui_file_path = os.path.join(base_path, 'gui', 'ui', 'device_connection.ui')
            else:
                # Normal development environment
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ui_file_path = os.path.join(current_dir, "ui", "device_connection.ui")
                
            logger.debug(f"Loading UI from: {ui_file_path}")
            
            # Create main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(main_layout)
            
            # Load UI file
            ui_file = QFile(ui_file_path)
            if not ui_file.open(QIODevice.ReadOnly):
                error_msg = f"Cannot open {ui_file_path}: {ui_file.errorString()}"
                logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                raise RuntimeError(error_msg)
            
            # Load UI using QUiLoader
            loader = QUiLoader()
            self.ui_widget = loader.load(ui_file)
            ui_file.close()
            
            if not self.ui_widget:
                error_msg = f"Failed to load UI file: {loader.errorString()}"
                logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                raise RuntimeError(error_msg)
            
            # Add widget to layout
            main_layout.addWidget(self.ui_widget)
            
            # Set UI properties
            self.setWindowTitle("Device Connection")
            self.resize(self.ui_widget.size())
            
            logger.debug("Device connection UI loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load UI: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load UI: {str(e)}")
            raise
    
    def _setup_connections(self):
        """Setup signal connections"""
        try:
            # Connect events
            self.ui_widget.combo_box_connection_type.currentIndexChanged.connect(self._on_connection_type_changed)
            self.ui_widget.push_button_connect.clicked.connect(self._on_connect_clicked)
            self.ui_widget.push_button_cancel.clicked.connect(self._on_disconnect_clicked)
            
            logger.debug("Device connection signals connected")
        except Exception as e:
            logger.error(f"Failed to connect device connection signals: {str(e)}", exc_info=True)
    
    def _setup_ui(self):
        """Set up UI with initial values"""
        try:
            # Serial port setup - and default values
            self.ui_widget.combo_box_port.addItems(["COM1", "COM2", "COM3", "COM4", "/dev/ttyUSB0", "/dev/ttyUSB1"])
            self.ui_widget.combo_box_baudrate.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
            self.ui_widget.combo_box_latency.addItems(["1", "2", "5", "10", "16"])
            self.ui_widget.combo_box_port.setCurrentText("COM4")
            self.ui_widget.combo_box_baudrate.setCurrentText("115200")
            self.ui_widget.combo_box_latency.setCurrentText("3")

        except Exception as e:
            logger.error(f"Error setting UI initial values: {str(e)}", exc_info=True)
    
    def _on_connection_type_changed(self, index):
        """Handle connection type change
        
        Args:
            index: selected index
        """
        try:
            # Show the corresponding page in the stacked widget
            self.ui_widget.stacked_widget_connection.setCurrentIndex(index)
            logger.debug(f"Connection type changed to: {self.ui_widget.combo_box_connection_type.currentText()}")
        except Exception as e:
            logger.error(f"Error switching connection type: {str(e)}", exc_info=True)
    
    def _on_connect_clicked(self):
        """Handle connect button click"""
        # Get connection type
        connection_type = self.ui_widget.combo_box_connection_type.currentText()
        
        try:
            logger.info(f"Connecting to {connection_type} device...")
            
            # Disable connect button during connection
            self.ui_widget.push_button_connect.setEnabled(False)
            self.ui_widget.push_button_connect.setText("Connecting...")
            QApplication.processEvents()  # Ensure UI update
            
            # Process by connection type
            if connection_type == "Serial":
                self._connect_serial()
            elif connection_type == "SSH":
                self._connect_ssh()
            elif connection_type == "TCP/IP":
                self._connect_tcpip()
            else:
                raise ValueError(f"Unsupported connection type: {connection_type}")
                
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Re-enable connect button
            self.ui_widget.push_button_connect.setEnabled(True)
            self.ui_widget.push_button_connect.setText("Connect")
            
            # Show error dialog
            QMessageBox.critical(self, "Connection Error", error_msg)
    
    def _on_disconnect_clicked(self):
        """Handle disconnect button click (cancel)"""
        # If we were in process of connecting, cancel it
        if not self.ui_widget.push_button_connect.isEnabled():
            self.ui_widget.push_button_connect.setEnabled(True)
            self.ui_widget.push_button_connect.setText("Connect")
        
        # Close the dialog, returning QDialog.Rejected
        self.reject()
    
    def _connect_serial(self):
        """Connect to serial device"""
        # Get connection parameters
        port = self.ui_widget.combo_box_port.currentText()
        baudrate = self.ui_widget.combo_box_baudrate.currentText()
        latency = self.ui_widget.combo_box_latency.currentText()
        
        # In a real application, you would connect to the device here
        # For demonstration, we'll simulate a connection with a delay
        logger.info(f"Connecting to Serial port {port} with baudrate {baudrate} and latency {latency}...")
        
        # Simulate processing
        QApplication.processEvents()  # Ensure UI updates
        time.sleep(1)  # Simulate connection time
        
        # Randomly succeed or fail (for demonstration purposes)
        # In a real application, you'd check actual connection status
        if random.random() > 0.3:  # 70% success rate
            # Connection successful
            logger.info(f"Successfully connected to Serial device on {port}")
            
            # Create device info to return to caller
            self.connected_device = {
                'name': f"Serial Device ({port})",
                'type': 'Serial',
                'address': port,
                'status': 'Connected',
                'details': {
                    'baudrate': baudrate,
                    'latency': latency
                }
            }
            
            # Close dialog with success
            self.accept()
        else:
            # Connection failed
            error_msg = f"Failed to connect to Serial device on {port}"
            logger.error(error_msg)
            
            # Re-enable connect button
            self.ui_widget.push_button_connect.setEnabled(True)
            self.ui_widget.push_button_connect.setText("Connect")
            
            # Show error dialog
            QMessageBox.critical(self, "Connection Error", error_msg)
    
    def _connect_ssh(self):
        """Connect to SSH device"""
        # Get connection parameters
        host = self.ui_widget.line_edit_host.text()
        port = self.ui_widget.line_edit_port.text()
        username = self.ui_widget.line_edit_username.text()
        
        # Basic validation
        if not host:
            raise ValueError("Host is required")
        
        # In a real application, you would connect to the SSH server here
        logger.info(f"Connecting to SSH server {host}:{port} as {username}...")
        
        # Simulate processing
        QApplication.processEvents()  # Ensure UI updates
        time.sleep(1)  # Simulate connection time
        
        # Randomly succeed or fail (for demonstration purposes)
        if random.random() > 0.3:  # 70% success rate
            # Connection successful
            logger.info(f"Successfully connected to SSH server at {host}")
            
            # Create device info to return to caller
            self.connected_device = {
                'name': f"SSH ({host})",
                'type': 'SSH',
                'address': f"{host}:{port}",
                'status': 'Connected',
                'details': {
                    'username': username
                }
            }
            
            # Close dialog with success
            self.accept()
        else:
            # Connection failed
            error_msg = f"Failed to connect to SSH server at {host}"
            logger.error(error_msg)
            
            # Re-enable connect button
            self.ui_widget.push_button_connect.setEnabled(True)
            self.ui_widget.push_button_connect.setText("Connect")
            
            # Show error dialog
            QMessageBox.critical(self, "Connection Error", error_msg)
    
    def _connect_tcpip(self):
        """Connect to TCP/IP device"""
        # Get connection parameters
        ip = self.ui_widget.line_edit_ip.text()
        port = self.ui_widget.line_edit_port_tcp.text()
        
        # Basic validation
        if not ip:
            raise ValueError("IP address is required")
        if not port:
            raise ValueError("Port is required")
        
        # In a real application, you would connect to the TCP/IP device here
        logger.info(f"Connecting to TCP/IP device at {ip}:{port}...")
        
        # Simulate processing
        QApplication.processEvents()  # Ensure UI updates
        time.sleep(1)  # Simulate connection time
        
        # Randomly succeed or fail (for demonstration purposes)
        if random.random() > 0.3:  # 70% success rate
            # Connection successful
            logger.info(f"Successfully connected to TCP/IP device at {ip}:{port}")
            
            # Create device info to return to caller
            self.connected_device = {
                'name': f"TCP/IP Device ({ip})",
                'type': 'TCP/IP',
                'address': f"{ip}:{port}",
                'status': 'Connected',
                'details': {}
            }
            
            # Close dialog with success
            self.accept()
        else:
            # Connection failed
            error_msg = f"Failed to connect to TCP/IP device at {ip}:{port}"
            logger.error(error_msg)
            
            # Re-enable connect button
            self.ui_widget.push_button_connect.setEnabled(True)
            self.ui_widget.push_button_connect.setText("Connect")
            
            # Show error dialog
            QMessageBox.critical(self, "Connection Error", error_msg)


# Allow direct testing of this dialog
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = DeviceConnectionDialog()
    result = dialog.exec()
    
    print(f"Dialog result: {result}")
    if result == QDialog.Accepted:
        print(f"Connected device: {dialog.connected_device}")
    else:
        print("No connected device") 