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
        
        # Initialize the re-entry flag
        self._is_closing = False
        
        # Initialize view model
        self.view_model = DeviceManagerViewModel()
        
        # Connect view model signals
        self.view_model.connection_result.connect(self._on_device_connected)
        self.view_model.disconnection_result.connect(self._on_device_disconnected)
        self.view_model.command_result.connect(self._on_command_completed)
        self.view_model.device_list_changed.connect(self._on_device_list_changed)
        
        # Load UI
        self._load_ui_direct()
        
        # Connect events
        self._setup_connections()
        
        # Initial refresh
        self._refresh_device_list()
        
        # Setup periodic refresh
        self._setup_refresh_timer()
        
        # Ensure this window is recognized as part of the main application
        self._set_window_properties()
        
        # Apply dark theme
        self._apply_dark_theme()
        
        # Connect application quit signal
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._on_app_quit)
        
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
                icon_path = os.path.join(base_path, 'resources', 'icons', 'header.ico')
            else:
                # Normal development environment
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ui_file_path = os.path.join(current_dir, "ui", "device_manager_widget.ui")
                
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
            self.setWindowTitle("Device Manager")
            self.resize(self.ui_widget.size())
            
            # Set application icon
            if os.path.exists(icon_path):
                from PySide6.QtGui import QIcon
                self.setWindowIcon(QIcon(icon_path))
                logger.debug("Application icon set successfully")
            else:
                logger.warning(f"Icon file not found: {icon_path}")
            
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
            
            # Execute dialog
            dialog.exec()
            
            # No need to manually manage device list
            # When device connection is successful, the view_model will automatically emit the device_list_changed signal
            
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
            
            # Check if window already exists and is still valid
            create_new_window = True
            if device_id in self.device_windows and self.device_windows[device_id]:
                controller = self.device_windows[device_id]
                # Check if window is still valid
                if controller.window.isVisible():
                    # Window exists and is visible, activate it
                    controller.window.setWindowState(controller.window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
                    controller.window.activateWindow()
                    controller.window.raise_()
                    logger.info(f"Raised existing main window for device: {device_id}")
                    create_new_window = False
                else:
                    # Window is not visible, possibly closed but reference still exists
                    logger.info(f"Window for device {device_id} exists but is not visible, creating new window")
            
            if create_new_window:
                # Create new window
                controller = MainWindowController(device_id, self.view_model)
                # Connect window closed signal
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
        """Handle device window closed event"""
        logger.info(f"Device window closed: {device_id}")
        # Remove reference from device window dictionary
        if hasattr(self, 'device_windows') and device_id in self.device_windows:
            # Remove window reference
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
        """Get devices filtered by selected filter type"""
        filter_type = self.ui_widget.combo_box_filter.currentText()
        
        # Get devices from view model
        all_devices = self.view_model.get_connected_devices()
        
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
            # No need to manually manage device list
            # The view will update through the _on_device_list_changed signal
        else:
            logger.error(f"Device disconnection failed: {device_id} - {message}")
            QMessageBox.warning(self, "Disconnection Failed", message)
    
    @Slot(str, str, str)
    def _on_command_completed(self, device_id, command, response):
        """Handle command completed event from view model"""
        logger.info(f"Command completed for device {device_id}")
        logger.debug(f"Command: {command}")
        logger.debug(f"Response: {response}")
        # In actual application, you may update the console view to display the response
    
    @Slot(list)
    def _on_device_list_changed(self, devices_list):
        """Handle device list change signal
        
        Args:
            devices_list: updated device list
        """
        logger.debug(f"Device list updated, {len(devices_list)} devices")
        self._refresh_device_list()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Prevent duplicate processing of close events
        if hasattr(self, '_is_closing') and self._is_closing:
            logger.debug("Close event is already being processed, ignore duplicate calls")
            event.accept()
            return
            
        # Set the closing flag
        self._is_closing = True
        
        logger.info("DeviceManagerWidget closeEvent triggered")
        
        # 1. Stop the auto-scan timer
        if hasattr(self, 'refresh_timer') and self.refresh_timer.isActive():
            self.refresh_timer.stop()
            logger.debug("Auto-scan timer stopped")
        
        # 2. Close all device windows
        if hasattr(self, 'device_windows') and self.device_windows:
            for device_id, controller in list(self.device_windows.items()):
                logger.info(f"Closing window for device: {device_id}")
                controller.close()
            
            # Wait a moment to ensure all windows are closed
            QTimer.singleShot(100, self._continue_close_event)
            
            # Delay accepting the close event
            event.ignore()
        else:
            # If there are no device windows, continue the close process directly
            self._continue_close_event()
            event.accept()
    
    def _continue_close_event(self):
        """Continue the close event process after device windows are closed"""
        # Prevent duplicate processing
        if not hasattr(self, '_is_closing') or not self._is_closing:
            logger.warning("Close process called improperly, exiting")
            return
            
        logger.info("Continuing device manager widget close process")
        
        # 3. Clear the device window dictionary
        if hasattr(self, 'device_windows'):
            self.device_windows.clear()
        
        # 4. Disconnect all signal connections
        try:
            # Disconnect view_model signals
            if hasattr(self, 'view_model') and self.view_model:
                try:
                    self.view_model.connection_result.disconnect(self._on_device_connected)
                    self.view_model.disconnection_result.disconnect(self._on_device_disconnected)
                    self.view_model.command_result.disconnect(self._on_command_completed)
                    self.view_model.device_list_changed.disconnect(self._on_device_list_changed)
                except Exception as e:
                    logger.warning(f"Error disconnecting view_model signals: {e}")
        except Exception as e:
            logger.warning(f"Error disconnecting signals: {e}")
        
        # 5. Clean up view_model resources
        if hasattr(self, 'view_model') and self.view_model:
            try:
                logger.info("Cleaning up view_model resources")
                self.view_model.cleanup()
                # Important: Clear the reference, avoid circular references
                self.view_model = None
            except Exception as e:
                logger.warning(f"Error cleaning up view_model: {e}")
        
        # 6. Clean up UI elements
        try:
            # Clear all tables
            if hasattr(self.ui_widget, 'table_widget_devices'):
                self.ui_widget.table_widget_devices.setRowCount(0)
                
            # Disable all buttons
            if hasattr(self.ui_widget, 'push_button_refresh'):
                self.ui_widget.push_button_refresh.setEnabled(False)
            if hasattr(self.ui_widget, 'push_button_new_device'):
                self.ui_widget.push_button_new_device.setEnabled(False)
            if hasattr(self.ui_widget, 'push_button_disconnect'):
                self.ui_widget.push_button_disconnect.setEnabled(False)
            if hasattr(self.ui_widget, 'push_button_open_main_window'):
                self.ui_widget.push_button_open_main_window.setEnabled(False)
                
        except Exception as e:
            logger.warning(f"Error during UI cleanup: {e}")
        
        # 7. Clean up Qt timers and events
        try:
            # Remove all timers
            for timer in self.findChildren(QTimer):
                if timer.isActive():
                    timer.stop()
                    logger.debug(f"Stopped timer: {timer}")
                    
            # Clean up event filters (if any)
            if hasattr(self, '_event_filter') and self._event_filter:
                QApplication.instance().removeEventFilter(self._event_filter)
                self._event_filter = None
                logger.debug("Removed event filter")
                
        except Exception as e:
            logger.warning(f"Error cleaning up Qt resources: {e}")
        
        logger.info("All DeviceManagerWidget resources have been cleaned up")
        
        # Remove the final close call, avoid infinite loop
        # If this is called from a timer callback, do not call close() again
        # if self.isVisible():
        #     self.close()
        
    def _final_cleanup(self):
        """Final cleanup after resources are released - Replaced by _continue_close_event"""
        logger.warning("_final_cleanup method is deprecated, please use _continue_close_event")

    def _on_app_quit(self):
        """Handle application quit event"""
        logger.info("Application is quitting, final cleanup")
        
        # Check if already in the closing or cleanup process
        if hasattr(self, '_is_closing') and self._is_closing:
            logger.info("Already in the closing process, skip application quit cleanup")
            return
        
        # Set the exit cleanup flag
        self._is_closing = True
        
        # Release the timer
        if hasattr(self, 'refresh_timer') and self.refresh_timer.isActive():
            self.refresh_timer.stop()
        
        # Check if view_model has been cleaned up
        # If view_model is None, it has been cleaned up
        if hasattr(self, 'view_model') and self.view_model is not None:
            try:
                # Avoid calling methods on deleted objects
                try:
                    # Try a simple operation to test object validity
                    self.view_model.blockSignals(True)
                    
                    # Object is valid, call cleanup
                    logger.info("Cleaning up view_model when quitting application")
                    self.view_model.cleanup()
                except RuntimeError as e:
                    # Object has been deleted, skip cleanup
                    if "C++ object" in str(e) and "deleted" in str(e):
                        logger.warning("View_model C++ object has been deleted, skip cleanup")
                    else:
                        # Other RuntimeError
                        logger.error(f"Error cleaning up view_model: {e}")
                except Exception as e:
                    logger.error(f"Unknown error cleaning up view_model: {e}")
                    
                # Clear the reference
                self.view_model = None
            except Exception as e:
                logger.error(f"Error cleaning up view_model when quitting application: {e}")
        
        logger.info("Application quit cleanup completed")

    def _set_window_properties(self):
        """Set window properties to ensure it's recognized as part of the main application"""
        try:
            # Get global application instance
            app = QApplication.instance()
            if app:
                # Use application icon
                if app.windowIcon():
                    self.setWindowIcon(app.windowIcon())
                
                # Set window title to include application name
                if app.applicationDisplayName():
                    self.setWindowTitle(f"{app.applicationDisplayName()}")
                else:
                    self.setWindowTitle("VT Hydra Device Manager")
                
                # Ensure this window is recognized as the main application window by Windows
                self.setWindowFlags(self.windowFlags() | Qt.Window)
                
                logger.debug("Main window properties set successfully")
        except Exception as e:
            logger.warning(f"Error setting main window properties: {e}")

    def _get_dark_style_sheet(self):
        """Return the dark style sheet"""
        return """
            QWidget {
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
            QTableWidget {
                background-color: #232323;
                alternate-background-color: #303030;
                color: white;
                gridline-color: #555555;
                border: 1px solid #555555;
                border-radius: 3px;
                selection-background-color: #0078D7;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #202020;
                color: white;
                padding: 5px;
                border: 1px solid #555555;
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
            QScrollBar:vertical {
                border: none;
                background-color: #2E2E2E;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #777777;
            }
            QScrollBar:horizontal {
                border: none;
                background-color: #2E2E2E;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #555555;
                min-width: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #777777;
            }
        """
    
    def _apply_dark_theme(self):
        """Apply dark theme to the widget"""
        # Set stylesheet
        self.setStyleSheet(self._get_dark_style_sheet())
        
        # Set window background
        self.setAutoFillBackground(True)
        self.ui_widget.setAutoFillBackground(True)


# If this file is run directly, create an application and display the window
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeviceManagerWidget()
    window.show()
    sys.exit(app.exec()) 