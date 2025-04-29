from PySide6.QtWidgets import QMainWindow, QHeaderView, QTableWidgetItem, QInputDialog, QLineEdit
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog
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
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout

# import TestManagerView
from gui.views.test_manager import TestManagerView


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
            
            logger.debug(f"Main window UI loaded successfully for device {device_id}")
        except Exception as e:
            logger.error(f"Failed to load main window UI: {str(e)}")
            raise
        
        # Set window properties
        self._set_window_properties()
        
        # Initialize logs view
        self._init_logs_view()
        
        # Create hardware test manager
        self.hw_test_manager = HardwareTestManagerService(self.view_model._serial_worker)
        
        # 创建测试管理器视图
        self.test_manager = TestManagerView(self.device_id, self.hw_test_manager)
        
        # Connect signals and slots
        self._connect_signals()
        
        # Initialize functionality test UI
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
    
    def eventFilter(self, obj, event):
        """Filter window events to capture close event"""
        if obj is self.window and event.type() == QEvent.Close:
            logger.info(f"Main window for device {self.device_id} is closing")
            # Stop update timer
            # self.update_timer.stop()
            # Emit window close signal
            self.window_closed.emit(self.device_id)
        return super().eventFilter(obj, event)
    
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
        
        # Connect command send button
        self.window.pushButton_send_command.clicked.connect(self._on_send_command)
        self.window.lineEdit_command.returnPressed.connect(self._on_send_command)
        
        # Connect logs filter
        self.window.comboBox_log_level.currentIndexChanged.connect(self._filter_logs)
        self.window.comboBox_time_range.currentIndexChanged.connect(self._filter_logs)
        
        # Connect refresh and clear buttons
        self.window.pushButton_refresh_logs.clicked.connect(self._refresh_logs)
        self.window.pushButton_clear_logs.clicked.connect(self._clear_logs)
    
    def _set_log_item_color(self, row, level):
        """Set log item color"""
        logs_table = self.window.tableWidget_logs
        color = Qt.white  # Default color
        
        # Set color based on level
        if level == "INFO":
            color = QColor("#3794FF")  # Blue
        elif level == "WARNING":
            color = QColor("#FFD700")  # Yellow
        elif level == "ERROR":
            color = QColor("#FF3333")  # Red
        elif level == "DEBUG":
            color = QColor("#888888")  # Gray
        
        # Set color for all cells in the row
        for col in range(logs_table.columnCount()):
            item = logs_table.item(row, col)
            if item:
                item.setForeground(color)
    
    def _filter_logs(self):
        """Filter logs based on selected level and time range"""
        logs_table = self.window.tableWidget_logs
        level_filter = self.window.comboBox_log_level.currentText()
        time_filter = self.window.comboBox_time_range.currentText()
        
        # Iterate through all rows
        for row in range(logs_table.rowCount()):
            item = logs_table.item(row, 1)  # Level column
            if not item:
                continue
                
            level = item.text()
            show_row = True
            
            # Apply level filter
            if level_filter != "All" and level != level_filter.upper():
                show_row = False
                
            # Apply time filter (in actual application, need to parse timestamp)
            # Here is just an example, actual operation needs to be based on real timestamp
            
            # Set row visibility
            logs_table.setRowHidden(row, not show_row)
    
    def _refresh_logs(self):
        """Refresh log data"""
        # In actual application, get latest logs from device
        logger.info(f"Refreshing logs for device: {self.device_id}")
        
        # For example, can send command to get logs
        self.view_model.send_command(self.device_id, "get_logs")
        
        # Can update logs in command_completed signal processing
    
    def _clear_logs(self):
        """Clear log table"""
        self.window.tableWidget_logs.setRowCount(0)
        logger.info(f"Cleared logs for device: {self.device_id}")
    
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
        self._add_log_entry("INFO", f"[Command] {command}")
    
    def _add_log_entry(self, level, message, timestamp=None):
        """Add new log entry"""
        logs_table = self.window.tableWidget_logs
        current_row_count = logs_table.rowCount()
        logs_table.setRowCount(current_row_count + 1)
        
        # Create timestamp
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Ensure level is uppercase
        level = level.upper()
        
        # Create and set items
        timestamp_item = QTableWidgetItem(timestamp)
        level_item = QTableWidgetItem(level)
        message_item = QTableWidgetItem(message)
        
        # Set message item alignment
        message_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        # Set items to table
        logs_table.setItem(current_row_count, 0, timestamp_item)
        logs_table.setItem(current_row_count, 1, level_item)
        logs_table.setItem(current_row_count, 2, message_item)
        
        # Adjust new row height
        logs_table.resizeRowToContents(current_row_count)
        
        # Set color
        self._set_log_item_color(current_row_count, level)
        
        # Scroll to latest item
        logs_table.scrollToBottom()
    
    def _connect_signals(self):
        """Connect signals and slots"""
        # Connect command result signal from view model
        self.view_model.command_result.connect(self._on_command_completed)
        
        # connect the all tests completed signal of the test manager
        self.test_manager.all_tests_completed.connect(self._on_all_tests_completed)
        
        # Add system info service signals
        if hasattr(self.view_model, 'system_info_service'):
            self.view_model.system_info_service.info_received.connect(self._on_system_info_received)
            self.view_model.system_info_service.info_error.connect(self._on_system_info_error)
        
        # connect the export result button
        if hasattr(self.window, 'button_export_result'):
            self.window.button_export_result.clicked.connect(self._export_test_results)
    
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
        
        # Set test modules to fixed height
        test_groups = [
            self.window.groupBox_usb_test,
            self.window.groupBox_emmc_test,
            self.window.groupBox_eeprom_test,
            self.window.groupBox_battery_test,
            self.window.groupBox_backlight_test,
            self.window.groupBox_led_test,
            self.window.groupBox_audio_test
        ]
        
        for group in test_groups:
            if group:
                group.setFixedHeight(50)  # Set fixed height for each test module
        
        # Create scroll area for test modules
        self._create_tests_scroll_area()
        
        # prepare the UI components dictionary to pass to the test manager
        test_ui_components = {
            "usb_ports": {
                "status_label": self.window.label_usb_status,
                "button": self.window.button_usb_test,
                "progress_bar": self.window.progressBar_hardware_test
            },
            "emmc": {
                "status_label": self.window.label_emmc_status,
                "button": self.window.button_emmc_test,
                "progress_bar": self.window.progressBar_hardware_test
            },
            "eeprom": {
                "status_label": self.window.label_eeprom_status,
                "button": self.window.button_eeprom_test,
                "progress_bar": self.window.progressBar_hardware_test
            },
            "battery": {
                "status_label": self.window.label_battery_status,
                "button": self.window.button_battery_test,
                "progress_bar": self.window.progressBar_hardware_test
            },
            "backlight": {
                "status_label": self.window.label_backlight_status,
                "button": self.window.button_backlight_test,
                "progress_bar": self.window.progressBar_hardware_test
            },
            "led": {
                "status_label": self.window.label_led_status,
                "button": self.window.button_led_test,
                "progress_bar": self.window.progressBar_hardware_test
            },
            "audio": {
                "status_label": self.window.label_audio_status,
                "button": self.window.button_audio_test,
                "progress_bar": self.window.progressBar_hardware_test
            },
            "test_all": {
                "button": self.window.button_test_all
            }
        }
        
        # set the UI components of the test manager
        self.test_manager.set_ui_components(
            test_ui_components,
            self.window.tableWidget_hardware_test_steps,
            self.window.progressBar_hardware_test
        )
        
        # connect the various test buttons to the test manager
        self.window.button_usb_test.clicked.connect(lambda: self.test_manager.start_test("usb_ports"))
        self.window.button_emmc_test.clicked.connect(lambda: self.test_manager.start_test("emmc"))
        self.window.button_eeprom_test.clicked.connect(lambda: self.test_manager.start_test("eeprom"))
        self.window.button_battery_test.clicked.connect(lambda: self.test_manager.start_test("battery"))
        self.window.button_backlight_test.clicked.connect(lambda: self.test_manager.start_test("backlight"))
        self.window.button_led_test.clicked.connect(lambda: self.test_manager.start_test("led"))
        self.window.button_audio_test.clicked.connect(lambda: self.test_manager.start_test("audio"))
        
        # connect the test all button
        self.window.button_test_all.clicked.connect(self.test_manager.start_test_all)
        
        # hide the progress bar by default
        self.window.progressBar_hardware_test.setVisible(False)
        
        # set the initial state
        for test_id in test_ui_components:
            if test_id != "test_all":
                self.test_manager._update_test_ui_state(test_id, "not_started")
    
    def _create_tests_scroll_area(self):
        """Create scroll area for test modules, keeping Progress section independent and always visible"""
        try:
            from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QPushButton
            
            # Get functionality test page layout
            tab_functionality = self.window.tab_functionality
            original_layout = tab_functionality.layout()
            
            if not original_layout:
                logger.error("Cannot find functionality test page layout")
                return
                
            # Create new scroll area
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)  # Allow content to adjust size
            scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)  # No frame
            scroll_area.setStyleSheet("background-color: #252526;")  # Set same background color as TabWidget::pane
            
            # Create scroll area content container
            scroll_content = QWidget()
            scroll_content.setStyleSheet("background-color: #252526;")  # Set content container background color
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(10)  # Set spacing between test modules
            
            # Save title and test progress group
            title_widget = None
            progress_group = None
            
            # Get title (usually the first widget)
            if original_layout.count() > 0:
                title_widget = original_layout.itemAt(0).widget()
                if title_widget and title_widget.objectName() == "label_hardware_tests":
                    original_layout.removeWidget(title_widget)
                
            # Find test progress group (usually the second last, before spacer)
            progress_index = -1
            for i in range(original_layout.count()):
                item = original_layout.itemAt(i)
                if item.widget() and item.widget().objectName() == "groupBox_hardware_test_results":
                    progress_group = item.widget()
                    progress_index = i
                    break
            
            # Clear all widgets except spacer in original layout
            items_to_move = []
            for i in range(original_layout.count()):
                item = original_layout.itemAt(i)
                # Skip spacer and progress group
                if ((not item.spacerItem()) and 
                    (not item.widget() or 
                     (item.widget() and item.widget() != progress_group))):
                    items_to_move.append(item)
            
            # Remove and collect test modules
            test_modules = []
            for item in items_to_move:
                if item.widget() and "groupBox" in item.widget().objectName() and "hardware_test_results" not in item.widget().objectName():
                    widget = item.widget()
                    original_layout.removeWidget(widget)
                    test_modules.append(widget)
            
            # Add test modules to scroll area and fix button styles
            for module in test_modules:
                # Add module to scroll area
                scroll_layout.addWidget(module)
                
                # Find all buttons in module and apply styles
                buttons = module.findChildren(QPushButton)
                for button in buttons:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #0078D7;
                            color: white;
                            border: none;
                            padding: 5px 15px;
                            border-radius: 2px;
                        }
                        QPushButton:hover {
                            background-color: #1C97EA;
                        }
                        QPushButton:pressed {
                            background-color: #00559F;
                        }
                    """)
            
            # Set scroll area content
            scroll_area.setWidget(scroll_content)
            
            # Set scroll area maximum height
            scroll_area.setMinimumHeight(180)
            scroll_area.setMaximumHeight(320)  # Set appropriate maximum height
            
            # Rebuild layout
            # 1. Add title first
            if title_widget:
                original_layout.insertWidget(0, title_widget)
                
            # 2. Then add scroll area
            original_layout.insertWidget(1, scroll_area)
            
            # 3. Ensure test progress group is moved to appropriate position (if previously removed)
            if progress_group and progress_group.parent() != tab_functionality:
                original_layout.addWidget(progress_group)

            logger.info("Successfully created test module scroll area")
        except Exception as e:
            logger.error(f"Error creating test module scroll area: {str(e)}")
    
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
            
        # Log command and response
        self._add_log_entry("DEBUG", f"[Response] {response}")
        
        # Process response based on command
        if command.startswith("get_logs"):
            self._process_logs_response(response)
    
    def _update_dashboard(self):
        """Update dashboard information"""
        # Update last updated time
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.window.label_last_updated.setText(f"Last updated: {current_time}")
        
        # In actual application, you need to get real data from device
        # Here is just an example, display some static data
        
        # Update basic system information
        self.window.value_model_name.setText(f"Device Model {self.device_id}")
        self.window.value_serial_number.setText(f"SN-{self.device_id}-2023")
        
        # Update battery information
        battery_level = 78  # This should be obtained from device
        self.window.progressBar_charge.setValue(battery_level)
        self.window.value_charge.setText(f"{battery_level}%")
    
    def _process_logs_response(self, response):
        """Process logs response"""
        # In actual application, response may be JSON or other format of log data
        # Here we simply assume response is text format of log lines
        try:
            # Clear existing logs
            self._clear_logs()
            
            # Parse response (assume each line is a log entry)
            log_lines = response.strip().split("\n")
            for line in log_lines:
                # Parse log line (format may vary depending on device)
                # Assume format is: [timestamp] [level] message
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    timestamp = parts[0].strip("[]")
                    level = parts[1].strip("[]")
                    message = parts[2]
                    self._add_log_entry(level, message, timestamp)
                else:
                    # Unparsable line, add as INFO level
                    self._add_log_entry("INFO", line)
                    
        except Exception as e:
            logger.error(f"Error processing logs response: {str(e)}")
            self._add_log_entry("ERROR", f"Failed to process logs: {str(e)}")
    
    def show(self):
        """Show window and trigger system info update"""
        # Check window properties again before showing, ensure it's part of the main application
        self._set_window_properties()
        
        # show the window
        self.window.show()
        
        # ensure the window is raised and activated
        self.window.raise_()
        self.window.activateWindow()
        
        # Trigger system info update after window is shown
        # QTimer.singleShot(100, self._on_refresh_system_info)
    
    def close(self):
        """Close window and release resources"""
        logger.info(f"Closing main window for device: {self.device_id}")
        
        # 1. stop all ongoing tests
        if hasattr(self, 'test_manager'):
            self.test_manager.stop_current_test()
        
        # 2. clean up the test manager resources
        if hasattr(self, 'test_manager') and hasattr(self.test_manager, 'cleanup'):
            logger.info("Cleaning up test manager")
            self.test_manager.cleanup()
        
        # 3. clean up the hardware test manager resources
        if hasattr(self, 'hw_test_manager') and hasattr(self.hw_test_manager, 'cleanup'):
            logger.info("Cleaning up hardware test manager")
            self.hw_test_manager.cleanup()
        
        # 4. clean up the view model resources
        if hasattr(self, 'view_model') and self.view_model and hasattr(self.view_model, 'cleanup'):
            logger.info("Cleaning up view model")
            self.view_model.cleanup()
        
        # 5. disconnect all signals
        try:
            # disconnect the view model signals
            if hasattr(self, 'view_model') and self.view_model:
                try:
                    self.view_model.command_result.disconnect(self._on_command_completed)
                except Exception:
                    pass  # if already disconnected, ignore the error
                
                # disconnect the system info service signals
                if hasattr(self.view_model, 'system_info_service'):
                    try:
                        self.view_model.system_info_service.info_received.disconnect(self._on_system_info_received)
                        self.view_model.system_info_service.info_error.disconnect(self._on_system_info_error)
                    except Exception:
                        pass  # the signal may already be disconnected
            
            # disconnect the test manager signals
            if hasattr(self, 'test_manager'):
                try:
                    self.test_manager.all_tests_completed.disconnect(self._on_all_tests_completed)
                except Exception:
                    pass  # ignore the error of already disconnected signal
                    
        except Exception as e:
            logger.error(f"Error disconnecting signals: {e}")
        
        # 6. remove the event filter
        if hasattr(self, 'window'):
            self.window.removeEventFilter(self)
            
        # 7. Close window
        self.window.close()
            
        # 8. Emit window closed signal
        self.window_closed.emit(self.device_id)
        
        logger.info(f"Main window resources cleaned up for device: {self.device_id}")

    def _set_initializing_state(self):
        """Set all system info display to initializing state"""
        # System basic info
        self.window.value_model_name.setText("...")
        self.window.value_serial_number.setText("...")
        self.window.value_cpu.setText("Initializing...")
        self.window.value_memory.setText("Initializing...")
        self.window.value_storage.setText("Initializing...")
        
        # Battery info
        self.window.value_battery_model.setText("...")
        self.window.value_battery_serial.setText("...")
        self.window.progressBar_charge.setValue(0)
        self.window.value_charge.setText("Initializing...")
        self.window.value_voltage.setText("Initializing...")
        self.window.value_current.setText("Initializing...")
        self.window.value_temperature.setText("Initializing...")

    def _set_ui_controls_enabled(self, enabled=True):
        """Enable or disable UI controls"""
        # Enable/disable test buttons
        if hasattr(self.window, 'button_usb_test'):
            self.window.button_usb_test.setEnabled(enabled)
        if hasattr(self.window, 'button_emmc_test'):
            self.window.button_emmc_test.setEnabled(enabled)
        if hasattr(self.window, 'button_eeprom_test'):
            self.window.button_eeprom_test.setEnabled(enabled)
        if hasattr(self.window, 'button_battery_test'):
            self.window.button_battery_test.setEnabled(enabled)
        if hasattr(self.window, 'button_backlight_test'):
            self.window.button_backlight_test.setEnabled(enabled)
        if hasattr(self.window, 'button_led_test'):
            self.window.button_led_test.setEnabled(enabled)
        if hasattr(self.window, 'button_audio_test'):
            self.window.button_audio_test.setEnabled(enabled)
        if hasattr(self.window, 'button_test_all'):
            self.window.button_test_all.setEnabled(enabled)
        
        # Enable/disable system info refresh button
        if hasattr(self.window, 'pushButton_refresh'):
            self.window.pushButton_refresh.setEnabled(enabled)
        
        # Enable/disable send command button
        if hasattr(self.window, 'button_send'):
            self.window.button_send.setEnabled(enabled)
        
        # Enable/disable export result button
        if hasattr(self.window, 'button_export_result'):
            self.window.button_export_result.setEnabled(enabled)
        
        # Enable/disable log filter comboboxes
        if hasattr(self.window, 'comboBox_log_level'):
            self.window.comboBox_log_level.setEnabled(enabled)
        if hasattr(self.window, 'comboBox_log_time'):
            self.window.comboBox_log_time.setEnabled(enabled)
        
        # Enable/disable tabs
        if hasattr(self.window, 'tabWidget'):
            for i in range(self.window.tabWidget.count()):
                self.window.tabWidget.setTabEnabled(i, enabled)

    def _on_refresh_system_info(self):
        """Handle refresh button click"""
        # If already updating, ignore this click
        if self.is_updating:
            return
        
        self.is_updating = True
        self._add_log_entry("INFO", f"Refreshing system info for {self.device_id}...")
        
        # Disable all control buttons
        self._set_ui_controls_enabled(False)
        
        # Do not reset to initializing state, keep current displayed data
        # self._set_initializing_state()  # Remove this line
        
        # Update timestamp, add updating mark
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.window.label_last_updated.setText(f"Last updated: {current_time} (updating...)")
        
        # Get system_info_service instance directly from view_model
        system_info_service = getattr(self.view_model, 'system_info_service', None)
        
        if system_info_service:
            # Ensure update_system_info method exists
            if hasattr(system_info_service, 'update_system_info'):
                logger.info(f"Trigger system info service update, device ID: {self.device_id}")
                system_info_service.update_system_info(self.device_id)
            else:
                logger.error("system_info_service does not have update_system_info method")
                self._on_system_info_update_completed()
        else:
            logger.warning("system_info_service not found, using simulated data")
            # If no system info service, wait a while then restore button status
            QTimer.singleShot(2000, self._on_system_info_update_completed)

    def _on_system_info_received(self, device_id, system_info):
        """System info received completed"""
        # Only process current device info
        if device_id != self.device_id:
            return
        
        # Use received data to update display
        self._update_system_info_display(system_info)
        
        # Restore button status
        self.is_updating = False
        self._set_ui_controls_enabled(True)
        
        # Update timestamp
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.window.label_last_updated.setText(f"Last updated: {current_time}")
        
        self._add_log_entry("INFO", "System info update completed")

    def _on_system_info_error(self, device_id, error_message):
        """System info update error"""
        # Only process current device info
        if device_id != self.device_id:
            return
        
        # Record error
        self._add_log_entry("ERROR", f"System info update failed: {error_message}")
        
        # Restore button status
        self.is_updating = False
        self._set_ui_controls_enabled(True)
        
        # Update timestamp
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.window.label_last_updated.setText(f"Last updated: {current_time} (failed)")

    def _update_system_info_display(self, system_info):
        """Update system info display"""
        # CPU info
        if "cpu" in system_info and "model" in system_info["cpu"]:
            self.window.value_cpu.setText(system_info["cpu"]["model"])
        
        # Memory info
        if "memory" in system_info:
            mem_info = system_info["memory"]
            if "total" in mem_info and "used" in mem_info:
                mem_text = f"{mem_info['total']} ({mem_info['used']} Used)"
                self.window.value_memory.setText(mem_text)
        
        # Storage info
        if "storage" in system_info:
            storage_info = system_info["storage"]
            if "total" in storage_info and "available" in storage_info:
                storage_text = f"{storage_info['total']} ({storage_info['available']} Available)"
                self.window.value_storage.setText(storage_text)
        
        # Battery info
        if "battery" in system_info:
            battery_info = system_info["battery"]
            
            # Battery charge
            if "relative_state" in battery_info:
                self.window.progressBar_charge.setValue(battery_info["relative_state"])
                self.window.value_charge.setText(f"{battery_info['relative_state']}%")
            
            # Voltage
            if "charging_voltage" in battery_info:
                self.window.value_voltage.setText(f"{battery_info['charging_voltage']} V")
            
            # Current
            if "charging_current" in battery_info:
                self.window.value_current.setText(f"{battery_info['charging_current']} A")
            
            # Temperature
            if "temperature" in battery_info:
                self.window.value_temperature.setText(f"{battery_info['temperature']}°C")

    def _on_system_info_update_completed(self):
        """System info update completed callback (for the case without system info service)"""
        # Restore button status
        self.is_updating = False
        self._set_ui_controls_enabled(True)
        
        # Update timestamp
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.window.label_last_updated.setText(f"Last updated: {current_time}")
        
        self._add_log_entry("INFO", "System info update completed (simulated data)")

    def _on_edit_model_name(self):
        """Handle model name edit button click"""
        current_text = self.window.value_model_name.text()
        
        # Create and show custom dark dialog
        dialog = DarkEditDialog(
            self.window, 
            "Edit model name",
            "Please enter the new model name:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                self.window.value_model_name.setText(new_text)
                # Maybe need to update backend data
    
    def _on_edit_serial_number(self):
        """Handle serial number edit button click"""
        current_text = self.window.value_serial_number.text()
        
        # Create and show custom dark dialog
        dialog = DarkEditDialog(
            self.window, 
            "Edit serial number",
            "Please enter the new serial number:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                self.window.value_serial_number.setText(new_text)
                # Maybe need to update backend data
    
    def _on_edit_battery_model(self):
        """Handle battery model edit button click"""
        current_text = self.window.value_battery_model.text()
        
        # Create and show custom dark dialog
        dialog = DarkEditDialog(
            self.window, 
            "Edit battery model",
            "Please enter the new battery model:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                self.window.value_battery_model.setText(new_text)
                # Maybe need to update backend data
    
    def _on_edit_battery_serial(self):
        """Handle battery serial edit button click"""
        current_text = self.window.value_battery_serial.text()
        
        # Create and show custom dark dialog
        dialog = DarkEditDialog(
            self.window, 
            "Edit battery serial",
            "Please enter the new battery serial number:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                self.window.value_battery_serial.setText(new_text)
                # Maybe need to update backend data

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
            
            # Set taskbar related properties on Windows
            if sys.platform == 'win32':
                try:
                    # We don't directly call Win32 API here
                    # Let the system naturally associate the window - rely on the application identifier set earlier
                    pass
                except Exception as e:
                    logger.warning(f"Unable to set Windows window properties: {e}")
            
            logger.debug(f"Window properties set: {title}")
        except Exception as e:
            logger.warning(f"Error setting window properties: {e}")

    @Slot()
    def _on_all_tests_completed(self):
        """Handle the event of all tests completed"""
        self._add_log_entry("INFO", "All hardware tests completed")
    
    def _export_test_results(self):
        """Export test results to a CSV file"""
        try:
            # get the save file path
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"test_results_{self.device_id}_{timestamp}.csv"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self.window,
                "Export Test Results",
                default_filename,
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
                
            # get the test results and progress records from the test manager
            test_results = self.test_manager.get_test_results()
            test_progress_records = self.test_manager.get_test_progress_records()
                
            # write to the CSV file
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # write the title row
                writer.writerow([
                    'Test Module',
                    'Timestamp',
                    'Current Step',
                    'Total Steps', 
                    'Progress %',
                    'Step Description',
                    'Step Status',
                    'Step Message'
                ])
                
                # write the progress records and step details for each test module
                for test_id, records in test_progress_records.items():
                    # get the step details of the test
                    test_steps = []
                    if test_id in test_results:
                        test_steps = test_results[test_id]["steps"]
                    
                    for record in records:
                        # basic progress information
                        row_data = [
                            test_id,
                            record['timestamp'],
                            record['current_step'],
                            record['total_steps'],
                            record['progress_percentage']
                        ]
                        
                        # add the step details
                        step_desc = ""
                        step_status = ""
                        step_message = ""
                        
                        # find the corresponding step information
                        current_step = record['current_step'] - 1  # convert to 0-based index
                        if test_id in self.hw_test_manager.test_workers:
                            worker = self.hw_test_manager.test_workers[test_id]
                            if len(worker.steps) > current_step:
                                step_desc = worker.steps[current_step].description
                        
                        # get the step status and message from the test results
                        for step in test_steps:
                            if step['index'] == current_step:
                                step_status = "Pass" if step['success'] else "Fail"
                                step_message = step['message']
                                break
                        
                        row_data.extend([step_desc, step_status, step_message])
                        writer.writerow(row_data)
            
            self._add_log_entry("INFO", f"Test results exported to: {file_path}")
            
        except Exception as e:
            error_msg = f"Error exporting test results: {str(e)}"
            logger.error(error_msg)
            self._add_log_entry("ERROR", error_msg)