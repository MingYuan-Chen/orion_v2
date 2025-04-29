from PySide6.QtWidgets import QMainWindow, QHeaderView, QTableWidgetItem, QInputDialog, QLineEdit
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject, QEvent
from PySide6.QtUiTools import QUiLoader
from typing import Dict, Optional, List
import datetime
from util.logger import logger
from PySide6.QtGui import QColor, QIcon, QFont
import os
import sys
from PySide6.QtCore import QFile
from core.services.hardware_test_manager import HardwareTestManagerService
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout


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
        
        # Add test sequence list and current test index
        self.test_sequence = ["usb_ports", "emmc", "eeprom", "battery", "backlight", "led", "audio"]
        self.current_test_index = -1
        self.is_test_all_running = False
        
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
        
        # Connect signals and slots
        self._connect_signals()
        
        # Initialize test results storage
        self.test_results = {}
        
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
        
        # Connect hardware test manager signals
        self.hw_test_manager.test_started.connect(self._on_test_started)
        self.hw_test_manager.test_completed.connect(self._on_test_completed)
        self.hw_test_manager.test_step_completed.connect(self._on_test_step_completed)
        self.hw_test_manager.test_step_retrying.connect(self._on_test_step_retrying)
        self.hw_test_manager.test_progress.connect(self._on_test_progress)
        
        # Add system info service signals
        if hasattr(self.view_model, 'system_info_service'):
            self.view_model.system_info_service.info_received.connect(self._on_system_info_received)
            self.view_model.system_info_service.info_error.connect(self._on_system_info_error)
    
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
            self.window.groupBox_led_test,  # Add LED test group
            self.window.groupBox_audio_test  # Add Audio test group
        ]
        
        for group in test_groups:
            if group:
                group.setFixedHeight(50)  # Set fixed height for each test module
        
        # Create scroll area for test modules
        self._create_tests_scroll_area()
        
        # Connect USB test button
        self.window.button_usb_test.clicked.connect(lambda: self._start_hardware_test("usb_ports"))
        
        # Connect emmc test button
        self.window.button_emmc_test.clicked.connect(lambda: self._start_hardware_test("emmc"))
        
        # Connect eeprom test button
        self.window.button_eeprom_test.clicked.connect(lambda: self._start_hardware_test("eeprom"))
        
        # Connect battery test button
        self.window.button_battery_test.clicked.connect(lambda: self._start_hardware_test("battery"))
        
        # Connect backlight test button
        self.window.button_backlight_test.clicked.connect(lambda: self._start_hardware_test("backlight"))
        
        # Connect LED test button
        self.window.button_led_test.clicked.connect(lambda: self._start_hardware_test("led"))
        
        # Connect Audio test button
        self.window.button_audio_test.clicked.connect(lambda: self._start_hardware_test("audio"))
        
        # Connect Test All button
        self.window.button_test_all.clicked.connect(self._start_test_all)
        
        # Default hide progress bar
        self.window.progressBar_hardware_test.setVisible(False)
        
        # Set initial state
        self._update_test_ui_state("usb_ports", "not_started")
        self._update_test_ui_state("emmc", "not_started")
        self._update_test_ui_state("eeprom", "not_started")
        self._update_test_ui_state("battery", "not_started")
        self._update_test_ui_state("backlight", "not_started")
        self._update_test_ui_state("led", "not_started")
        self._update_test_ui_state("audio", "not_started")
    
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
    
    def _start_hardware_test(self, test_id: str):
        """
        Common method to start hardware test
        
        Args:
            test_id: Test ID
        """
        # Clear previous test results
        self.window.tableWidget_hardware_test_steps.setRowCount(0)
        
        # Start test
        self.hw_test_manager.start_test(self.device_id, test_id)
        
        # Record test start
        self._add_log_entry("INFO", f"Starting {test_id} test for device {self.device_id}")
    
    def _update_test_ui_state(self, test_id: str, state: str, message: str = ""):
        """
        Update test UI state
        
        Args:
            test_id: Test ID
            state: State ('not_started', 'running', 'pass', 'fail')
            message: Optional message
        """
        # Determine which UI components to update based on test ID
        if test_id == "usb_ports":
            status_label = self.window.label_usb_status
            button = self.window.button_usb_test
        elif test_id == "emmc":
            status_label = self.window.label_emmc_status
            button = self.window.button_emmc_test
        elif test_id == "eeprom":
            status_label = self.window.label_eeprom_status
            button = self.window.button_eeprom_test
        elif test_id == "battery":
            status_label = self.window.label_battery_status
            button = self.window.button_battery_test
        elif test_id == "backlight":
            status_label = self.window.label_backlight_status
            button = self.window.button_backlight_test
        elif test_id == "led":
            status_label = self.window.label_led_status
            button = self.window.button_led_test
        elif test_id == "audio":
            status_label = self.window.label_audio_status
            button = self.window.button_audio_test
        else:
            # Unknown test ID, do not update UI
            return
        
        # Shared progress bar
        progress_bar = self.window.progressBar_hardware_test
        
        # Update UI based on state
        if state == "not_started":
            status_label.setStyleSheet("background-color: #333333; border-radius: 8px; min-width: 16px; min-height: 16px; max-width: 16px; max-height: 16px;")
            button.setText("Start Test")
            button.setEnabled(True)
            progress_bar.setVisible(False)
            
        elif state == "running":
            status_label.setStyleSheet("background-color: #FFA500; border-radius: 8px; min-width: 16px; min-height: 16px; max-width: 16px; max-height: 16px;")
            button.setText("Running...")
            button.setEnabled(False)
            progress_bar.setVisible(True)
            
        elif state == "pass":
            status_label.setStyleSheet("background-color: #00AA00; border-radius: 8px; min-width: 16px; min-height: 16px; max-width: 16px; max-height: 16px;")
            button.setText("Start Test")
            button.setEnabled(True)
            progress_bar.setVisible(False)
            
        elif state == "fail":
            status_label.setStyleSheet("background-color: #FF0000; border-radius: 8px; min-width: 16px; min-height: 16px; max-width: 16px; max-height: 16px;")
            button.setText("Start Test")
            button.setEnabled(True)
            progress_bar.setVisible(False)
    
    @Slot(str)
    def _on_test_started(self, test_id: str):
        """
        Handle test started event
        
        Args:
            test_id: Test ID
        """
        # Update test UI state
        self._update_test_ui_state(test_id, "running")
        
        # Initialize test results storage
        self.test_results[test_id] = {
            "steps": [],
            "success": None,
            "message": ""
        }
        
        logger.info(f"Test started: {test_id} for device {self.device_id}")
    
    @Slot(str, bool, str)
    def _on_test_completed(self, test_id: str, success: bool, message: str):
        """
        Handle test completed event
        
        Args:
            test_id: Test ID
            success: Whether test passed
            message: Result message
        """
        # Store test results
        if test_id in self.test_results:
            self.test_results[test_id]["success"] = success
            self.test_results[test_id]["message"] = message
        
        # Update test UI state
        self._update_test_ui_state(test_id, "pass" if success else "fail", message)
        
        # Log test completion
        log_level = "INFO" if success else "ERROR"
        self._add_log_entry(log_level, f"Test {test_id} completed: {message}")
        
        # If we're running Test All, execute next test
        if self.is_test_all_running:
            QTimer.singleShot(1000, self._execute_next_test)  # Wait 1 second before starting next test
    
    @Slot(str, int, bool, str)
    def _on_test_step_completed(self, test_id: str, step_index: int, success: bool, message: str):
        """
        Handle test step completed event
        
        Args:
            test_id: Test ID
            step_index: Step index
            success: Whether step passed
            message: Step result message
        """
        # Store step results
        if test_id in self.test_results:
            self.test_results[test_id]["steps"].append({
                "index": step_index,
                "success": success,
                "message": message
            })
        
        # Update test step UI
        table = self.window.tableWidget_hardware_test_steps
        row = table.rowCount()
        table.insertRow(row)
        
        # Get step description
        step_description = ""
        if test_id in self.hw_test_manager.test_workers and len(self.hw_test_manager.test_workers[test_id].steps) > step_index:
            step = self.hw_test_manager.test_workers[test_id].steps[step_index]
            step_description = step.description
        
        # Add step details
        table.setItem(row, 0, QTableWidgetItem(step_description))
        table.setItem(row, 1, QTableWidgetItem("Pass" if success else "Fail"))
        table.setItem(row, 2, QTableWidgetItem(message))
        
        # Set row color
        color = QColor("#00AA00") if success else QColor("#FF0000")
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item:
                item.setForeground(color)
        
        # Record step completion
        log_level = "INFO" if success else "WARNING"
        self._add_log_entry(log_level, f"Test {test_id} step {step_index+1}: {message}")
        
        # Scroll to latest item
        table.scrollToBottom()
    
    @Slot(str, int, int, int, str)
    def _on_test_step_retrying(self, test_id: str, step_index: int, retry_count: int, max_retries: int, error: str):
        """
        Handle test step retry event
        
        Args:
            test_id: Test ID
            step_index: Step index
            retry_count: Current retry count
            max_retries: Maximum retry count
            error: Error message
        """
        # Log retry
        self._add_log_entry("WARNING", f"Test {test_id} step {step_index+1} retrying ({retry_count}/{max_retries}): {error}")
    
    @Slot(str, int, int)
    def _on_test_progress(self, test_id: str, current_step: int, total_steps: int):
        """
        Handle test progress event
        
        Args:
            test_id: Test ID
            current_step: Current step index (starts from 1)
            total_steps: Total number of steps
        """
        # Update progress bar
        progress_pct = int((current_step / total_steps) * 100)
        self.window.progressBar_hardware_test.setValue(progress_pct)
        
        # Record progress (every 25% of total steps)
        if current_step % max(1, total_steps // 4) == 0 or current_step == total_steps:
            self._add_log_entry("INFO", f"Test {test_id} progress: {current_step}/{total_steps} ({progress_pct}%)")
    
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
        
        # 啟動窗口
        self.window.show()
        
        # 確保窗口提升到前面並激活
        self.window.raise_()
        self.window.activateWindow()
        
        # Trigger system info update after window is shown
        # QTimer.singleShot(100, self._on_refresh_system_info)
    
    def close(self):
        """Close window and release resources"""
        logger.info(f"Closing main window for device: {self.device_id}")
        
        # 1. Stop all ongoing tests
        if hasattr(self, 'hw_test_manager'):
            self.hw_test_manager.stop_current_test()
        
        # 2. Clean up hardware test manager resources
        if hasattr(self, 'hw_test_manager') and hasattr(self.hw_test_manager, 'cleanup'):
            logger.info("Cleaning up hardware test manager")
            self.hw_test_manager.cleanup()
        
        # 3. Clean up view_model resources
        if hasattr(self, 'view_model') and self.view_model and hasattr(self.view_model, 'cleanup'):
            logger.info("Cleaning up view model")
            self.view_model.cleanup()
        
        # 4. Disconnect all signals
        try:
            # Disconnect view_model signals
            if hasattr(self, 'view_model') and self.view_model:
                try:
                    self.view_model.command_result.disconnect(self._on_command_completed)
                except Exception:
                    pass  # If already disconnected, ignore error
                
                # Disconnect system info service signals
                if hasattr(self.view_model, 'system_info_service'):
                    try:
                        self.view_model.system_info_service.info_received.disconnect(self._on_system_info_received)
                        self.view_model.system_info_service.info_error.disconnect(self._on_system_info_error)
                    except Exception:
                        pass  # Signals may already be disconnected
            
            # Disconnect hardware test manager signals
            if hasattr(self, 'hw_test_manager'):
                try:
                    self.hw_test_manager.test_started.disconnect(self._on_test_started)
                    self.hw_test_manager.test_completed.disconnect(self._on_test_completed)
                    self.hw_test_manager.test_step_completed.disconnect(self._on_test_step_completed)
                    self.hw_test_manager.test_step_retrying.disconnect(self._on_test_step_retrying)
                    self.hw_test_manager.test_progress.disconnect(self._on_test_progress)
                except Exception:
                    pass  # Ignore already disconnected signal errors
            
            # Disconnect window button signals
            if hasattr(self, 'window'):
                try:
                    self.window.pushButton_refresh.clicked.disconnect(self._on_refresh_system_info)
                    self.window.pushButton_refresh_logs.clicked.disconnect(self._refresh_logs)
                    self.window.pushButton_clear_logs.clicked.disconnect(self._clear_logs)
                    self.window.pushButton_send_command.clicked.disconnect(self._on_send_command)
                    self.window.lineEdit_command.returnPressed.disconnect(self._on_send_command)
                    self.window.button_edit_model_name.clicked.disconnect(self._on_edit_model_name)
                    self.window.button_edit_serial_number.clicked.disconnect(self._on_edit_serial_number)
                    self.window.button_edit_battery_model.clicked.disconnect(self._on_edit_battery_model)
                    self.window.button_edit_battery_serial.clicked.disconnect(self._on_edit_battery_serial)
                    self.window.comboBox_log_level.currentIndexChanged.disconnect(self._filter_logs)
                    self.window.comboBox_time_range.currentIndexChanged.disconnect(self._filter_logs)
                    
                    # Test buttons signals
                    self.window.button_usb_test.clicked.disconnect()
                    self.window.button_emmc_test.clicked.disconnect()
                    self.window.button_eeprom_test.clicked.disconnect()
                    self.window.button_battery_test.clicked.disconnect()
                    self.window.button_backlight_test.clicked.disconnect()
                    self.window.button_led_test.clicked.disconnect()
                    self.window.button_audio_test.clicked.disconnect()  # 斷開音頻測試按鈕的信號連接
                except Exception:
                    pass  # Ignore already disconnected signal errors
            
            # Disconnect our signals
            try:
                self.window_closed.disconnect()
            except Exception:
                pass  # Ignore already disconnected signal errors
                
        except Exception as e:
            logger.warning(f"Error while disconnecting signals: {e}")
        
        # 5. Stop all timers
        if hasattr(self, 'retry_timer') and hasattr(self.retry_timer, 'stop'):
            self.retry_timer.stop()
            
        # Stop any existing QTimers (one-time timers)
        for timer in QTimer.findChildren(self, QTimer):
            if timer.isActive():
                timer.stop()
        
        # 6. Remove event filter
        if hasattr(self, 'window'):
            self.window.removeEventFilter(self)
            
        # 7. Close window
        self.window.close()
            
        # 8. Emit window closed signal
        self.window_closed.emit(self.device_id)
        
        # 9. Clear references
        self.test_results.clear()
        
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
        """Set all control buttons enabled"""
        # Refresh button
        self.window.pushButton_refresh.setEnabled(enabled)
        
        # Function test buttons
        self.window.button_usb_test.setEnabled(enabled)
        self.window.button_emmc_test.setEnabled(enabled)
        self.window.button_eeprom_test.setEnabled(enabled)
        self.window.button_battery_test.setEnabled(enabled)
        self.window.button_backlight_test.setEnabled(enabled)
        self.window.button_led_test.setEnabled(enabled)
        self.window.button_audio_test.setEnabled(enabled)  # 啟用/禁用音頻測試按鈕
        
        # Log related buttons
        self.window.pushButton_refresh_logs.setEnabled(enabled)
        self.window.pushButton_clear_logs.setEnabled(enabled)
        self.window.pushButton_send_command.setEnabled(enabled)
        self.window.lineEdit_command.setEnabled(enabled)

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

    def _start_test_all(self):
        """Start executing all test modules in sequence"""
        # If already running test all, ignore
        if self.is_test_all_running:
            return
            
        # Clear previous test results
        self.window.tableWidget_hardware_test_steps.setRowCount(0)
        
        # Reset test sequence
        self.current_test_index = -1
        self.is_test_all_running = True
        
        # Disable Test All button
        self.window.button_test_all.setEnabled(False)
        self.window.button_test_all.setText("Running...")
        
        # Start first test
        self._execute_next_test()
        
        # Record start of test all
        self._add_log_entry("INFO", "Starting Test All sequence")

    def _execute_next_test(self):
        """Execute next test in the sequence"""
        self.current_test_index += 1
        
        # Check if we've completed all tests
        if self.current_test_index >= len(self.test_sequence):
            self._complete_test_all()
            return
            
        # Get next test ID
        test_id = self.test_sequence[self.current_test_index]
        
        # Start the test
        self._start_hardware_test(test_id)

    def _complete_test_all(self):
        """Complete Test All sequence"""
        self.is_test_all_running = False
        self.current_test_index = -1
        
        # Enable Test All button
        self.window.button_test_all.setEnabled(True)
        self.window.button_test_all.setText("Test All")
        
        # Record completion
        self._add_log_entry("INFO", "Test All sequence completed")