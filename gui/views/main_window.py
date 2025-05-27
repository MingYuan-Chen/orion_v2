from PySide6.QtWidgets import QMainWindow, QHeaderView, QTableWidgetItem, QInputDialog, QLineEdit
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QComboBox, QTabWidget
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject, QEvent
from PySide6.QtUiTools import QUiLoader
from typing import Dict, Optional, List
import datetime
from util.logger import logger
from PySide6.QtGui import QColor, QIcon, QFont
import os
import sys
import csv
from PySide6.QtCore import QFile
from core.services.hardware_test_manager import HardwareTestManagerService
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QSizePolicy, QMessageBox, QFrame, QSpacerItem, QGroupBox

from gui.views.test_manager import TestManagerView
from gui.widgets.test_container import TestContainer
from gui.views.system_info_manager import SystemInfoManagerView
from gui.views.log_manager import LogManagerView
from gui.views.auto_diagnostic_view import AutoDiagnosticView
from gui.views.hw_sw_config_manager import HWSWConfigManager
from gui.views.firmware_os_manager import FirmwareOSManager


class DarkEditDialog(QDialog):
    """Custom dark theme edit dialog"""
    
    def __init__(self, parent=None, title="Edit", label_text="Enter value:", initial_text=""):
        super().__init__(parent)
        
        # Set window properties
        self.setWindowTitle(title)
        self.resize(350, 120)
        
        # Set dark theme style
        self.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                color: white;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #3E3E3E;
                color: #4FC3F7;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
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
        """)
        
        # Create layout
        main_layout = QVBoxLayout(self)
        
        # Add label with bold font
        self.label = QLabel(label_text)
        font = self.label.font()
        font.setBold(True)
        self.label.setFont(font)
        main_layout.addWidget(self.label)
        
        # Add line edit
        self.line_edit = QLineEdit(initial_text)
        self.line_edit.selectAll()  # Select all text for easy editing
        main_layout.addWidget(self.line_edit)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        # Add space to push buttons to the right
        button_layout.addStretch()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)  # Make it the default button (Enter key)
        button_layout.addWidget(self.ok_button)
        
        main_layout.addLayout(button_layout)
        
        # Set focus to the line edit
        self.line_edit.setFocus()
    
    def get_text(self):
        """Get the entered text"""
        return self.line_edit.text()

class MainWindowController(QObject):
    """
    Controller class for managing device monitoring main window
    Each device will create a separate instance
    """
    # Add window closed signal
    window_closed = Signal(str)  # Send device ID
    
    def __init__(self, device_id, view_model):
        """
        Initialize main window controller
        
        Args:
            device_id: device ID
            view_model: DeviceManagerViewModel instance
        """
        # Call QObject initialization
        super().__init__()
        
        # Save device ID and view model
        self.device_id = device_id
        self.view_model = view_model
        
        # Add update status flag
        self.is_updating = False
        
        # add current tab index
        self.current_tab_index = -1
        
        # Add logged commands set to avoid duplicate logging
        self.logged_commands = set()
        
        # Ensure view_model has system_info_service
        if not hasattr(self.view_model, 'system_info_service') and hasattr(self.view_model, '_serial_worker'):
            from core.services.system_info import SystemInfoService
            self.view_model.system_info_service = SystemInfoService(self.view_model._serial_worker)
        
        # Load UI
        try:
            # Get UI file path - support PyInstaller
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
                ui_file_path = os.path.join(base_path, 'gui', 'ui', 'main_window.ui')
                icon_path = os.path.join(base_path, 'resources', 'icons', 'header.ico')
            else:
                # Normal development environment
                current_dir = os.path.dirname(os.path.abspath(__file__))
                gui_dir = os.path.dirname(current_dir)
                ui_file_path = os.path.join(gui_dir, "ui", "main_window.ui")
                
                # Get icon path - go up two levels from gui/views
                base_dir = os.path.dirname(gui_dir)
                icon_path = os.path.join(base_dir, "resources", "icons", "header.ico")
            
            logger.debug(f"Loading main window UI from: {ui_file_path}")
            
            # Load UI file
            ui_file = QFile(ui_file_path)
            if not ui_file.open(QFile.ReadOnly):
                error_msg = f"Cannot open {ui_file_path}: {ui_file.errorString()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Load UI using QUiLoader
            loader = QUiLoader()
            self.window = loader.load(ui_file)
            ui_file.close()
            
            if not self.window:
                error_msg = f"Failed to load UI file: {loader.errorString()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Ensure the window can be resized
            self.window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.window.setMinimumSize(600, 500)  # set a reasonable minimum size
            self.window.setMaximumSize(16777215, 16777215)  # set the maximum size to a large value
            
            logger.debug(f"Main window UI loaded successfully for device {device_id}")
        except Exception as e:
            logger.error(f"Failed to load main window UI: {str(e)}")
            raise
        
        # create the waiting spinner widget
        from gui.widgets.waiting_spinner import WaitingSpinner
        self.waiting_spinner = WaitingSpinner(
            parent=self.window,
            disable_parent_when_spinning=False,
            radius=10,
            line_length=5,
            line_width=2,
            speed=1.5,
            color=QColor(0, 120, 215)  # use blue, match the system style
        )
        
        # Set window properties
        self._set_window_properties()
        
        # create the system info manager
        self.system_info_manager = SystemInfoManagerView(self.device_id, self.view_model.system_info_service)
        
        # create the HW/SW configuration manager
        self.hw_sw_config_manager = HWSWConfigManager()
        
        # create the firmware & OS manager
        self.firmware_os_manager = FirmwareOSManager()
        
        # create the log manager
        self.log_manager = LogManagerView(self.device_id)
        
        # Initialize system info view
        self._init_system_info_view()
        
        # Initialize HW/SW config view
        self._init_hw_sw_config_view()
        
        # Initialize firmware & OS view
        self._init_firmware_os_view()
        
        # Initialize dashboard scrolling
        self._init_dashboard_scrolling()
        
        # Initialize logs view
        self._init_logs_view()
        
        # Create hardware test manager
        self.hw_test_manager = HardwareTestManagerService(self.view_model._serial_worker)
        
        # Create the test manager view and auto diagnostic view
        self.test_manager = TestManagerView(self.device_id, self.hw_test_manager)
        self.auto_diagnostic_view = AutoDiagnosticView(self.device_id, self.hw_test_manager)
        
        # Connect signals and slots
        self._connect_signals()
        
        # Initialize auto diagnostic view
        self._init_functionality_test_ui()
        
        # Connect refresh button
        self.window.pushButton_refresh.clicked.connect(self._on_refresh_system_info)
        
        # Initialize display status as "Initializing"
        self._set_initializing_state()
        
        # Install event filter to capture window close event
        self.window.installEventFilter(self)
        
        # Connect edit button signals
        self.window.button_edit_model_name.clicked.connect(self._on_edit_model_name)
        self.window.button_edit_serial_number.clicked.connect(self._on_edit_serial_number)
        self.window.button_edit_battery_model.clicked.connect(self._on_edit_battery_model)
        self.window.button_edit_battery_serial.clicked.connect(self._on_edit_battery_serial)
        
        # connect the tab changed signal
        if hasattr(self.window, 'tabWidget'):
            self.window.tabWidget.currentChanged.connect(self._on_tab_changed)
        
        # unified test result storage
        self.unified_test_results = {
            "functionality": {},  # functionality test results
            "diagnostic": {}      # diagnostic test results
        }
        self.unified_test_progress = {
            "functionality": {},  # functionality test progress
            "diagnostic": {}      # diagnostic test progress
        }
        
        # Add step template storage to save the step definition for each test
        self.test_step_templates = {
            "functionality": {},  # functionality test step templates
            "diagnostic": {}      # diagnostic test step templates
        }
        
        # set the result recorders after TestManagerView and AutoDiagnosticView are created
        self.test_manager.set_result_recorders(
            lambda test_type, test_id, data: self.record_test_result(test_type, test_id, data),
            lambda test_type, test_id, data: self.record_test_progress(test_type, test_id, data)
        )

        self.auto_diagnostic_view.set_result_recorders(
            lambda test_type, test_id, data: self.record_test_result(test_type, test_id, data),
            lambda test_type, test_id, data: self.record_test_progress(test_type, test_id, data)
        )
        
        # Connect test started signal to save step templates
        self.hw_test_manager.test_started.connect(self._on_test_started)
    
    def eventFilter(self, obj, event):
        """Filter window events to capture close event"""
        if obj is self.window and event.type() == QEvent.Close:
            logger.info(f"Main window for device {self.device_id} is closing")
            # Stop update timer
            # self.update_timer.stop()
            # Emit window close signal
            self.window_closed.emit(self.device_id)
        return super().eventFilter(obj, event)
    
    def _init_system_info_view(self):
        """Initialize system info view settings"""
        # set the ui components of the system info manager
        system_ui_components = {
            "refresh_button": self.window.pushButton_refresh,
            "last_updated_label": self.window.label_last_updated,
            
            # System basic info
            "model_name": self.window.value_model_name,
            "serial_number": self.window.value_serial_number,
            "cpu": self.window.value_cpu,
            "memory": self.window.value_memory,
            "storage": self.window.value_storage,
            
            # Battery info
            "battery_model": self.window.value_battery_model,
            "battery_serial": self.window.value_battery_serial,
            "charge_progress": self.window.progressBar_charge,
            "charge": self.window.value_charge,
            "voltage": self.window.value_voltage,
            "current": self.window.value_current,
            "temperature": self.window.value_temperature,
        }
        
        # set the ui components
        self.system_info_manager.set_ui_components(system_ui_components)
        
        # Provide a reference to the controller for command logging
        self.system_info_manager.main_controller = self
        
        # set a function to add system log, directly write to the log manager
        # use anonymous function to wrap, ensure the log will not cause the switch to the system log tab
        self.system_info_manager.add_system_log = lambda level, message: self._add_system_log_without_tab_switch(level, message)
        
        # connect the signals of the system info manager
        # when updating, directly call the method to handle instead of using the signal, so that the tab switch can be controlled
        # when the update is completed, re-enable the UI controls
        self.system_info_manager.info_update_completed.connect(self._on_system_info_update_completed)
        
        # when the update is error, add the error log, and close the waiting icon
        self.system_info_manager.info_update_error.connect(self._on_system_info_update_error)
    
    def _init_hw_sw_config_view(self):
        """Initialize HW/SW configuration view"""
        # Get the table widget from the UI
        hw_sw_table = self.window.tableWidget_hw_sw_config
        
        # Set up the HW/SW config manager with the table widget and edit dialog
        self.hw_sw_config_manager.set_ui_components(hw_sw_table, DarkEditDialog)
        
        # Connect signals if needed
        self.hw_sw_config_manager.config_updated.connect(self._on_hw_sw_config_updated)
        
        logger.info("HW/SW configuration view initialized")
    
    def _init_firmware_os_view(self):
        """Initialize firmware & OS view"""
        # Set up the firmware & OS manager with the window and edit dialog
        self.firmware_os_manager.set_ui_components(self.window, DarkEditDialog)
        
        # Connect signals
        self.firmware_os_manager.info_updated.connect(self._on_firmware_os_updated)
        
        logger.info("Firmware & OS view initialized")
    
    def _init_dashboard_scrolling(self):
        """Initialize dashboard scrolling functionality"""
        try:
            # Check if scroll area already exists in the UI file
            if hasattr(self.window, 'scrollArea_dashboard'):
                logger.info("Scroll area already exists in UI file, configuring existing components")
                
                # Just configure the fixed heights for existing components
                system_overview = self.window.groupBox_system_overview
                if system_overview:
                    system_overview.setMinimumHeight(280)
                    system_overview.setMaximumHeight(280)
                    logger.debug("Set System Overview fixed height: 280px")
                
                # Find and configure HW Components
                hw_components = self.window.tableWidget_hw_sw_config
                if hw_components:
                    # Find the parent groupbox
                    hw_groupbox = hw_components.parent()
                    while hw_groupbox and not isinstance(hw_groupbox, QGroupBox):
                        hw_groupbox = hw_groupbox.parent()
                    
                    if hw_groupbox:
                        hw_groupbox.setMinimumHeight(400)
                        hw_groupbox.setMaximumHeight(400)
                        logger.debug("Set HW Components group fixed height: 400px")
                    
                    # Set the table to show all rows without internal scrolling
                    hw_components.setMinimumHeight(350)
                    hw_components.setMaximumHeight(350)
                    hw_components.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    logger.debug("Set HW Components table fixed height: 350px, no internal scrolling")
                
                # Find and configure Firmware & OS group
                firmware_os_groupbox = self.window.groupBox_firmware_os
                if firmware_os_groupbox:
                    firmware_os_groupbox.setMinimumHeight(200)
                    firmware_os_groupbox.setMaximumHeight(200)
                    logger.debug("Set Firmware & OS group fixed height: 200px")
                
                logger.info("Dashboard scrolling functionality configured successfully")
                return
            
            # If no scroll area exists, create one dynamically (fallback)
            logger.info("No scroll area found in UI file, creating dynamically")
            
            # Get the dashboard tab
            dashboard_tab = self.window.tab_dashboard
            
            # Get the existing layout
            existing_layout = dashboard_tab.layout()
            if not existing_layout:
                logger.warning("No existing layout found in dashboard tab")
                return
            
            # Create a scroll area
            scroll_area = QScrollArea(dashboard_tab)
            scroll_area.setFrameShape(QScrollArea.NoFrame)
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            # Create content widget for scroll area
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(10, 10, 10, 10)
            content_layout.setSpacing(10)
            
            # Move all existing widgets to the content layout
            while existing_layout.count():
                item = existing_layout.takeAt(0)
                if item.widget():
                    content_layout.addWidget(item.widget())
                elif item.layout():
                    content_layout.addLayout(item.layout())
                elif item.spacerItem():
                    content_layout.addItem(item.spacerItem())
            
            # Set fixed heights for groups
            system_overview = self.window.groupBox_system_overview
            if system_overview:
                system_overview.setMinimumHeight(280)
                system_overview.setMaximumHeight(280)
                logger.debug("Set System Overview fixed height: 280px")
            
            # Add a vertical spacer at the bottom to handle extra space
            spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
            content_layout.addItem(spacer)
            
            # Set the content widget to the scroll area
            scroll_area.setWidget(content_widget)
            
            # Remove the old layout and add the scroll area
            dashboard_tab.setLayout(None)
            new_layout = QVBoxLayout(dashboard_tab)
            new_layout.setContentsMargins(0, 0, 0, 0)
            new_layout.addWidget(scroll_area)
            
            logger.info("Dashboard scrolling functionality created dynamically")
            
        except Exception as e:
            logger.error(f"Error initializing dashboard scrolling: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _on_hw_sw_config_updated(self, component_id: str, field_type: str, new_value: str):
        """Handle HW/SW configuration update"""
        # Log the configuration change
        self.log_manager.add_log_entry(
            "INFO", 
            f"HW/SW Config updated - {component_id} {field_type}: {new_value}"
        )
        logger.info(f"HW/SW Config updated: {component_id} {field_type} = {new_value}")
    
    def _on_firmware_os_updated(self, field_name: str, new_value: str):
        """Handle firmware & OS information update"""
        # Log the firmware & OS change
        self.log_manager.add_log_entry(
            "INFO", 
            f"Firmware & OS updated - {field_name}: {new_value}"
        )
        logger.info(f"Firmware & OS updated: {field_name} = {new_value}")
    
    def _add_system_log_without_tab_switch(self, level, message):
        """Add system log without switching tabs"""
        # record the current tab
        current_tab = -1
        if hasattr(self.window, 'tabWidget'):
            current_tab = self.window.tabWidget.currentIndex()
            
        # add the log, but do not scroll to bottom to avoid activating the log tab
        self.log_manager.add_log_entry(level, message, scroll_to_bottom=False)
        
        # if updating and current tab is valid, restore to the previous tab
        if self.is_updating and current_tab >= 0 and hasattr(self.window, 'tabWidget'):
            self.window.tabWidget.setCurrentIndex(current_tab)
    
    def _on_system_info_update_completed(self):
        """Handle the event of system info update completed"""
        # restore the updating status flag
        self.is_updating = False
        
        # stop the waiting icon
        if hasattr(self, 'waiting_spinner'):
            self.waiting_spinner.stop()
        
        # enable all UI controls
        self.set_ui_controls_state(True)
        
        # add the completed log
        self.log_manager.add_log_entry("INFO", "System info update completed")
    
    def _on_system_info_update_error(self, error_message):
        """Handle the event of system info update error"""
        # restore the updating status flag
        self.is_updating = False
        
        # stop the waiting icon
        if hasattr(self, 'waiting_spinner'):
            self.waiting_spinner.stop()
        
        # enable all UI controls
        self.set_ui_controls_state(True)
        
        # add the error log
        self.log_manager.add_log_entry("ERROR", f"System info update error: {error_message}")
    
    def _init_logs_view(self):
        """Initialize logs view settings"""
        # Configure logs table
        logs_table = self.window.tableWidget_logs
        logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        logs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Message column stretch
        
        # Set column width
        logs_table.setColumnWidth(0, 180)  # Timestamp column
        logs_table.setColumnWidth(1, 80)   # Level column
        
        # Enable automatic row height adjustment to display full content
        logs_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Set table to automatically wrap text
        logs_table.setWordWrap(True)
        
        # set the ui components to the log manager
        self.log_manager.set_ui_components(
            self.window.tableWidget_logs,
            self.window.comboBox_log_level,
            self.window.comboBox_time_range,
            self.window.pushButton_clear_logs
        )
        
        # Connect command send button
        self.window.pushButton_send_command.clicked.connect(self._on_send_command)
        self.window.lineEdit_command.returnPressed.connect(self._on_send_command)
        
        # Connect logs refresh button
        self.window.pushButton_refresh_logs.clicked.connect(self._refresh_logs)
    
    def _filter_logs(self):
        """Filter logs based on selected level and time range"""
        # this method is already handled internally by LogManagerView, keep it for backward compatibility
        pass
    
    def _refresh_logs(self):
        """Refresh log data"""
        # In actual application, get latest logs from device
        logger.info(f"Refreshing logs for device: {self.device_id}")
        
        # For example, can send command to get logs
        self.view_model.send_command(self.device_id, "get_logs")
        
        # Can update logs in command_completed signal processing
    
    def _clear_logs(self):
        """Clear log table"""
        # delegate to the log manager to clear logs
        self.log_manager.clear_logs()
    
    def _on_send_command(self):
        """Process command sending"""
        command = self.window.lineEdit_command.text().strip()
        if not command:
            return
            
        logger.info(f"Sending command to device {self.device_id}: {command}")
        
        # Send command to device
        self.view_model.send_command(self.device_id, command)
        
        # Clear command input box
        self.window.lineEdit_command.clear()
        
        # Add command record to logs
        self.log_manager.add_log_entry("INFO", f"[Command] {command}")
        
        # mark the command as logged
        self.mark_command_as_logged(command)
    
    def _connect_signals(self):
        """Connect signals and slots"""
        # Connect command result signal from view model
        self.view_model.command_result.connect(self._on_command_completed)
        
        # connect the all tests completed signal of the test manager
        self.test_manager.all_tests_completed.connect(self._on_all_tests_completed)

    def _init_functionality_test_ui(self):
        """Initialize functionality test UI elements"""
        # Configure shared test steps table
        hw_test_table = self.window.tableWidget_hardware_test_steps
        hw_test_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        hw_test_table.horizontalHeader().setStretchLastSection(True)
        hw_test_table.setColumnWidth(0, 200)  # Step column
        hw_test_table.setColumnWidth(1, 80)   # Status column
        
        # Set table minimum height
        hw_test_table.verticalHeader().setDefaultSectionSize(30)  # Set row height to 30 pixels
        hw_test_table.setMinimumHeight(180)   # Set minimum height
        
        # get the functionality test tab
        tab_functionality = self.window.tab_functionality
        
        # set the background color of the tab
        tab_functionality.setStyleSheet("background-color: #1E1E1E;")
        
        # clear all the child widgets in the tab
        for child in tab_functionality.findChildren(QWidget):
            # skip the already processed UI components
            if child.objectName() in ["tableWidget_hardware_test_steps", "progressBar_hardware_test"]:
                continue
            # skip the button widgets
            if isinstance(child, QPushButton) and child in [self.window.button_test_all]:
                continue
            # only process the direct child widgets
            if child.parent() == tab_functionality:
                child.setVisible(False)
                child.deleteLater()
        
        # save the original layout reference
        original_layout = tab_functionality.layout()
        if original_layout:
            # remove all the elements in the existing layout (avoid duplicate addition)
            while original_layout.count():
                item = original_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
        else:
            # if there is no layout, create a new one
            original_layout = QVBoxLayout(tab_functionality)
            original_layout.setContentsMargins(5, 5, 5, 5)
        
        # create the scroll area
        scroll_area = QScrollArea(tab_functionality)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # set the scroll bar style
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1E1E1E;
                border: none;
            }
            QScrollBar:vertical {
                background: #333333;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # create the content container
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # set the background color of the content container
        content_widget.setStyleSheet("background-color: #1E1E1E;")
        
        # create the auto diagnostic element
        self.auto_diagnostic_widget = self.auto_diagnostic_view.create_widget()
        content_layout.addWidget(self.auto_diagnostic_widget)
        
        # set the auto diagnostic test items
        diagnostic_tests = {
            "diagnostic_cpu_name": "Check CPU Name",
            "diagnostic_cpu_processor": "Check CPU Processor",
            "diagnostic_emmc_size": "Check eMMC Size",
            "diagnostic_mac_address": "Check MAC Address",
            "diagnostic_memory_size": "Check Memory Size",
            "diagnostic_nor_flash_size": "Check NOR Flash Size",
            "diagnostic_pic_version": "Check PIC Version",
            "diagnostic_sync_time": "Check Sync Time",
            "diagnostic_set_get_rtc_time": "Check Set and Get RTC Time",
            "diagnostic_design_capacity": "Check Design Capacity",
            "diagnostic_design_voltage": "Check Design Voltage",
            "diagnostic_uboot_version": "Check U-Boot Version",
            "diagnostic_kernal_name": "Check Kernal Name",
            "diagnostic_panel_id_resolution": "Check Panel ID and Resolution",
            "diagnostic_wifi_bt": "Check Wifi and Bluetooth"
        }
        self.auto_diagnostic_view.setup_diagnostic_items(diagnostic_tests)
        
        # set the auto diagnostic log function
        self.auto_diagnostic_view.add_system_log = lambda level, message: self.log_manager.add_log_entry(level, message)
        
        # connect the auto diagnostic signal
        self.auto_diagnostic_view.all_diagnostics_completed.connect(self._on_all_diagnostics_completed)
        self.auto_diagnostic_view.export_report_requested.connect(self._export_results)
        
        # add the spacing
        spacer = QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Fixed)
        content_layout.addItem(spacer)
        
        # create the functionality test title element
        hw_title_widget = QWidget()
        hw_title_layout = QHBoxLayout(hw_title_widget)
        hw_title_layout.setContentsMargins(5, 5, 5, 5)
        
        # set the background color of the title area
        hw_title_widget.setStyleSheet("background-color: #1E1E1E;")
        
        hw_title = QLabel("Functionality Test")
        hw_title.setStyleSheet("font-weight: bold; color: #4FC3F7; font-size: 14px;")
        hw_title_layout.addWidget(hw_title)
        
        hw_title_layout.addStretch()
        
        # add the test all button
        if hasattr(self.window, 'button_test_all'):
            # if the button_test_all does not exist, create a new one
            if not self.window.button_test_all:
                self.window.button_test_all = QPushButton("Test All")
            
            # apply the style
            self.window.button_test_all.setStyleSheet("""
                QPushButton {
                    background-color: #0078D7;
                    color: white;
                    border: none;
                    padding: 4px 12px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1C97EA;
                }
            """)
            hw_title_layout.addWidget(self.window.button_test_all)
        else:
            # if there is no this attribute, create a new button
            self.window.button_test_all = QPushButton("Test All")
            self.window.button_test_all.setStyleSheet("""
                QPushButton {
                    background-color: #0078D7;
                    color: white;
                    border: none;
                    padding: 4px 12px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1C97EA;
                }
            """)
            hw_title_layout.addWidget(self.window.button_test_all)
        
        # create the abort button
        self.window.button_abort_test = QPushButton("Abort Test")
        self.window.button_abort_test.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #F44336;
            }
        """)
        hw_title_layout.addWidget(self.window.button_abort_test)
        
        # add the title to the layout
        content_layout.addWidget(hw_title_widget)
        
        # add the separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #333333;")
        separator.setMaximumHeight(1)
        content_layout.addWidget(separator)
        
        # create the test container
        test_container = TestContainer()
        
        # set the fixed height of the test container, to display more items
        item_height = 32  # the height of each test item
        visible_items = 5  # the number of items to display, same as Auto Diagnostic
        scroll_height = item_height * visible_items + 20  # add some extra space
        test_container.set_fixed_height(scroll_height)
        
        # create the test items
        test_container.add_test_group("functionality_audio", "Audio Test")
        test_container.add_test_group("functionality_backlight", "Backlight Test")
        test_container.add_test_group("functionality_battery", "Battery Test")
        test_container.add_test_group("functionality_camera", "Camera Test")
        test_container.add_test_group("functionality_charge", "Charge Test")
        test_container.add_test_group("functionality_eeprom", "EEPROM Test")
        test_container.add_test_group("functionality_emmc", "eMMC Test")
        test_container.add_test_group("functionality_lcd", "LCD Test")
        test_container.add_test_group("functionality_led", "LED Test")
        test_container.add_test_group("functionality_power_button", "Power Button Test")
        test_container.add_test_group("functionality_touch", "Touch Test")
        test_container.add_test_group("functionality_usb", "USB Test")
        
        # add the test container to the layout
        content_layout.addWidget(test_container)
        
        # add the spacing
        progress_spacer = QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Fixed)
        content_layout.addItem(progress_spacer)
        
        # add the test progress title
        progress_title = QLabel("Test Progress")
        progress_title.setStyleSheet("font-weight: bold; color: white; font-size: 13px; background-color: #1E1E1E;")
        content_layout.addWidget(progress_title)
        
        # add the test steps table
        content_layout.addWidget(hw_test_table)
        
        # set the background color of the table
        hw_test_table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                color: white;
                gridline-color: #333333;
                border: none;
            }
            QTableWidget::item {
                background-color: #252526;
            }
            QHeaderView::section {
                background-color: #252526;
                color: white;
                border: 1px solid #333333;
                padding: 4px;
            }
        """)
        
        # add the progress bar
        if hasattr(self.window, 'progressBar_hardware_test'):
            content_layout.addWidget(self.window.progressBar_hardware_test)
        
        # add the bottom spacing
        bottom_spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        content_layout.addItem(bottom_spacer)
        
        # set the content of the scroll area
        scroll_area.setWidget(content_widget)
        
        # add the scroll area to the original layout
        original_layout.addWidget(scroll_area)
        
        # ensure the entire tab page has the correct background color
        tab_functionality.update()
        
        # find and clear any unknown text labels at the bottom of the tab page (excluding known UI components)
        for label in tab_functionality.findChildren(QLabel):
            if label.parent() == tab_functionality:  # only process direct child labels
                # skip title and button UI components
                if label.text() in ["Functionality Test", "Test Progress", "Auto Diagnostic"]:
                    continue
                # only process labels without objectName or obviously redundant labels
                if not label.objectName() or label.objectName() == "":
                    label.setVisible(False)
                    label.deleteLater()
        
        # set the UI components
        self.test_manager.set_ui_components(
            test_container,
            self.window.button_test_all,
            self.window.tableWidget_hardware_test_steps,
            self.window.progressBar_hardware_test,
            self.window,
            self.window.button_abort_test
        )
        
        # set the log recorder
        self.test_manager.add_system_log = lambda level, message: self.log_manager.add_log_entry(level, message)
        
        # set the default hidden progress bar
        self.window.progressBar_hardware_test.setVisible(False)
        
        # set the result recorder
        self.test_manager.set_result_recorders(
            lambda test_type, test_id, data: self.record_test_result(test_type, test_id, data),
            lambda test_type, test_id, data: self.record_test_progress(test_type, test_id, data)
        )

        self.auto_diagnostic_view.set_result_recorders(
            lambda test_type, test_id, data: self.record_test_result(test_type, test_id, data),
            lambda test_type, test_id, data: self.record_test_progress(test_type, test_id, data)
        )
    
    def _set_initializing_state(self):
        """Set all system info display to initializing state"""
        # delegate to the system info manager to set the initializing state
        self.system_info_manager.set_initializing_state()

    def _on_refresh_system_info(self):
        """Handle refresh button click"""
        # record the current tab, but do not force switch back, allow the user to freely switch
        if hasattr(self.window, 'tabWidget'):
            self.current_tab_index = self.window.tabWidget.currentIndex()
            logger.debug(f"Current tab index: {self.current_tab_index} (Dashboard)")
        
        # set the updating status flag
        self.is_updating = True
        
        # add the log, but do not switch to the log tab
        self.log_manager.add_log_entry("INFO", f"Refreshing system info for {self.device_id}...")
        
        # position and show the waiting icon next to the refresh button
        if hasattr(self, 'waiting_spinner'):
            self.waiting_spinner.position_next_to(self.window.pushButton_refresh)
            self.waiting_spinner.start()
        
        # disable all controls, but keep the tab switch functionality available
        self.set_ui_controls_state_except_tabs(False)
        
        # execute the system info refresh
        self.system_info_manager.refresh_system_info()

    def _on_edit_model_name(self):
        """handle the edit model name button click"""
        if self.system_info_manager.edit_model_name():
            self.log_manager.add_log_entry("INFO", "Model name updated")

    def _on_edit_serial_number(self):
        """handle the edit serial number button click"""
        if self.system_info_manager.edit_serial_number():
            self.log_manager.add_log_entry("INFO", "Serial number updated")

    def _on_edit_battery_model(self):
        """handle the edit battery model button click"""
        if self.system_info_manager.edit_battery_model():
            self.log_manager.add_log_entry("INFO", "Battery model updated")

    def _on_edit_battery_serial(self):
        """handle the edit battery serial number button click"""
        if self.system_info_manager.edit_battery_serial():
            self.log_manager.add_log_entry("INFO", "Battery serial number updated")

    def _set_window_properties(self):
        """Set window properties, ensure it is recognized as part of the main application"""
        try:
            # Get application instance
            app = QApplication.instance()
            if not app:
                logger.warning("Unable to get QApplication instance")
                return
                
            # Get global application display name
            app_name = app.applicationDisplayName() or app.applicationName() or "VT Hydra System Monitor"
            
            # Use application icon
            if app.windowIcon() and not self.window.windowIcon():
                self.window.setWindowIcon(app.windowIcon())
                
            # Set window title to include application name
            title = f"{app_name} - Device {self.device_id} Monitoring"
            self.window.setWindowTitle(title)
            
            # Set window flags to ensure it is recognized as the main application window
            self.window.setWindowFlags(self.window.windowFlags() | Qt.Window)
            
            # ensure the window can be resized
            self.window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            # remove the fixed size constraint (if any)
            if self.window.minimumSize().width() == self.window.maximumSize().width() or \
               self.window.minimumSize().height() == self.window.maximumSize().height():
                # reset the minimum and maximum size
                self.window.setMinimumSize(600, 500)  # set a reasonable minimum size
                self.window.setMaximumSize(16777215, 16777215)  # set the maximum size to a large value
            
            # Set taskbar related properties on Windows
            if sys.platform == 'win32':
                try:
                    # we don't directly call Win32 API here
                    # let the system naturally associate the window - rely on the application identifier set earlier
                    pass
                except Exception as e:
                    logger.warning(f"Unable to set Windows window properties: {e}")
            
            logger.debug(f"Window properties set: {title}")
        except Exception as e:
            logger.warning(f"Error setting window properties: {e}")

    @Slot()
    def _on_all_tests_completed(self):
        """Handle the event of all tests completed"""
        self.log_manager.add_log_entry("INFO", "All functionality tests completed")
    
    def _export_results(self):
        """Export test results to a CSV file"""
        try:
            # set the flag to prevent repeated execution
            if hasattr(self, '_export_in_progress') and self._export_in_progress:
                return
            self._export_in_progress = True
            
            # set the file name
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"test_results_{self.device_id}_{timestamp}.csv"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self.window,
                "Export Test Results",
                default_filename,
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                self._export_in_progress = False
                return
                
            # get the test results and progress records from the unified storage
            test_results = self.unified_test_results.get("functionality", {})
            test_progress_records = self.unified_test_progress.get("functionality", {})
            diagnostic_results = self.unified_test_results.get("diagnostic", {})
            
            # Debug: Display the step template storage status
            logger.info(f"Export debug - Step templates stored:")
            for test_type, templates in self.test_step_templates.items():
                logger.info(f"  {test_type}: {list(templates.keys())}")
                for test_id, step_list in templates.items():
                    logger.info(f"    {test_id}: {len(step_list)} steps")
            
            # Debug: Display the progress record status
            logger.info(f"Export debug - Progress records:")
            for test_type, progress in self.unified_test_progress.items():
                logger.info(f"  {test_type}: {list(progress.keys())}")
            
            # check if there is data to export
            data_exported = False
            
            # write to the CSV file
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # write the title row
                writer.writerow(["Module", "Step", "Criteria", "Result", "Command", "Response", "Timestamp", "Duration (sec)"])
                
                # write the functionality test results
                # first process the tests with progress records
                processed_tests = set()
                for test_id, records in test_progress_records.items():
                    processed_tests.add(test_id)
                    
                    # determine the test type: if the test_id starts with diagnostic_, then get the step templates from diagnostic
                    test_type = "diagnostic" if test_id.startswith("diagnostic_") else "functionality"
                    step_templates = self.test_step_templates.get(test_type, {}).get(test_id, [])
                    logger.info(f"Processing test with progress records: {test_id}, progress records: {len(records)}, step templates: {len(step_templates)} (from {test_type})")
                    
                    # get the step details of the test
                    test_steps = []
                    if test_id in test_results:
                        test_steps = test_results[test_id].get("steps", [])
                    elif test_id in diagnostic_results:
                        test_steps = diagnostic_results[test_id].get("steps", [])
                    
                    # try to get the step details and execution status from the test worker
                    worker_steps = []
                    worker = None
                    if hasattr(self.hw_test_manager, 'test_workers'):
                        worker = self.hw_test_manager.test_workers.get(test_id)
                        if worker and hasattr(worker, 'steps'):
                            worker_steps = worker.steps
                    
                    # if there are step templates, export all steps with criteria based on the step templates
                    if step_templates:
                        logger.info(f"Using step templates to export {len(step_templates)} steps for {test_id}")
                        
                        for template_index, template in enumerate(step_templates):
                            try:
                                # export only the steps with criteria
                                step_criteria = template.get('criteria', '')
                                if not step_criteria:
                                    logger.debug(f"Skipping template step {template_index} for {test_id} - no criteria")
                                    continue
                                
                                # get the basic step information
                                step_desc = template.get('description', '')
                                step_command = template.get('command', '')
                                is_manual_step = template.get('manual_only', False)
                                
                                # initialize the result variables
                                step_message = "NOT_EXECUTED"
                                step_response = ""
                                step_time = "--:--:--"
                                
                                # try to get more detailed information from test_steps
                                for step in test_steps:
                                    if step.get('index') == template_index:
                                        # use the information from test_steps (these are the ones recorded during actual execution)
                                        test_step_message = step.get('message', '')
                                        logger.debug(f"Found test_step for {template_index}: message='{test_step_message}', response='{step.get('response', '')[:50]}...'")
                                        
                                        if test_step_message and test_step_message != "No command specified":
                                            step_message = test_step_message
                                            logger.debug(f"Using test_step message for {template_index}: '{step_message}'")
                                        elif test_step_message == "No command specified" and is_manual_step:
                                            # for manual steps, if it is "No command specified", check if there is an actual PASS/FAIL result
                                            # get the more accurate status from the worker
                                            if worker and template_index < len(worker_steps):
                                                worker_step = worker_steps[template_index]
                                                if hasattr(worker_step, 'passed') and worker_step.passed is not None:
                                                    step_message = "PASS" if worker_step.passed else "FAIL"
                                                    logger.debug(f"Using worker status for manual step {template_index}: '{step_message}'")
                                        
                                        if step.get('response'):
                                            step_response = step.get('response', step_response)
                                        if step.get('command'):
                                            step_command = step.get('command', step_command)
                                        if step.get('time'):
                                            step_time = step.get('time', step_time)
                                        break
                                
                                # if no suitable result is found in test_steps, then get it from the worker
                                if step_message == "NOT_EXECUTED" and worker and template_index < len(worker_steps):
                                    worker_step = worker_steps[template_index]
                                    if hasattr(worker_step, 'passed') and worker_step.passed is not None:
                                        step_message = "PASS" if worker_step.passed else "FAIL"
                                        if is_manual_step:
                                            step_response = f"Manual interaction step - {step_message} (verified by user)"
                                        logger.debug(f"Using worker as fallback for step {template_index}: '{step_message}'")
                                
                                # if it is still "No command specified" but this is a manual step and there is a worker result, then use the worker result
                                if step_message == "No command specified" and is_manual_step and worker and template_index < len(worker_steps):
                                    worker_step = worker_steps[template_index]
                                    if hasattr(worker_step, 'passed') and worker_step.passed is not None:
                                        step_message = "PASS" if worker_step.passed else "FAIL"
                                        step_response = f"Manual interaction step - {step_message} (verified by user)"
                                        logger.debug(f"Overriding 'No command specified' for manual step {template_index}: '{step_message}'")
                                
                                # process the response text, filter out the useless information
                                final_response = ""
                                if isinstance(step_response, str):
                                    # for manual_only steps, keep the original response
                                    is_manual_step = template.get('manual_only', False)
                                    if is_manual_step:
                                        final_response = step_response
                                    else:
                                        # for non-manual steps, filter the response
                                        for line in step_response.split("\n"):
                                            line_stripped = line.strip()
                                            if not line_stripped:
                                                continue
                                            # filter out the obvious command lines and control information
                                            if any(filter_str in line_stripped for filter_str in ["i2ctransfer", "grep", "............"]):
                                                continue
                                            # filter out the obvious command prompt lines
                                            # check if the line is a command prompt line (usually starts with #, $, or >)
                                            if (line_stripped.startswith("#") or line_stripped.startswith("$") or line_stripped.startswith(">") or
                                                line_stripped.endswith("#") or line_stripped.endswith("$") or line_stripped.endswith(">")):
                                                continue
                                            # filter out the empty command prompt lines (only contains prompt characters and spaces)
                                            if line_stripped in ["#", "$", ">", "# ", "$ ", "> "]:
                                                continue
                                            final_response += line + "\n"
                                
                                step_response = final_response.strip()
                                
                                # process the skipped steps
                                if isinstance(step_message, str) and "skip" in step_message.lower():
                                    step_message = "SKIPPED"
                                
                                # get the timestamp
                                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                # try to get the actual timestamp from the progress records
                                for record in records:
                                    if isinstance(record, dict) and record.get('current_step') == template_index + 1:
                                        timestamp = record.get('timestamp', timestamp)
                                        break
                                
                                # create the data row
                                row_data = [
                                    test_id,                    # module
                                    step_desc,                  # step
                                    step_criteria,              # criteria
                                    step_message,               # result
                                    step_command,               # command
                                    step_response,              # response
                                    timestamp,                  # timestamp
                                    step_time                   # duration
                                ]
                                
                                writer.writerow(row_data)
                                data_exported = True
                                logger.debug(f"Exported step from template: {step_desc} (result: {step_message})")
                                logger.info(f"Step {template_index} final export: '{step_desc}' -> Result: '{step_message}', Response: '{step_response[:50]}...'")
                                
                            except Exception as ex:
                                logger.warning(f"Error processing template step {template_index}: {str(ex)}")
                                continue
                    
                    else:
                        logger.info(f"No step templates found for {test_id}, using progress records only")
                        
                        # if there are no step templates, fall back to the original logic
                        for record in records:
                            try:
                                # ensure record is a dictionary and has current_step
                                if not isinstance(record, dict) or 'current_step' not in record:
                                    continue
                                    
                                # find the corresponding step information
                                current_step = record['current_step'] - 1  # convert to 0-based index
                                if current_step < 0:
                                    continue
                                
                                # get the step status, message and time from the test results
                                step_desc = ""
                                step_message = ""
                                step_command = ""
                                step_response = ""
                                step_time = "--:--:--"  # default time
                                step_criteria = ""
                                
                                # initialize the test_step variable
                                test_step = None
                                
                                # get the step information from the test results
                                for step in test_steps:
                                    if step.get('index') == current_step:
                                        step_message = step.get('message', '')
                                        step_desc = step.get('description', '')
                                        step_criteria = step.get('criteria', '')
                                        step_command = step.get('command', '')
                                        step_response = step.get('response', '')
                                        step_time = step.get('time', '--:--:--')
                                        break
                                
                                # try to get the step description from the test worker
                                if worker and hasattr(worker, 'steps') and len(worker.steps) > current_step:
                                    test_step = worker.steps[current_step]
                                    # get the step description
                                    if hasattr(test_step, 'description'):
                                        step_desc = test_step.description
                                    
                                    # only get the command when the test results do not have command
                                    if not step_command and hasattr(test_step, 'command'):
                                        step_command = test_step.command
                                    
                                    # only get the response when the test results do not have response
                                    if not step_response:
                                        # use the response property first, if not, use the result property
                                        if hasattr(test_step, 'response') and test_step.response:
                                            step_response = test_step.response
                                        elif hasattr(test_step, 'result') and test_step.result:
                                            step_response = test_step.result
                                            
                                    # get criteria if not set
                                    if not step_criteria and hasattr(test_step, 'criteria'):
                                        step_criteria = test_step.criteria
                                    
                                    # for manual_only steps, set the message and response based on the actual execution result
                                    if hasattr(test_step, 'manual_only') and test_step.manual_only:
                                        # set the message based on the passed status
                                        if hasattr(test_step, 'passed') and test_step.passed is not None:
                                            step_message = "PASS" if test_step.passed else "FAIL"
                                            if test_step.passed:
                                                step_response = "Manual interaction step - PASS (verified by user)"
                                            else:
                                                step_response = "Manual interaction step - FAIL (verified by user)"
                                        else:
                                            step_message = "NOT_EXECUTED"
                                            step_response = "Manual interaction step - no command executed"
                                
                                # Skip steps with empty criteria
                                if not step_criteria:
                                    logger.debug(f"Skipping step {current_step} for {test_id} - no criteria")
                                    continue
                                
                                # process the "No command specified" case - for manual steps, if there is an execution result, use it
                                if step_message == "No command specified" and test_step:
                                    if hasattr(test_step, 'manual_only') and test_step.manual_only:
                                        if hasattr(test_step, 'passed') and test_step.passed is not None:
                                            step_message = "PASS" if test_step.passed else "FAIL"
                                        else:
                                            step_message = "NOT_EXECUTED"
                                
                                # process the response text
                                final_response = ""
                                if isinstance(step_response, str):
                                    # for manual_only steps, keep the original response
                                    is_manual_step = template.get('manual_only', False)
                                    if is_manual_step:
                                        final_response = step_response
                                    else:
                                        # for non-manual steps, filter the response
                                        for line in step_response.split("\n"):
                                            line_stripped = line.strip()
                                            if not line_stripped:
                                                continue
                                            # filter out the obvious command lines and control information
                                            if any(filter_str in line_stripped for filter_str in ["i2ctransfer", "grep", "............"]):
                                                continue
                                            # filter out the obvious command prompt lines
                                            # check if the line is a command prompt line (usually starts with #, $, or >)
                                            if (line_stripped.startswith("#") or line_stripped.startswith("$") or line_stripped.startswith(">") or
                                                line_stripped.endswith("#") or line_stripped.endswith("$") or line_stripped.endswith(">")):
                                                continue
                                            # filter out the empty command prompt lines (only contains prompt characters and spaces)
                                            if line_stripped in ["#", "$", ">", "# ", "$ ", "> "]:
                                                continue
                                            final_response += line + "\n"
                                
                                step_response = final_response
                                if isinstance(step_message, str) and "skip" in step_message.lower():
                                    step_message = "SKIPPED"

                                # create the data row
                                row_data = [
                                    test_id,                                       # module
                                    step_desc,                                     # step
                                    step_criteria,                                 # criteria
                                    step_message,                                  # result
                                    step_command,                                  # command
                                    step_response,                                 # response
                                    record.get('timestamp', '--:--:--'),           # timestamp
                                    step_time                                      # duration
                                ]

                                writer.writerow(row_data)
                                data_exported = True
                                logger.debug(f"Exported step from progress records: {step_desc}")
                            except Exception as ex:
                                logger.warning(f"Error processing test record: {str(ex)}")
                                continue
                
                # process the tests without progress records but with step templates - skip this part, only export the executed tests
                # comment out this part of the code, because the user only wants to export the executed modules
                
                # if the step templates are empty, try to get the step information directly from test_workers - also skip this part
                # comment out this part of the code, because the user only wants to export the executed modules
            
            # write the diagnostic test results
            for test_id, result_data in diagnostic_results.items():
                try:
                    # get the step templates of the diagnostic test
                    step_templates = self.test_step_templates.get("diagnostic", {}).get(test_id, [])
                    logger.info(f"Processing diagnostic test: {test_id}, step templates: {len(step_templates)}")
                    
                    # get the step data of the diagnostic test
                    test_steps = result_data.get("steps", [])
                    
                    # if there are step templates, export all steps with criteria based on the step templates
                    if step_templates:
                        logger.info(f"Using step templates to export diagnostic {test_id}")
                        
                        for template_index, template in enumerate(step_templates):
                            try:
                                # export only the steps with criteria
                                step_criteria = template.get('criteria', '')
                                if not step_criteria:
                                    logger.debug(f"Skipping diagnostic template step {template_index} for {test_id} - no criteria")
                                    continue
                                
                                # get the basic step information
                                step_desc = template.get('description', 'Diagnostic Test')
                                step_command = template.get('command', '')
                                
                                # initialize the result variables
                                step_message = "NOT_EXECUTED"
                                step_response = ""
                                step_time = "--:--:--"
                                
                                # try to get the execution result from test_steps
                                for step in test_steps:
                                    if step.get('index') == template_index:
                                        step_message = step.get('message', 'NOT_EXECUTED')
                                        step_response = step.get('response', '')
                                        step_time = step.get('time', '--:--:--')
                                        if step.get('command'):
                                            step_command = step.get('command', step_command)
                                        break
                                
                                # process the response text, filter out the useless information
                                final_response = ""
                                if isinstance(step_response, str):
                                    for line in step_response.split("\n"):
                                        line_stripped = line.strip()
                                        if not line_stripped:
                                            continue
                                        # filter out the obvious command lines and control information
                                        if any(filter_str in line_stripped for filter_str in ["i2ctransfer", "grep", "............"]):
                                            continue
                                        # filter out the obvious command prompt lines
                                        # check if the line is a command prompt line (usually starts with #, $, or >)
                                        if (line_stripped.startswith("#") or line_stripped.startswith("$") or line_stripped.startswith(">") or
                                            line_stripped.endswith("#") or line_stripped.endswith("$") or line_stripped.endswith(">")):
                                            continue
                                        # filter out the empty command prompt lines (only contains prompt characters and spaces)
                                        if line_stripped in ["#", "$", ">", "# ", "$ ", "> "]:
                                            continue
                                        final_response += line + "\n"
                                
                                step_response = final_response.strip()
                                
                                # process the skipped steps
                                if isinstance(step_message, str) and "skip" in step_message.lower():
                                    step_message = "SKIPPED"
                                
                                # get the timestamp
                                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                # create the data row
                                row_data = [
                                    test_id,                    # module
                                    step_desc,                  # step
                                    step_criteria,              # criteria
                                    step_message,               # result
                                    step_command,               # command
                                    step_response,              # response
                                    timestamp,                  # timestamp
                                    step_time                   # duration
                                ]
                                
                                writer.writerow(row_data)
                                data_exported = True
                                logger.debug(f"Exported diagnostic step from template: {step_desc} (result: {step_message})")
                                
                            except Exception as ex:
                                logger.warning(f"Error processing diagnostic template step {template_index}: {str(ex)}")
                                continue
                    
                    # if there are no step templates, use the original logic
                    elif test_steps:
                        for step in test_steps:
                            step_desc = step.get("description", "Diagnostic Test")
                            step_message = step.get("message", "")
                            step_command = step.get("command", "")
                            step_response = step.get("response", "")
                            step_time = step.get("time", "--:--:--")
                            step_criteria = step.get("criteria", "")
                            
                            # Skip steps with empty criteria - diagnostic tests must have criteria to be valid
                            if not step_criteria:
                                logger.debug(f"Skipping diagnostic step {step.get('index', -1)} for {test_id} - no criteria")
                                continue
                            
                            # process the response text
                            final_response = ""
                            if isinstance(step_response, str):
                                for line in step_response.split("\n"):
                                    line_stripped = line.strip()
                                    if not line_stripped:
                                        continue
                                    # filter out the obvious command lines and control information
                                    if any(filter_str in line_stripped for filter_str in ["i2ctransfer", "grep", "............"]):
                                        continue
                                    # filter out the obvious command prompt lines
                                    # check if the line is a command prompt line (usually starts with #, $, or >)
                                    if (line_stripped.startswith("#") or line_stripped.startswith("$") or line_stripped.startswith(">") or
                                        line_stripped.endswith("#") or line_stripped.endswith("$") or line_stripped.endswith(">")):
                                        continue
                                    # filter out the empty command prompt lines (only contains prompt characters and spaces)
                                    if line_stripped in ["#", "$", ">", "# ", "$ ", "> "]:
                                        continue
                                    final_response += line + "\n"
                            else:
                                final_response = str(step_response)
                            
                            step_response = final_response
                            if isinstance(step_message, str) and "skip" in step_message.lower():
                                step_message = "SKIPPED"

                            # create the data row of the diagnostic step
                            row_data = [
                                test_id,                # module
                                step_desc,              # step
                                step_criteria,          # criteria
                                step_message,           # result
                                step_command,           # command
                                step_response,          # response
                                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # timestamp
                                step_time               # time
                            ]
                            
                            writer.writerow(row_data)
                            data_exported = True
                            logger.debug(f"Exported diagnostic step: {step_desc} (result: {step_message})")
                    else:
                        # if there is no step data, use the basic information
                        status = result_data.get("status", "")
                        time_str = result_data.get("time", "--:--:--")
                        details = result_data.get("details", {})
                        if not isinstance(details, dict):
                            details = {}
                            
                        message = details.get("message", "")
                        
                        # Skip this entry if there are no criteria or validation results
                        if not message or message.strip() == "":
                            logger.debug(f"Skipping diagnostic {test_id} - no message or validation results")
                            continue
                        
                        # create the data row of the diagnostic result
                        row_data = [
                            test_id,                # module
                            "Diagnostic Test",      # step
                            "",                     # criteria
                            f"{status}: {message}", # result
                            "",                     # command
                            "",                     # response
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # timestamp
                            time_str                # time
                        ]
                        
                        writer.writerow(row_data)
                        data_exported = True
                        logger.debug(f"Exported diagnostic basic info: {test_id} (status: {status})")
                except Exception as ex:
                    logger.warning(f"Error processing diagnostic result for {test_id}: {str(ex)}")
                    continue
            
            if data_exported:
                logger.info(f"Test results exported to: {file_path}")
            else:
                logger.warning(f"No data was exported to the CSV file")
            
            # clear all the test results
            self.clear_all_test_results()
            
            # also reset the related UI
            # reset the test steps table
            if hasattr(self.window, 'tableWidget_hardware_test_steps'):
                self.window.tableWidget_hardware_test_steps.setRowCount(0)
            
            # reset the progress bar
            if hasattr(self.window, 'progressBar_hardware_test'):
                self.window.progressBar_hardware_test.setValue(0)
                self.window.progressBar_hardware_test.setVisible(False)
            
            # add the log of clearing the test records
            self.log_manager.add_log_entry("INFO", "Test and diagnostic records were cleared after exporting")
            
        except Exception as e:
            error_msg = f"Error exporting test results: {str(e)}"
            logger.error(error_msg)
            self.log_manager.add_log_entry("ERROR", error_msg)
        finally:
            # reset the flag
            self._export_in_progress = False

    @Slot(str, str, str)
    def _on_command_completed(self, device_id: str, command: str, response: str):
        """
        Handle command completed event
        
        Args:
            device_id: Device ID
            command: Command sent
            response: Command response
        """
        # Only process commands for this device
        if device_id != self.device_id:
            return
            
        # Log command and response - check if it is a test command
        # NOTE: this is a workaround to avoid logging the command and response for the test commands
        if not command.startswith("get_logs"):
            # check if the command has been logged
            if command not in self.logged_commands:
                self.log_manager.add_log_entry("INFO", f"[Command] {command}")
            # log the response in any case
            self.log_manager.add_log_entry("DEBUG", f"[Response] {response}")
            # remove the command from the tracking set
            self.logged_commands.discard(command)
        
        # Process response based on command
        if command.startswith("get_logs"):
            self._process_logs_response(response)
    
    def _update_dashboard(self):
        """Update dashboard information"""
        # delegate to the system info manager to refresh the system info
        self.system_info_manager.refresh_system_info()
    
    def _process_logs_response(self, response):
        """Process logs response"""
        # delegate to the log manager to process the logs response
        self.log_manager.process_logs_response(response)
    
    def show(self):
        """Show window and trigger system info update"""
        # Check window properties again before showing, ensure it's part of the main application
        self._set_window_properties()
        
        # ensure the window can be resized
        from PySide6.QtCore import Qt
        self.window.setWindowFlags(
            self.window.windowFlags() | 
            Qt.Window | 
            Qt.WindowMinMaxButtonsHint | 
            Qt.WindowCloseButtonHint
        )
        self.window.setAttribute(Qt.WA_DeleteOnClose, False)  # prevent the window from being deleted when closed
        
        # show the window
        self.window.show()
        
        # ensure the window is raised and activated
        self.window.raise_()
        self.window.activateWindow()
    
    def close(self):
        """Close the main window and cleanup resources"""
        try:
            logger.info(f"Closing main window for device {self.device_id}")
            
            # stop the waiting icon
            if hasattr(self, 'waiting_spinner') and self.waiting_spinner:
                self.waiting_spinner.stop()
                self.waiting_spinner = None
            
            # Clean up hardware test manager
            if self.hw_test_manager:
                logger.debug("Cleaning up hardware test manager")
                # Stop any running tests
                self.hw_test_manager.stop_current_test()
                if hasattr(self.hw_test_manager, 'cleanup'):
                    self.hw_test_manager.cleanup()
            
            # Clean up test manager
            if self.test_manager:
                logger.debug("Cleaning up test manager")
                self.test_manager.cleanup()
                self.test_manager = None
            
            # Clean up system info manager
            if self.system_info_manager:
                logger.debug("Cleaning up system info manager")
                # Disconnect signals
                try:
                    self.system_info_manager.info_update_completed.disconnect()
                    self.system_info_manager.info_update_error.disconnect()
                except Exception:
                    # Signals may already be disconnected
                    pass
                
                if hasattr(self.system_info_manager, 'cleanup'):
                    self.system_info_manager.cleanup()
                self.system_info_manager = None
            
            # Clean up HW/SW config manager
            if hasattr(self, 'hw_sw_config_manager') and self.hw_sw_config_manager:
                logger.debug("Cleaning up HW/SW config manager")
                try:
                    self.hw_sw_config_manager.config_updated.disconnect()
                except Exception:
                    pass
                self.hw_sw_config_manager = None
            
            # Clean up firmware & OS manager
            if hasattr(self, 'firmware_os_manager') and self.firmware_os_manager:
                logger.debug("Cleaning up firmware & OS manager")
                try:
                    self.firmware_os_manager.info_updated.disconnect()
                except Exception:
                    pass
                self.firmware_os_manager = None
            
            # Clean up log manager
            if self.log_manager:
                logger.debug("Cleaning up log manager")
                if hasattr(self.log_manager, 'cleanup'):
                    self.log_manager.cleanup()
                self.log_manager = None
            
            # Clean up auto diagnostic view
            if self.auto_diagnostic_view:
                logger.debug("Cleaning up auto diagnostic view")
                self.auto_diagnostic_view.cleanup()
                self.auto_diagnostic_view = None
            
            # Clean up the view model
            if hasattr(self, 'view_model') and self.view_model and hasattr(self.view_model, 'cleanup'):
                logger.debug("Cleaning up view model")
                self.view_model.cleanup()
            
            # Disconnect signals
            try:
                # Disconnect view model signals
                if hasattr(self, 'view_model') and self.view_model:
                    try:
                        self.view_model.command_result.disconnect(self._on_command_completed)
                    except Exception:
                        pass  # If already disconnected, ignore the error
                
                # Disconnect test manager signals
                if hasattr(self, 'test_manager'):
                    try:
                        self.test_manager.all_tests_completed.disconnect(self._on_all_tests_completed)
                    except Exception:
                        pass  # Ignore error of already disconnected signal
            except Exception as e:
                logger.error(f"Error disconnecting signals: {e}")
            
            # Remove event filter
            if hasattr(self, 'window') and self.window:
                self.window.removeEventFilter(self)
            
            # Close the window
            if self.window:
                logger.debug("Closing the main window")
                self.window.close()
                self.window = None
            
            # Emit window closed signal
            self.window_closed.emit(self.device_id)
            
            logger.info(f"Main window resources cleaned up for device: {self.device_id}")
            
        except Exception as e:
            logger.error(f"Error during main window cleanup: {str(e)}")
            # Still try to close the window even if there was an error
            if self.window:
                self.window.close()
                self.window = None

    def set_ui_controls_state(self, enabled=True, exclude_widgets=None):
        """
        General UI control enable/disable method
        
        Args:
            enabled (bool): Whether to enable the controls
            exclude_widgets (list): List of widgets to exclude from the enable/disable operation
        """
        if exclude_widgets is None:
            exclude_widgets = []
        
        # handle the buttons
        for button in self.window.findChildren(QPushButton):
            if button not in exclude_widgets:
                button.setEnabled(enabled)
        
        # handle the combo boxes
        for combobox in self.window.findChildren(QComboBox):
            if combobox not in exclude_widgets:
                combobox.setEnabled(enabled)
        
        # handle the line edits
        for lineedit in self.window.findChildren(QLineEdit):
            if lineedit not in exclude_widgets:
                lineedit.setEnabled(enabled)
        
        # handle the tab widgets
        for tabwidget in self.window.findChildren(QTabWidget):
            if tabwidget not in exclude_widgets:
                for i in range(tabwidget.count()):
                    tabwidget.setTabEnabled(i, enabled)
        
        # Ensure the system log page's send command button and input box state is correct
        if hasattr(self.window, 'pushButton_send_command'):
            self.window.pushButton_send_command.setEnabled(enabled)
        if hasattr(self.window, 'lineEdit_command'):
            self.window.lineEdit_command.setEnabled(enabled)
                
        # if there is a TestManager, handle the test container buttons
        if hasattr(self, 'test_manager') and hasattr(self.test_manager, 'test_container'):
            self.test_manager.set_test_buttons_enabled(enabled)
            
        # if there is an AutoDiagnosticView, handle its buttons
        if hasattr(self, 'auto_diagnostic_view'):
            self.auto_diagnostic_view.set_buttons_enabled(enabled)


    @Slot()
    def _on_all_diagnostics_completed(self):
        """handle the event of all diagnostics completed"""
        self.log_manager.add_log_entry("INFO", "All diagnostic tests completed")

    def _on_tab_changed(self, index):
        """Handle tab change event"""
        # only save the current tab index when not updating
        if not self.is_updating:
            self.current_tab_index = index
            logger.debug(f"Tab changed to index {index}")

    def set_ui_controls_state_except_tabs(self, enabled=True):
        """
        Set UI controls state, but keep the tabs available
        
        Args:
            enabled (bool): Whether to enable the controls
        """
        # exclude the tab widgets
        exclude_widgets = []
        if hasattr(self.window, 'tabWidget'):
            exclude_widgets.append(self.window.tabWidget)
        
        # call the original method, but exclude the tab widgets
        self.set_ui_controls_state(enabled, exclude_widgets)

    def record_test_result(self, test_type, test_id, result_data):
        """record the test results to the unified storage"""
        if test_type in self.unified_test_results:
            self.unified_test_results[test_type][test_id] = result_data

    def record_test_progress(self, test_type, test_id, progress_data):
        """record the test progress to the unified storage"""
        if test_type in self.unified_test_progress:
            if test_id not in self.unified_test_progress[test_type]:
                self.unified_test_progress[test_type][test_id] = []
            self.unified_test_progress[test_type][test_id].append(progress_data)

    def clear_all_test_results(self):
        """clear all the test results"""
        for test_type in self.unified_test_results:
            self.unified_test_results[test_type].clear()
            self.unified_test_progress[test_type].clear()
        
        # 清理步骤模板
        for test_type in self.test_step_templates:
            self.test_step_templates[test_type].clear()
        
        # notify the views to reset the UI
        if hasattr(self, 'test_manager'):
            self.test_manager.reset_ui()
        if hasattr(self, 'auto_diagnostic_view'):
            self.auto_diagnostic_view.reset_ui()

    def mark_command_as_logged(self, command):
        """
        將命令標記為已記錄，避免重複記錄
        
        Args:
            command: 命令字符串
        """
        self.logged_commands.add(command)
        # 设置一个定时器来清理过时的命令 (3分钟后)
        QTimer.singleShot(180000, lambda cmd=command: self.logged_commands.discard(cmd))

    @Slot(str)
    def _on_test_started(self, test_id: str):
        """Handle the event of test started, save step template information"""
        logger.info(f"Test started: {test_id}, saving step template")
        
        try:
            # 从hardware test manager获取当前active worker的步骤信息
            if hasattr(self.hw_test_manager, 'active_test_worker') and self.hw_test_manager.active_test_worker:
                worker = self.hw_test_manager.active_test_worker
                logger.info(f"Found active worker for {test_id}: {type(worker).__name__}")
                
                if hasattr(worker, 'steps') and worker.steps:
                    logger.info(f"Worker has {len(worker.steps)} steps")
                    
                    # 保存步骤模板信息
                    step_templates = []
                    for i, step in enumerate(worker.steps):
                        step_template = {
                            'index': i,
                            'description': getattr(step, 'description', ''),
                            'criteria': getattr(step, 'criteria', ''),
                            'command': getattr(step, 'command', ''),
                            'manual_only': getattr(step, 'manual_only', False),
                            'pre_condition': getattr(step, 'pre_condition', ''),
                            'post_check': getattr(step, 'post_check', ''),
                            'specification': getattr(step, 'specification', ''),
                        }
                        step_templates.append(step_template)
                        
                        # 记录每个步骤的详细信息
                        logger.debug(f"Step {i}: {step_template['description']} (criteria: {step_template['criteria']}, manual: {step_template['manual_only']})")
                    
                    # 确定测试类型
                    test_type = "functionality" if test_id.startswith("functionality_") else "diagnostic"
                    self.test_step_templates[test_type][test_id] = step_templates
                    
                    logger.info(f"Saved {len(step_templates)} step templates for {test_id}")
                    
                    # 额外验证：检查有多少步骤有criteria
                    steps_with_criteria = sum(1 for t in step_templates if t['criteria'])
                    logger.info(f"Steps with criteria: {steps_with_criteria}")
                    
                else:
                    logger.warning(f"No steps found in worker for {test_id}")
            else:
                logger.warning(f"No active worker found for {test_id}")
                
        except Exception as e:
            logger.error(f"Error saving step template for {test_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")