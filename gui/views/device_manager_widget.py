#!/usr/bin/env python
"""
Device Manager View

Handle the display of device manager UI and device management
"""

import os
import sys
from PySide6.QtWidgets import QWidget, QMessageBox, QTableWidgetItem, QVBoxLayout, QApplication
from PySide6.QtCore import QFile, Qt, QIODevice, Slot, QTimer
from PySide6.QtUiTools import QUiLoader
from gui.views.device_connection_dialog import DeviceConnectionDialog
from gui.view_models.device_manager_view_model import DeviceManagerViewModel
from util.logger import logger


class DeviceManagerWidget(QWidget):
    """Device manager widget class"""
    
    def __init__(self, parent=None):
        """Initialize device manager widget
        
        Args:
            parent: parent window
        """
        super().__init__(parent)
        
        # Initialize view model
        self.view_model = DeviceManagerViewModel()
        
        # Connect view model signals
        self.view_model.device_connected.connect(self._on_device_connected)
        self.view_model.device_disconnected.connect(self._on_device_disconnected)
        self.view_model.command_completed.connect(self._on_command_completed)
        
        # Initialize device list (in real application, this would be stored in a database or config)
        self.devices = []
        
        # Load UI
        self._load_ui_direct()
        
        # Connect events
        self._setup_connections()
        
        # Initial refresh
        self._refresh_device_list()
        
        # Setup periodic refresh
        self._setup_refresh_timer()
        
    def _setup_refresh_timer(self, interval_ms=5000):
        """Setup periodic refresh timer"""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_device_list)
        self.refresh_timer.start(interval_ms)
        
    def _load_ui_direct(self):
        """Load UI with a more direct approach"""
        try:
            # Get UI file path - support PyInstaller
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
                ui_file_path = os.path.join(base_path, 'gui', 'ui', 'device_manager_widget.ui')
            else:
                # Normal development environment
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ui_file_path = os.path.join(current_dir, "ui", "device_manager_widget.ui")
                
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
            self.setWindowTitle("Device Manager")
            self.resize(self.ui_widget.size())
            
            logger.debug("Device manager UI loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load UI: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load UI: {str(e)}")
            raise
    
    def _setup_connections(self):
        """Setup signal connections"""
        try:
            # Connect button events
            self.ui_widget.push_button_new_device.clicked.connect(self._on_new_device_clicked)
            self.ui_widget.push_button_disconnect.clicked.connect(self._on_disconnect_clicked)
            self.ui_widget.push_button_open_main_window.clicked.connect(self._on_open_main_window_clicked)
            self.ui_widget.push_button_refresh.clicked.connect(self._refresh_device_list)
            
            # Connect other events
            self.ui_widget.table_widget_devices.itemSelectionChanged.connect(self._on_device_selection_changed)
            self.ui_widget.combo_box_filter.currentIndexChanged.connect(self._refresh_device_list)
            
            logger.debug("Device manager signals connected")
        except Exception as e:
            logger.error(f"Failed to connect device manager signals: {str(e)}", exc_info=True)
    
    def _on_new_device_clicked(self):
        """Handle new device button click"""
        try:
            # Create and show device connection dialog
            dialog = DeviceConnectionDialog(self)
            
            # Check if dialog can accept the view model
            if hasattr(dialog, 'set_view_model'):
                dialog.set_view_model(self.view_model)
            
            result = dialog.exec()
            
            if result == DeviceConnectionDialog.Accepted and dialog.connected_device:
                # 設備已經在對話框中連接，只需添加到本地列表即可
                if not any(d.get('id') == dialog.connected_device.get('id') for d in self.devices):
                    # 只有在設備不在本地列表中時才添加
                    self.devices.append(dialog.connected_device)
                    logger.info(f"New device added: {dialog.connected_device['name']}")
                    self._refresh_device_list()
        except Exception as e:
            error_msg = f"Failed to open device connection dialog: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)
    
    def _on_disconnect_clicked(self):
        """Handle disconnect button click"""
        selected_row = self.ui_widget.table_widget_devices.currentRow()
        if selected_row < 0:
            return
            
        try:
            # Get device from the current row
            device = self._get_filtered_devices()[selected_row]
            
            # Get device ID
            device_id = device.get('id', None)
            if device_id:
                # Use view model to disconnect
                self.view_model.disconnect_device(device_id)
            else:
                # For devices not yet managed by view model
                logger.info(f"Disconnecting from device: {device['name']}")
                device['status'] = 'Disconnected'
                self._refresh_device_list()
                QMessageBox.information(self, "Success", f"Device {device['name']} disconnected successfully.")
                
        except Exception as e:
            error_msg = f"Failed to disconnect device: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)
    
    def _on_open_main_window_clicked(self):
        """Handle open main window button click"""
        selected_row = self.ui_widget.table_widget_devices.currentRow()
        if selected_row < 0:
            return
            
        try:
            # Get device from the current row
            device = self._get_filtered_devices()[selected_row]
            
            if device['status'] != 'Connected':
                QMessageBox.warning(self, "Warning", "Device is not connected. Please connect first.")
                return
            
            # Get device ID
            device_id = device.get('id', None)
            if not device_id:
                QMessageBox.warning(self, "Warning", "Device ID is missing. Cannot open main window.")
                return
                
            # Import MainWindowController and create a new instance for this device
            from gui.views.main_window import MainWindowController
            
            # Create a new main window controller for this device
            # If we don't already have a storage for device windows, create one
            if not hasattr(self, 'device_windows'):
                self.device_windows = {}
            
            # 檢查窗口是否已存在且仍然有效
            create_new_window = True
            if device_id in self.device_windows and self.device_windows[device_id]:
                controller = self.device_windows[device_id]
                # 檢查窗口是否仍然有效
                if controller.window.isVisible():
                    # 窗口存在且可見，激活它
                    controller.window.setWindowState(controller.window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
                    controller.window.activateWindow()
                    controller.window.raise_()
                    logger.info(f"Raised existing main window for device: {device_id}")
                    create_new_window = False
                else:
                    # 窗口不可見，可能已關閉但引用仍存在
                    logger.info(f"Window for device {device_id} exists but is not visible, creating new window")
            
            if create_new_window:
                # 創建新窗口
                controller = MainWindowController(device_id, self.view_model)
                # 連接窗口關閉信號
                controller.window_closed.connect(self._on_device_window_closed)
                self.device_windows[device_id] = controller
                controller.show()
                logger.info(f"Opened new main window for device: {device_id}")
            
        except Exception as e:
            error_msg = f"Failed to open main window: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)
    
    @Slot(str)
    def _on_device_window_closed(self, device_id):
        """處理設備窗口關閉事件"""
        logger.info(f"Device window closed: {device_id}")
        # 從設備窗口字典中移除引用
        if hasattr(self, 'device_windows') and device_id in self.device_windows:
            # 移除窗口引用
            del self.device_windows[device_id]
            logger.debug(f"Removed window reference for device: {device_id}")
    
    def _on_device_selection_changed(self):
        """Handle device selection change in the table"""
        # Enable/disable buttons based on selection
        has_selection = self.ui_widget.table_widget_devices.currentRow() >= 0
        
        self.ui_widget.push_button_disconnect.setEnabled(has_selection)
        self.ui_widget.push_button_open_main_window.setEnabled(has_selection)
        
        # In a real app, you might want to check the device status to determine if buttons should be enabled
        if has_selection:
            selected_row = self.ui_widget.table_widget_devices.currentRow()
            device = self._get_filtered_devices()[selected_row]
            
            # Only enable disconnect button if device is connected
            self.ui_widget.push_button_disconnect.setEnabled(device['status'] == 'Connected')
            
            # Only enable open main window button if device is connected
            self.ui_widget.push_button_open_main_window.setEnabled(device['status'] == 'Connected')
    
    def _get_filtered_devices(self):
        """Get devices filtered by the selected filter type"""
        filter_type = self.ui_widget.combo_box_filter.currentText()
        
        # 合併兩個來源的設備
        all_devices = self.devices.copy()
        
        # 添加來自 view model 的設備
        vm_device_ids = self.view_model.get_connected_devices()
        for device_id in vm_device_ids:
            # 檢查設備是否已存在
            if not any(d.get('id') == device_id for d in all_devices):
                # 為視圖模型設備創建新條目
                is_connected = self.view_model.is_device_connected(device_id)
                
                # 從設備ID中提取信息
                parts = device_id.split('_')
                device_type = parts[0].capitalize() if len(parts) > 0 else 'Serial'
                device_address = parts[1] if len(parts) > 1 else device_id
                
                all_devices.append({
                    'id': device_id,
                    'name': f"{device_type} Device ({device_address})",
                    'type': device_type,
                    'address': device_address,
                    'status': 'Connected' if is_connected else 'Disconnected'
                })
        
        if filter_type == "All Devices":
            return all_devices
        else:
            return [device for device in all_devices if device['type'] == filter_type]
    
    def _refresh_device_list(self):
        """Refresh the device list in the table"""
        # Clear the table
        self.ui_widget.table_widget_devices.setRowCount(0)
        
        # Get filtered devices
        filtered_devices = self._get_filtered_devices()
        
        # Add devices to the table
        for row, device in enumerate(filtered_devices):
            self.ui_widget.table_widget_devices.insertRow(row)
            
            # Set data for each column
            self.ui_widget.table_widget_devices.setItem(row, 0, QTableWidgetItem(device['name']))
            self.ui_widget.table_widget_devices.setItem(row, 1, QTableWidgetItem(device['type']))
            self.ui_widget.table_widget_devices.setItem(row, 2, QTableWidgetItem(device['address']))
            
            # Create status item with color based on status
            status_item = QTableWidgetItem(device['status'])
            if device['status'] == 'Connected':
                status_item.setForeground(Qt.green)
            elif device['status'] == 'Disconnected':
                status_item.setForeground(Qt.red)
            elif device['status'] == 'Error':
                status_item.setForeground(Qt.red)
            
            self.ui_widget.table_widget_devices.setItem(row, 3, status_item)
        
        # Resize columns to content
        self.ui_widget.table_widget_devices.resizeColumnsToContents()
        
        # Update button states
        self._on_device_selection_changed()
    
    @Slot(str, bool, str)
    def _on_device_connected(self, device_id, success, message):
        """Handle device connection event from view model"""
        if success:
            logger.info(f"Device connected: {device_id}")
            # Refresh device list to show the new device
            self._refresh_device_list()
            # Optionally show a notification
            # QMessageBox.information(self, "Connection Success", message)
        else:
            logger.error(f"Device connection failed: {device_id} - {message}")
    
    @Slot(str, bool, str)
    def _on_device_disconnected(self, device_id, success, message):
        """Handle device disconnection event from view model"""
        if success:
            logger.info(f"Device disconnected: {device_id}")
            # Remove device from local list if it exists
            self.devices = [d for d in self.devices if d.get('id') != device_id]
            # Refresh device list
            self._refresh_device_list()
        else:
            logger.error(f"Device disconnection failed: {device_id} - {message}")
            QMessageBox.warning(self, "Disconnection Failed", message)
    
    @Slot(str, str, str)
    def _on_command_completed(self, device_id, command, response):
        """Handle command completed event from view model"""
        logger.info(f"Command completed for device {device_id}")
        logger.debug(f"Command: {command}")
        logger.debug(f"Response: {response}")
        # 在實際應用中，您可能會更新控制台視圖來顯示響應
    
    def closeEvent(self, event):
        """Handle close event for window"""
        try:
            # 停止刷新計時器
            if hasattr(self, 'refresh_timer'):
                self.refresh_timer.stop()
            
            # 清理資源並斷開所有設備
            self.view_model.cleanup_resources()
            
            logger.info("Device manager resources cleaned up")
            event.accept()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            event.accept()  # 仍然接受事件以關閉窗口


# 如果直接運行此文件，則創建應用並顯示窗口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeviceManagerWidget()
    window.show()
    sys.exit(app.exec()) 