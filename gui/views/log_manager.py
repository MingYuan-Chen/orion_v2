"""
Log manager view module
Responsible for managing log display, filtering and clearing
"""
from typing import Dict, List, Any, Optional
import datetime
import re
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QComboBox, QPushButton
from PySide6.QtGui import QColor

from util.logger import logger


class LogManagerView(QObject):
    """
    Log manager view class
    Responsible for managing log display, filtering and clearing
    """
    
    def __init__(self, device_id: str):
        """
        Initialize log manager view
        
        Args:
            device_id: Device ID
        """
        super().__init__()
        
        # Save device ID
        self.device_id = device_id
        
        # UI components references
        self.log_table = None
        self.log_level_combo = None
        self.time_range_combo = None
        self.clear_button = None
        
        # Log entries storage
        self.log_entries = []
        
        logger.info("Log manager view initialized")
    
    def set_ui_components(self, log_table: QTableWidget, log_level_combo: QComboBox, 
                          time_range_combo: QComboBox, clear_button: QPushButton):
        """
        Set UI components references
        
        Args:
            log_table: Table widget for logs
            log_level_combo: Combo box for log level filter
            time_range_combo: Combo box for time range filter
            clear_button: Clear logs button
        """
        self.log_table = log_table
        self.log_level_combo = log_level_combo
        self.time_range_combo = time_range_combo
        self.clear_button = clear_button
        
        # Connect UI signals
        if self.log_level_combo:
            self.log_level_combo.currentIndexChanged.connect(self._filter_logs)
        
        if self.time_range_combo:
            self.time_range_combo.currentIndexChanged.connect(self._filter_logs)
        
        if self.clear_button:
            self.clear_button.clicked.connect(self.clear_logs)
        
        # Initialize log table
        self._init_log_table()
    
    def _init_log_table(self):
        """Initialize log table"""
        if not self.log_table:
            return
            
        # Clear existing items
        self.log_table.setRowCount(0)
        
        # Set column widths
        self.log_table.setColumnWidth(0, 170)  # Timestamp
        self.log_table.setColumnWidth(1, 70)   # Level
        # Message column will stretch

    def add_log_entry(self, level: str, message: str, timestamp: Optional[str] = None, scroll_to_bottom: bool = True):
        """
        Add a log entry to the log table
        
        Args:
            level: Log level (INFO, WARNING, ERROR, etc.)
            message: Log message
            timestamp: Optional timestamp, current time will be used if not provided
            scroll_to_bottom: Whether to scroll to the bottom of the log table after adding the entry
        """
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Clean message from ANSI escape codes and other non-printable characters
        # Comprehensive regex for ANSI escape sequences (CSI)
        ansi_csi_pattern = r'\x1b\[[0-?]*[ -/]*[@-~]'
        message = re.sub(ansi_csi_pattern, '', message)
        # Remove null bytes, which can come from device responses
        message = message.replace('\x00', '')
        
        # Add to log entries storage
        self.log_entries.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })
        
        # Update log table
        self._refresh_logs(scroll_to_bottom)
    
    def _set_log_item_color(self, row: int, level: str):
        """
        Set color for log item based on level
        
        Args:
            row: Row index
            level: Log level
        """
        if not self.log_table:
            return
            
        # Define colors for different log levels
        colors = {
            "DEBUG": QColor(120, 120, 120),    # Gray
            "INFO": QColor(255, 255, 255),     # White
            "WARNING": QColor(255, 204, 0),    # Yellow
            "ERROR": QColor(255, 102, 102),    # Red
            "CRITICAL": QColor(255, 0, 0)      # Bright Red
        }
        
        # Set color for all cells in the row
        color = colors.get(level, QColor(255, 255, 255))  # Default to white
        
        for col in range(self.log_table.columnCount()):
            item = self.log_table.item(row, col)
            if item:
                item.setForeground(color)
    
    def _filter_logs(self):
        """Filter logs based on selected level and time range"""
        self._refresh_logs(True)  # scroll to bottom
    
    def _refresh_logs(self, scroll_to_bottom: bool = True):
        """
        Refresh log table display based on current filters
        
        Args:
            scroll_to_bottom: Whether to scroll to the bottom of the log table
        """
        if not self.log_table or not self.log_level_combo or not self.time_range_combo:
            return
            
        # Get current filters
        level_filter = self.log_level_combo.currentText()
        time_filter = self.time_range_combo.currentText()
        
        # Parse time filter
        hours = 0
        if time_filter == "Last 1 hour":
            hours = 1
        elif time_filter == "Last 6 hours":
            hours = 6
        elif time_filter == "Last 24 hours":
            hours = 24
        elif time_filter == "Last 7 days":
            hours = 24 * 7
        
        # Filter log entries
        filtered_entries = []
        current_time = datetime.datetime.now()
        
        for entry in self.log_entries:
            # Apply level filter
            if level_filter != "ALL" and entry["level"] != level_filter:
                continue
                
            # Apply time filter
            if hours > 0:
                try:
                    log_time = datetime.datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
                    time_diff = current_time - log_time
                    if time_diff.total_seconds() > hours * 3600:
                        continue
                except ValueError:
                    # In case of invalid timestamp, skip filtering
                    pass
            
            filtered_entries.append(entry)
        
        # Update table
        self.log_table.setRowCount(0)  # Clear table
        
        for entry in filtered_entries:
            row = self.log_table.rowCount()
            self.log_table.insertRow(row)
            
            # Add timestamp
            self.log_table.setItem(row, 0, QTableWidgetItem(entry["timestamp"]))
            
            # Add level
            self.log_table.setItem(row, 1, QTableWidgetItem(entry["level"]))
            
            # Add message
            self.log_table.setItem(row, 2, QTableWidgetItem(entry["message"]))
            
            # Set row color based on level
            self._set_log_item_color(row, entry["level"])
        
        # Only scroll to bottom if requested
        if scroll_to_bottom:
            # Scroll to bottom to show latest logs
            self.log_table.scrollToBottom()
    
    def clear_logs(self):
        """Clear all log entries"""
        self.log_entries = []
        if self.log_table:
            self.log_table.setRowCount(0)
        logger.info("Logs cleared")
    
    def process_logs_response(self, response: str):
        """
        Process logs response from device
        
        Args:
            response: Log response string from device
        """
        if not response:
            return
            
        # Split response into lines
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try to parse log entry
            try:
                # Expected format: [TIMESTAMP] [LEVEL] MESSAGE
                # E.g. [2022-01-01 12:00:00] [INFO] This is a log message
                
                # Extract timestamp
                timestamp_start = line.find('[')
                timestamp_end = line.find(']')
                if timestamp_start != -1 and timestamp_end != -1:
                    timestamp = line[timestamp_start+1:timestamp_end].strip()
                    line = line[timestamp_end+1:].strip()
                else:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Extract level
                level_start = line.find('[')
                level_end = line.find(']')
                if level_start != -1 and level_end != -1:
                    level = line[level_start+1:level_end].strip()
                    message = line[level_end+1:].strip()
                else:
                    level = "INFO"
                    message = line
                
                # Add log entry
                self.add_log_entry(level, message, timestamp)
                
            except Exception as e:
                # If parsing fails, add as raw message
                logger.warning(f"Failed to parse log entry: {e}")
                self.add_log_entry("INFO", line)
    
    def cleanup(self):
        """Clean up log manager resources"""
        try:
            logger.debug("Cleaning up LogManagerView resources")
            
            # Disconnect signals
            if self.log_level_combo:
                try:
                    self.log_level_combo.currentIndexChanged.disconnect(self._filter_logs)
                except Exception:
                    pass
            
            if self.time_range_combo:
                try:
                    self.time_range_combo.currentIndexChanged.disconnect(self._filter_logs)
                except Exception:
                    pass
            
            if self.clear_button:
                try:
                    self.clear_button.clicked.disconnect(self.clear_logs)
                except Exception:
                    pass
            
            # Clear references
            self.log_table = None
            self.log_level_combo = None
            self.time_range_combo = None
            self.clear_button = None
            
            # Clear log entries
            self.log_entries = []
            
        except Exception as e:
            logger.error(f"Error during LogManagerView cleanup: {e}") 