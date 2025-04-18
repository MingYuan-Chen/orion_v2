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
                ui_file_path = os.path.join(base_path, 'gui', 'ui', 'device_connection_dialog.ui')
            else:
                # Normal development environment
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ui_file_path = os.path.join(current_dir, "ui", "device_connection_dialog.ui")
                
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
            self.ui_widget.combo_box_port.addItems(["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2"])
            self.ui_widget.combo_box_baudrate.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
            self.ui_widget.combo_box_latency.addItems(["1", "2", "3", "5", "10", "16"])
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
        """連接到串行設備"""
        # 獲取連接參數
        port = self.ui_widget.combo_box_port.currentText()
        baudrate = int(self.ui_widget.combo_box_baudrate.currentText())
        latency = int(self.ui_widget.combo_box_latency.currentText())
        
        # 檢查是否有視圖模型
        if hasattr(self, 'view_model') and self.view_model:
            logger.info(f"Using view model to connect to device: {port}")
            
            # 禁用連接按鈕並顯示連接狀態
            self.ui_widget.push_button_connect.setEnabled(False)
            self.ui_widget.push_button_connect.setText("Connecting...")
            QApplication.processEvents()  # 確保 UI 更新
            
            # 生成設備ID (可以根據需要調整)
            device_id = f"serial_{port.replace('/', '_').replace(':', '_')}"
            
            # 使用視圖模型進行連接
            self.view_model.connect_serial_device(device_id, port, baudrate, latency)
            # 連接結果由信號處理函數處理
            return
    
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

    def set_view_model(self, view_model):
        """設置視圖模型用於設備操作
        
        Args:
            view_model: DeviceManagerViewModel 實例
        """
        self.view_model = view_model
        
        # 連接視圖模型的信號
        self.view_model.device_connected.connect(self._on_device_connected_result)
        logger.debug("DeviceConnectionDialog: view model signals connected")

    @Slot(str, bool, str)
    def _on_device_connected_result(self, device_id, success, message):
        """處理來自視圖模型的設備連接結果
        
        Args:
            device_id: 設備ID
            success: 連接是否成功
            message: 連接結果消息
        """
        # 重新啟用連接按鈕
        self.ui_widget.push_button_connect.setEnabled(True)
        self.ui_widget.push_button_connect.setText("Connect")
        
        if success:
            # 連接成功
            logger.info(f"Successfully connected to device {device_id}")
            
            # 從設備ID解析信息
            parts = device_id.split('_')
            device_type = parts[0] if len(parts) > 0 else "serial"
            address = parts[1] if len(parts) > 1 else device_id
            
            # 獲取連接參數
            port = self.ui_widget.combo_box_port.currentText()
            baudrate = self.ui_widget.combo_box_baudrate.currentText()
            latency = self.ui_widget.combo_box_latency.currentText()
            
            # 創建設備信息返回給調用者
            self.connected_device = {
                'id': device_id,  # 新增: 保存設備ID供後續使用
                'name': f"Serial Device ({port})",
                'type': 'Serial',
                'address': port,
                'status': 'Connected',
                'details': {
                    'port': port,  # 新增: 保存端口信息
                    'baudrate': baudrate,
                    'latency': latency
                }
            }
            
            # 成功關閉對話框
            self.accept()
        else:
            # 連接失敗
            logger.error(f"Failed to connect to device: {message}")
            
            # 顯示錯誤對話框
            QMessageBox.critical(self, "Connection Error", message)


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