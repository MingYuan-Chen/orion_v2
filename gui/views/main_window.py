from PySide6.QtWidgets import QMainWindow, QHeaderView, QTableWidgetItem
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject, QEvent
from PySide6.QtUiTools import QUiLoader
from typing import Dict, Optional, List
import datetime
from util.logger import logger
from PySide6.QtGui import QColor, QIcon
import os
import sys
from PySide6.QtCore import QFile
from core.services.hardware_test_manager import HardwareTestManagerService


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
        
        # Set window title
        self.window.setWindowTitle(f"System Monitoring - Device {device_id}")
        
        # Set window icon
        try:
            if os.path.exists(icon_path):
                self.window.setWindowIcon(QIcon(icon_path))
                logger.debug(f"Main window icon set successfully for device {device_id}")
            else:
                logger.warning(f"Icon file not found: {icon_path}")
        except Exception as e:
            logger.error(f"Failed to set window icon: {str(e)}")
        
        # Initialize tables
        self._init_tables()
        
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
        
        # Set auto update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_dashboard)
        self.update_timer.start(5000)  # Update every 5 seconds
        
        # Load device data
        self._update_dashboard()
        
        # Install event filter to capture window close event
        self.window.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Filter window events to capture close event"""
        if obj is self.window and event.type() == QEvent.Close:
            logger.info(f"Main window for device {self.device_id} is closing")
            # Stop update timer
            self.update_timer.stop()
            # Emit window close signal
            self.window_closed.emit(self.device_id)
        return super().eventFilter(obj, event)
    
    def _init_tables(self):
        """Initialize table settings"""
        # Configure hardware table
        hw_table = self.window.tableWidget_hw
        hw_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Configure diagnostic table
        diag_table = self.window.tableWidget_diagnostic
        diag_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Add some sample data
        self._populate_sample_data()
    
    def _populate_sample_data(self):
        """Add sample data to tables"""
        # Hardware table sample data
        hw_table = self.window.tableWidget_hw
        hw_table.setRowCount(4)
        
        components = [
            ("CPU", "NXP i.MX6 Quad", "CPU-2023-0123", "Normal"),
            ("Memory", "DDR4-8GB", "MEM-2023-9876", "Normal"),
            ("Storage", "eMMC 128GB", "STO-2023-4567", "Normal"),
            ("Battery", "MD-BAT", "240500734", "Normal")
        ]
        
        for row, (comp, part, serial, status) in enumerate(components):
            hw_table.setItem(row, 0, QTableWidgetItem(comp))
            hw_table.setItem(row, 1, QTableWidgetItem(part))
            hw_table.setItem(row, 2, QTableWidgetItem(serial))
            hw_table.setItem(row, 3, QTableWidgetItem(status))
        
        # Diagnostic table sample data
        diag_table = self.window.tableWidget_diagnostic
        diag_table.setRowCount(3)
        
        tests = [
            ("System Boot Test", "Passed", "00:01:23"),
            ("Memory Test", "Passed", "00:03:45"),
            ("Storage Test", "Passed", "00:02:12")
        ]
        
        for row, (test, status, time) in enumerate(tests):
            diag_table.setItem(row, 0, QTableWidgetItem(test))
            diag_table.setItem(row, 1, QTableWidgetItem(status))
            diag_table.setItem(row, 2, QTableWidgetItem(time))
    
    def _init_logs_view(self):
        """Initialize logs view settings"""
        # Configure logs table
        logs_table = self.window.tableWidget_logs
        logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        logs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Message column stretch
        
        # Set column width
        logs_table.setColumnWidth(0, 180)  # Timestamp column
        logs_table.setColumnWidth(1, 80)   # Level column
        
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
        
        logs_table.setItem(current_row_count, 0, timestamp_item)
        logs_table.setItem(current_row_count, 1, level_item)
        logs_table.setItem(current_row_count, 2, message_item)
        
        # Set color
        self._set_log_item_color(current_row_count, level)
        
        # Scroll to latest item
        logs_table.scrollToBottom()
    
    def _connect_signals(self):
        """Connect signals and slots"""
        # Connect command result signal from view model
        self.view_model.command_result.connect(self._on_command_completed)
        
        # Connect hardware detection and config buttons
        self.window.pushButton_detect_hw.clicked.connect(self._on_detect_hardware)
        self.window.pushButton_save_config.clicked.connect(self._on_save_config)
        
        # Connect diagnostic test buttons
        self.window.pushButton_run_tests.clicked.connect(self._on_run_tests)
        self.window.pushButton_export_report.clicked.connect(self._on_export_report)
        
        # Connect hardware test manager signals
        self.hw_test_manager.test_started.connect(self._on_test_started)
        self.hw_test_manager.test_completed.connect(self._on_test_completed)
        self.hw_test_manager.test_step_completed.connect(self._on_test_step_completed)
        self.hw_test_manager.test_step_retrying.connect(self._on_test_step_retrying)
        self.hw_test_manager.test_progress.connect(self._on_test_progress)
    
    def _init_functionality_test_ui(self):
        """Initialize functionality test UI elements"""
        # Configure USB test steps table
        usb_table = self.window.tableWidget_usb_test_steps
        usb_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        usb_table.horizontalHeader().setStretchLastSection(True)
        usb_table.setColumnWidth(0, 150)  # Step column
        usb_table.setColumnWidth(1, 80)   # Status column
        
        # Connect USB test button
        self.window.button_usb_test.clicked.connect(self._on_usb_test_clicked)
        
        # Hide progress bar initially
        self.window.progressBar_usb_test.setVisible(False)
        
        # Set initial state
        self._update_test_ui_state("usb_ports", "not_started")
    
    def _update_test_ui_state(self, test_id: str, state: str, message: str = ""):
        """
        Update test UI state
        
        Args:
            test_id: Test ID
            state: State ('not_started', 'running', 'pass', 'fail')
            message: Optional message
        """
        if test_id == "usb_ports":
            status_label = self.window.label_usb_status
            button = self.window.button_usb_test
            progress_bar = self.window.progressBar_usb_test
            
            # Update status indicator
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
    
    def _on_usb_test_clicked(self):
        """Handle USB test button click"""
        # Clear previous test results
        self.window.tableWidget_usb_test_steps.setRowCount(0)
        
        # Start USB ports test
        self.hw_test_manager.start_test(self.device_id, "usb_ports")
        
        # Log test start
        self._add_log_entry("INFO", f"Starting USB ports test for device {self.device_id}")
    
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
        if test_id == "usb_ports":
            table = self.window.tableWidget_usb_test_steps
            row = table.rowCount()
            table.insertRow(row)
            
            # Get step from test worker
            step_description = ""
            if len(self.hw_test_manager.test_workers[test_id].steps) > step_index:
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
        
        # Log step completion
        log_level = "INFO" if success else "WARNING"
        self._add_log_entry(log_level, f"Test {test_id} step {step_index+1}: {message}")
    
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
            current_step: Current step index (1-based)
            total_steps: Total steps count
        """
        # Update progress bar
        if test_id == "usb_ports":
            progress_pct = int((current_step / total_steps) * 100)
            self.window.progressBar_usb_test.setValue(progress_pct)
            
        # Log progress (every 25%)
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
        elif command.startswith("get_hw_info"):
            self._process_hardware_info(response)
    
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
    
    def _on_detect_hardware(self):
        """Detect hardware button click event"""
        logger.info(f"Detecting hardware for device: {self.device_id}")
        # In actual application, you should send command to device to get hardware information
        # Then update table
        
        # Example: Assume we send command and get response
        self.view_model.send_command(self.device_id, "get_hardware_info")
    
    def _on_save_config(self):
        """Save configuration button click event"""
        logger.info(f"Saving configuration for device: {self.device_id}")
        # Implement saving configuration logic
    
    def _on_run_tests(self):
        """Run tests button click event"""
        logger.info(f"Running diagnostic tests for device: {self.device_id}")
        # Implement running diagnostic tests logic
    
    def _on_export_report(self):
        """Export report button click event"""
        logger.info(f"Exporting diagnostic report for device: {self.device_id}")
        # Implement exporting diagnostic report logic
    
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
    
    def _process_hardware_info(self, response):
        """Process hardware info response"""
        # In actual application, parse device returned hardware info and update table
        try:
            # Assume response is JSON format of hardware info
            # Here is just a simple example, actual implementation needs to be based on device returned format
            hw_table = self.window.tableWidget_hw
            hw_table.setRowCount(0)  # Clear table
            
            # Add some sample data (actual application should parse response)
            components = [
                ("CPU", "NXP i.MX6 Quad", "CPU-2023-0123", "Normal"),
                ("Memory", "DDR4-8GB", "MEM-2023-9876", "Normal"),
                ("Storage", "eMMC 128GB", "STO-2023-4567", "Normal"),
                ("Battery", "MD-BAT", "240500734", "Normal"),
                ("Touchscreen", "GT911", "TCH-2023-5678", "Error")
            ]
            
            hw_table.setRowCount(len(components))
            for row, (comp, part, serial, status) in enumerate(components):
                hw_table.setItem(row, 0, QTableWidgetItem(comp))
                hw_table.setItem(row, 1, QTableWidgetItem(part))
                hw_table.setItem(row, 2, QTableWidgetItem(serial))
                
                status_item = QTableWidgetItem(status)
                if status == "Error":
                    status_item.setForeground(Qt.red)
                elif status == "Warning":
                    status_item.setForeground(QColor("#FFD700"))  # Yellow
                else:
                    status_item.setForeground(Qt.green)
                    
                hw_table.setItem(row, 3, status_item)
        
        except Exception as e:
            logger.error(f"Error processing hardware info: {str(e)}")
            self._add_log_entry("ERROR", f"Failed to process hardware info: {str(e)}")
    
    def show(self):
        """Show window"""
        self.window.show()
    
    def close(self):
        """Close window and release resources"""
        # Stop update timer
        if hasattr(self, 'update_timer') and self.update_timer.isActive():
            self.update_timer.stop()
        
        # Remove event filter
        if hasattr(self, 'window'):
            self.window.removeEventFilter(self)
            
        # Close window
        self.window.close()
            
        # Emit window closed signal (if not already emitted)
        self.window_closed.emit(self.device_id)
        
        logger.info(f"Main window resources cleaned up for device: {self.device_id}")