#!/usr/bin/env python
"""
Device Manager View

Handle the display of device manager UI and device management
"""

import os
import sys
from PySide6.QtWidgets import QWidget, QMessageBox, QTableWidgetItem, QVBoxLayout
from PySide6.QtCore import QFile, Qt, QIODevice
from PySide6.QtUiTools import QUiLoader
from gui.views.device_connection import DeviceConnectionDialog
from util.logger import logger


class DeviceManagerWidget(QWidget):
    """Device manager widget class"""
    
    def __init__(self, parent=None):
        """Initialize device manager widget
        
        Args:
            parent: parent window
        """
        super().__init__(parent)
        
        # Initialize device list (in real application, this would be stored in a database or config)
        self.devices = []
        
        # Load UI
        self._load_ui_direct()
        
        # Connect events
        self._setup_connections()
        
        # Initial refresh
        self._refresh_device_list()
        
    def _load_ui_direct(self):
        """Load UI with a more direct approach"""
        try:
            # Get UI file path - support PyInstaller
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
                ui_file_path = os.path.join(base_path, 'gui', 'ui', 'device_manager.ui')
            else:
                # Normal development environment
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ui_file_path = os.path.join(current_dir, "ui", "device_manager.ui")
                
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
            self.ui_widget.push_button_open_console.clicked.connect(self._on_open_console_clicked)
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
            result = dialog.exec()
            
            if result == DeviceConnectionDialog.Accepted and dialog.connected_device:
                # Add the new device to our list
                self.devices.append(dialog.connected_device)
                logger.info(f"New device added: {dialog.connected_device['name']}")
                
                # Refresh the device list
                self._refresh_device_list()
        except Exception as e:
            error_msg = f"Failed to open device connection dialog: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)
    
    def _on_disconnect_clicked(self):
        """Handle disconnect button click"""
        # Get selected row
        selected_row = self.ui_widget.table_widget_devices.currentRow()
        if selected_row < 0:
            return
            
        try:
            # Get device from the current row
            device = self._get_filtered_devices()[selected_row]
            
            # In a real application, you would disconnect from the device here
            logger.info(f"Disconnecting from device: {device['name']}")
            
            # Update device status
            device['status'] = 'Disconnected'
            
            # Refresh the device list
            self._refresh_device_list()
            
            # Show success message
            QMessageBox.information(self, "Success", f"Device {device['name']} disconnected successfully.")
        except Exception as e:
            error_msg = f"Failed to disconnect device: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)
    
    def _on_open_console_clicked(self):
        """Handle open console button click"""
        # Get selected row
        selected_row = self.ui_widget.table_widget_devices.currentRow()
        if selected_row < 0:
            return
            
        try:
            # Get device from the current row
            device = self._get_filtered_devices()[selected_row]
            
            if device['status'] != 'Connected':
                QMessageBox.warning(self, "Warning", "Device is not connected. Please connect first.")
                return
                
            # In a real application, you would open the console for the selected device
            logger.info(f"Opening console for device: {device['name']}")
            
            # Show a message for now (in a real app, you would open the console window)
            QMessageBox.information(self, "Console", f"Opening console for {device['name']}...")
            
        except Exception as e:
            error_msg = f"Failed to open console: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)
    
    def _on_device_selection_changed(self):
        """Handle device selection change in the table"""
        # Enable/disable buttons based on selection
        has_selection = self.ui_widget.table_widget_devices.currentRow() >= 0
        
        self.ui_widget.push_button_disconnect.setEnabled(has_selection)
        self.ui_widget.push_button_open_console.setEnabled(has_selection)
        
        # In a real app, you might want to check the device status to determine if buttons should be enabled
        if has_selection:
            selected_row = self.ui_widget.table_widget_devices.currentRow()
            device = self._get_filtered_devices()[selected_row]
            
            # Only enable disconnect button if device is connected
            self.ui_widget.push_button_disconnect.setEnabled(device['status'] == 'Connected')
            
            # Only enable open console button if device is connected
            self.ui_widget.push_button_open_console.setEnabled(device['status'] == 'Connected')
    
    def _get_filtered_devices(self):
        """Get devices filtered by the selected filter type
        
        Returns:
            filtered list of devices
        """
        filter_type = self.ui_widget.combo_box_filter.currentText()
        
        if filter_type == "All Devices":
            return self.devices
        else:
            return [device for device in self.devices if device['type'] == filter_type]
    
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


# For testing
if __name__ == "__main__":
    # Test the device manager widget
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = DeviceManagerWidget()
    widget.show()
    sys.exit(app.exec()) 