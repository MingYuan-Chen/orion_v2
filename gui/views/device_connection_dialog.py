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
from PySide6.QtCore import QFile, Signal, Slot, QIODevice, Qt, QTimer
from PySide6.QtUiTools import QUiLoader
from util.logger import logger

# Import for serial port detection
try:
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.warning("pyserial not available - serial port detection disabled")


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
        
        # Connection timeout timer
        self.connection_timeout_timer = QTimer()
        self.connection_timeout_timer.setSingleShot(True)
        self.connection_timeout_timer.timeout.connect(self._on_connection_timeout)
        
        # Load UI
        self._load_ui_direct()
        
        # Setup connections
        self._setup_connections()
        
        # Additional setup - populate combo boxes with sample data
        self._setup_ui()
        
        # Set initial state - show Serial page
        self._on_connection_type_changed(0)
        
        # Apply dark theme
        self._apply_dark_theme()
    
    def _load_ui_direct(self):
        """Load UI with a more direct approach"""
        try:
            # Get UI file path - support PyInstaller
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
                ui_file_path = os.path.join(base_path, 'gui', 'ui', 'device_connection_dialog.ui')
                icon_path = os.path.join(base_path, 'resources', 'icons', 'header.ico')
            else:
                # Normal development environment
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ui_file_path = os.path.join(current_dir, "ui", "device_connection_dialog.ui")
                
                # Get icon path - go up two directories to find resources
                base_dir = os.path.dirname(os.path.dirname(current_dir))
                icon_path = os.path.join(base_dir, "resources", "icons", "header.ico")
                
            logger.debug(f"Loading UI from: {ui_file_path}")
            logger.debug(f"Icon path: {icon_path}")
            
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
            
            # Set application icon
            if os.path.exists(icon_path):
                from PySide6.QtGui import QIcon
                self.setWindowIcon(QIcon(icon_path))
                logger.debug("Connection dialog icon set successfully")
            else:
                logger.warning(f"Icon file not found: {icon_path}")
            
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
            # add refresh button
            # self._add_refresh_button()
            
            # dynamic detection of available serial ports
            available_ports = self._get_available_serial_ports()
            
            # Serial port setup - use detected ports
            if available_ports:
                self.ui_widget.combo_box_port.addItems(available_ports)
                logger.info(f"Detected {len(available_ports)} serial ports: {available_ports}")
            else:
                # if no ports are detected, add some default values as alternatives
                default_ports = ["COM1", "COM2", "COM3", "COM4", "/dev/ttyUSB0", "/dev/ttyUSB1"]
                self.ui_widget.combo_box_port.addItems(default_ports)
                logger.warning("No serial ports detected, using default port list")
            
            # other configuration items remain unchanged
            self.ui_widget.combo_box_baudrate.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
            self.ui_widget.combo_box_latency.addItems(["1", "2", "3", "5", "10", "16"])
            
            # set default values
            self._set_default_values()

        except Exception as e:
            logger.error(f"Error setting UI initial values: {str(e)}", exc_info=True)
    
    def _add_refresh_button(self):
        """add refresh button to serial port selection"""
        try:
            from PySide6.QtWidgets import QPushButton, QHBoxLayout
            from PySide6.QtGui import QIcon
            from PySide6.QtCore import QSize
            
            # get the grid layout of the serial port selection
            grid_layout = self.ui_widget.group_box_serial.layout()
            
            # create refresh button
            self.refresh_button = QPushButton("🔄")
            self.refresh_button.setToolTip("Refresh available serial ports")
            self.refresh_button.setMaximumSize(QSize(30, 25))
            self.refresh_button.setMinimumSize(QSize(30, 25))
            
            # connect the click event of the refresh button
            self.refresh_button.clicked.connect(self._refresh_serial_ports)
            
            # add the refresh button to the serial port selection row
            grid_layout.addWidget(self.refresh_button, 0, 2, 1, 1)  # row=0, col=2
            
            logger.debug("Refresh button added to serial port selection")
            
        except Exception as e:
            logger.error(f"Error adding refresh button: {str(e)}", exc_info=True)
    
    def _refresh_serial_ports(self):
        """refresh serial port list"""
        try:
            logger.info("Refreshing serial port list...")
            
            # temporarily disable the refresh button
            self.refresh_button.setEnabled(False)
            self.refresh_button.setText("...")
            QApplication.processEvents()
            
            # save the current selected port
            current_port = self.ui_widget.combo_box_port.currentText()
            
            # clear the current list
            self.ui_widget.combo_box_port.clear()
            
            # re-detect the serial ports
            available_ports = self._get_available_serial_ports()
            
            if available_ports:
                self.ui_widget.combo_box_port.addItems(available_ports)
                logger.info(f"Refreshed serial ports: {available_ports}")
                
                # try to restore the previous selected port
                index = self.ui_widget.combo_box_port.findText(current_port)
                if index >= 0:
                    self.ui_widget.combo_box_port.setCurrentIndex(index)
                    logger.debug(f"Restored previous selection: {current_port}")
                else:
                    # if the previous port is no longer available, select the first one
                    if self.ui_widget.combo_box_port.count() > 0:
                        self.ui_widget.combo_box_port.setCurrentIndex(0)
                        logger.debug(f"Previous port {current_port} no longer available, selected first port")
                        
            else:
                # if no ports are detected, add default values
                default_ports = ["COM1", "COM2", "COM3", "COM4", "/dev/ttyUSB0", "/dev/ttyUSB1"]
                self.ui_widget.combo_box_port.addItems(default_ports)
                logger.warning("No serial ports detected after refresh, using default port list")
                
                # try to restore the previous selection
                index = self.ui_widget.combo_box_port.findText(current_port)
                if index >= 0:
                    self.ui_widget.combo_box_port.setCurrentIndex(index)
                    
        except Exception as e:
            logger.error(f"Error refreshing serial ports: {str(e)}", exc_info=True)
        finally:
            # re-enable the refresh button
            self.refresh_button.setEnabled(True)
            self.refresh_button.setText("🔄")
    
    def _get_available_serial_ports(self):
        """check available serial ports
        
        Returns:
            list: available serial ports
        """
        ports = []
        
        if not SERIAL_AVAILABLE:
            logger.warning("Serial port detection not available - pyserial module not found")
            return ports
            
        try:
            # get all available serial ports
            available_ports = serial.tools.list_ports.comports()
            
            for port_info in available_ports:
                port_name = port_info.device
                port_description = port_info.description
                
                # filter out some ports (e.g. bluetooth)
                if self._is_valid_serial_port(port_info):
                    ports.append(port_name)
                    logger.debug(f"Found serial port: {port_name} - {port_description}")
                else:
                    logger.debug(f"Filtered out port: {port_name} - {port_description}")
            
            # sort by port name
            ports.sort()
            
        except Exception as e:
            logger.error(f"Error detecting serial ports: {str(e)}", exc_info=True)
            
        return ports
    
    def _is_valid_serial_port(self, port_info):
        """check if the port is a valid serial port
        
        Args:
            port_info: serial port info object
            
        Returns:
            bool: whether the port is a valid serial port
        """
        port_name = port_info.device.lower()
        description = port_info.description.lower()
        
        # exclude bluetooth ports
        if 'bluetooth' in description or 'bt' in description:
            return False
            
        # exclude virtual ports
        if 'virtual' in description:
            return False
            
        # Windows system - contains COM ports
        if port_name.startswith('com'):
            return True
            
        # Linux system - contains common USB serial ports and serial devices
        if (port_name.startswith('/dev/ttyusb') or 
            port_name.startswith('/dev/ttyacm') or 
            port_name.startswith('/dev/ttys') or
            port_name.startswith('/dev/ttyama')):
            return True
            
        # macOS system - USB serial ports
        if port_name.startswith('/dev/cu.usb') or port_name.startswith('/dev/tty.usb'):
            return True
            
        return False
    
    def _set_default_values(self):
        """set default values"""
        try:
            # try to set a common default port
            port_count = self.ui_widget.combo_box_port.count()
            if port_count > 0:
                # on Windows, prefer COM4, on Linux, prefer the first detected port
                default_set = False
                
                for i in range(port_count):
                    port_text = self.ui_widget.combo_box_port.itemText(i)
                    # on Windows, prefer COM4
                    if port_text.upper() == "COM4":
                        self.ui_widget.combo_box_port.setCurrentIndex(i)
                        default_set = True
                        break
                
                # if COM4 is not found, select the first port
                if not default_set:
                    self.ui_widget.combo_box_port.setCurrentIndex(0)
            
            # set other default values
            self.ui_widget.combo_box_baudrate.setCurrentText("115200")
            self.ui_widget.combo_box_latency.setCurrentText("3")
            
        except Exception as e:
            logger.error(f"Error setting default values: {str(e)}", exc_info=True)
    
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
            
            # Start connection timeout timer (15 seconds)
            self.connection_timeout_timer.start(15000)
            
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
            
            # Stop timeout timer
            self.connection_timeout_timer.stop()
            
            # Re-enable connect button
            self.ui_widget.push_button_connect.setEnabled(True)
            self.ui_widget.push_button_connect.setText("Connect")
            
            # Show error dialog
            QMessageBox.critical(self, "Connection Error", error_msg)
    
    def _on_connection_timeout(self):
        """Handle connection timeout"""
        logger.warning("Device connection timed out")
        
        # Re-enable connect button
        self.ui_widget.push_button_connect.setEnabled(True)
        self.ui_widget.push_button_connect.setText("Connect")
        
        # Show timeout error dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Connection Timeout")
        msg_box.setText("Connection Timeout")
        msg_box.setInformativeText("Device connection timed out. Please check if the device is properly connected and try again.")
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # apply dark style sheet
        msg_box.setStyleSheet(self._get_dark_style_sheet())
        
        msg_box.exec()
    
    def _on_disconnect_clicked(self):
        """Handle disconnect button click (cancel)"""
        # Stop timeout timer if running
        self.connection_timeout_timer.stop()
        
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
        baudrate = int(self.ui_widget.combo_box_baudrate.currentText())
        latency = int(self.ui_widget.combo_box_latency.currentText())
        
        # Check if view model exists
        if hasattr(self, 'view_model') and self.view_model:
            logger.info(f"Using view model to connect to device: {port}")
            
            # Generate device ID (adjust as needed)
            device_id = f"serial_{port.replace('/', '_').replace(':', '_')}"
            
            # Use view model to connect
            self.view_model.connect_serial_device(device_id, port, baudrate, latency)
            
            # Note: Connection results will be handled by _on_device_connected_result function
            return
        else:
            # If no view model, show error
            raise RuntimeError("View model not available for device connection")
    
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
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Connection Error")
            msg_box.setText("SSH Connection Error")
            msg_box.setInformativeText(error_msg)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setStandardButtons(QMessageBox.Ok)
            
            # apply dark style sheet
            msg_box.setStyleSheet(self._get_dark_style_sheet())
            
            msg_box.exec()
    
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
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Connection Error")
            msg_box.setText("Connection Error")
            msg_box.setInformativeText(error_msg)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setStandardButtons(QMessageBox.Ok)
            
            # apply dark style sheet
            msg_box.setStyleSheet(self._get_dark_style_sheet())
            
            msg_box.exec()

    def set_view_model(self, view_model):
        """Set view model for device operations
        
        Args:
            view_model: DeviceManagerViewModel instance
        """
        self.view_model = view_model
        
        # Connect view model signals
        self.view_model.connection_result.connect(self._on_device_connected_result)
        logger.debug("DeviceConnectionDialog: view model signals connected")

    @Slot(str, bool, str)
    def _on_device_connected_result(self, device_id, success, message):
        """Handle device connection result from view model
        
        Args:
            device_id: device ID
            success: connection success
            message: connection result message
        """
        # Stop timeout timer
        self.connection_timeout_timer.stop()
        
        # Re-enable connect button
        self.ui_widget.push_button_connect.setEnabled(True)
        self.ui_widget.push_button_connect.setText("Connect")
        
        if success:
            # Connection successful
            logger.info(f"Successfully connected to device {device_id}")
            
            # Parse information from device ID
            parts = device_id.split('_')
            device_type = parts[0] if len(parts) > 0 else "serial"
            address = parts[1] if len(parts) > 1 else device_id
            
            # Get connection parameters
            port = self.ui_widget.combo_box_port.currentText()
            baudrate = self.ui_widget.combo_box_baudrate.currentText()
            latency = self.ui_widget.combo_box_latency.currentText()
            
            # If view model exists, update device details
            if hasattr(self, 'view_model') and self.view_model:
                details = {
                    'port': port,
                    'baudrate': baudrate,
                    'latency': latency
                }
                self.view_model.update_device_info(device_id, details)
            
            # Create device info to return to caller
            self.connected_device = {
                'id': device_id,
                'name': f"Serial Device ({port})",
                'type': 'Serial',
                'address': port,
                'status': 'Connected',
                'details': {
                    'port': port,
                    'baudrate': baudrate,
                    'latency': latency
                }
            }
            
            # Successfully close dialog
            self.accept()
        else:
            # Connection failed
            logger.error(f"Failed to connect to device: {message}")
            
            # Show error dialog
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Connection Error")
            msg_box.setText("Device Connection Failed")
            msg_box.setInformativeText(f"Failed to connect to device: {message}")
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setStandardButtons(QMessageBox.Ok)
            
            # apply dark style sheet
            msg_box.setStyleSheet(self._get_dark_style_sheet())
            
            msg_box.exec()

    def _get_dark_style_sheet(self):
        """Return the dark style sheet"""
        return """
            QDialog, QWidget {
                background-color: #2E2E2E;
                color: white;
            }
            QLabel {
                color: white;
            }
            QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox {
                background-color: #3E3E3E;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                selection-background-color: #0078D7;
            }
            QComboBox QAbstractItemView {
                background-color: #3E3E3E;
                color: white;
                selection-background-color: #0078D7;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
            QPushButton:pressed {
                background-color: #00559F;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #999999;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 3px;
                margin-top: 10px;
                font-weight: bold;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2E2E2E;
            }
            QTabBar::tab {
                background-color: #252525;
                color: white;
                padding: 6px 12px;
                border: 1px solid #555555;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #3E3E3E;
            }
            QTabBar::tab:hover {
                background-color: #353535;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QStackedWidget {
                background-color: #2E2E2E;
            }
        """
    
    def _apply_dark_theme(self):
        """Apply dark theme to the dialog"""
        # Set stylesheet
        self.setStyleSheet(self._get_dark_style_sheet())
        
        # Set window background
        self.setAutoFillBackground(True)
        self.ui_widget.setAutoFillBackground(True)


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