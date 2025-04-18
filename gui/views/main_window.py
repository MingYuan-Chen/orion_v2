from PySide6.QtWidgets import QMainWindow, QHeaderView, QTableWidgetItem
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject, QEvent
from PySide6.QtUiTools import QUiLoader
from typing import Dict, Optional, List
import datetime
from util.logger import logger
from PySide6.QtGui import QColor


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
        self.window = QUiLoader().load("gui/ui/main_window.ui")
        
        # Set window title
        self.window.setWindowTitle(f"System Monitoring - Device {device_id}")
        
        # Initialize tables
        self._init_tables()
        
        # Initialize logs view
        self._init_logs_view()
        
        # Connect signals and slots
        self._connect_signals()
        
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
        
        # Add some sample logs
        self._add_sample_logs()
        
        # Connect command send button
        self.window.pushButton_send_command.clicked.connect(self._on_send_command)
        self.window.lineEdit_command.returnPressed.connect(self._on_send_command)
        
        # Connect logs filter
        self.window.comboBox_log_level.currentIndexChanged.connect(self._filter_logs)
        self.window.comboBox_time_range.currentIndexChanged.connect(self._filter_logs)
        
        # Connect refresh and clear buttons
        self.window.pushButton_refresh_logs.clicked.connect(self._refresh_logs)
        self.window.pushButton_clear_logs.clicked.connect(self._clear_logs)
    
    def _add_sample_logs(self):
        """Add sample log data"""
        sample_logs = [
            ("2025-04-15 13:45:27", "INFO", "System startup completed"),
            ("2025-04-15 13:45:28", "INFO", "Hardware initialization successful"),
            ("2025-04-15 13:45:29", "INFO", "Network services started"),
            ("2025-04-15 13:45:30", "WARNING", "Battery health check recommended"),
            ("2025-04-15 13:45:31", "ERROR", "Touch calibration failed"),
            ("2025-04-15 13:45:32", "INFO", "Storage check completed"),
            ("2025-04-15 13:45:33", "DEBUG", "CPU temperature: 45°C"),
        ]
        
        logs_table = self.window.tableWidget_logs
        logs_table.setRowCount(len(sample_logs))
        
        for row, (timestamp, level, message) in enumerate(sample_logs):
            # Create and set items
            timestamp_item = QTableWidgetItem(timestamp)
            level_item = QTableWidgetItem(level)
            message_item = QTableWidgetItem(message)
            
            # Set log level as data for filtering
            timestamp_item.setData(Qt.UserRole, level)
            level_item.setData(Qt.UserRole, level)
            message_item.setData(Qt.UserRole, level)
            
            # Set log level as attribute for styling
            logs_table.setItem(row, 0, timestamp_item)
            logs_table.setItem(row, 1, level_item)
            logs_table.setItem(row, 2, message_item)
            
            # Set color
            self._set_log_item_color(row, level)
    
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
        self._add_log_entry("INFO", f"Command sent: {command}")
    
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
        """Connect UI signals and slots"""
        # Connect button click events
        self.window.pushButton_detect_hw.clicked.connect(self._on_detect_hardware)
        self.window.pushButton_save_config.clicked.connect(self._on_save_config)
        self.window.pushButton_run_tests.clicked.connect(self._on_run_tests)
        self.window.pushButton_export_report.clicked.connect(self._on_export_report)
        
        # Connect view model signals
        self.view_model.command_result.connect(self._on_command_completed)
    
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
    
    @Slot(str, str, str)
    def _on_command_completed(self, device_id, command, response):
        """Process command completion event"""
        # Only process commands related to current device
        if device_id != self.device_id:
            return
            
        logger.debug(f"Command completed for device {device_id}: {command}")
        
        # Add command response to logs
        if command == "get_logs":
            # If it is get logs command, parse response and update logs view
            self._process_logs_response(response)
        elif command == "get_hardware_info":
            # If it is get hardware info command, update hardware table
            self._process_hardware_info(response)
            self._add_log_entry("INFO", f"Hardware information updated")
        else:
            # Other commands, add response to logs directly
            self._add_log_entry("DEBUG", f"Response for '{command}': {response}")
    
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