"""
Battery Monitor Manager Module
Manages battery monitoring UI updates and data display
"""
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QMessageBox, QProgressBar, QLabel, QPushButton
from typing import Dict, Any, Optional
from util.logger import logger
import datetime
import csv
import os


class BatteryMonitorManager(QObject):
    """
    Battery Monitor Manager
    Handles battery monitoring UI updates and data presentation
    """
    
    # Define signals
    monitoring_started = Signal()
    monitoring_completed = Signal()
    monitoring_error = Signal(str)
    
    def __init__(self, device_id: str, battery_service):
        """
        Initialize battery monitor manager
        
        Args:
            device_id: Device ID
            battery_service: BatteryMonitorService instance
        """
        super().__init__()
        
        self.device_id = device_id
        self.battery_service = battery_service
        
        # UI components references (set by main controller)
        self.ui_components = {}
        self.main_controller = None
        self.chart_widget = None  # Reference to chart widget
        
        # Battery data storage
        self.current_battery_data = {}
        self.battery_history = []  # Store historical data for trending
        self.max_history_entries = 100  # Limit history size
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_interval = 3000  # 3 seconds default (optimized for better user experience)
        self.monitoring_timer = QTimer()
        self.monitoring_timer.timeout.connect(self._on_monitoring_timer)
        
        # CSV logging state
        self.csv_logging_enabled = False
        self.csv_file_path = None
        self.csv_writer = None
        self.csv_file = None
        
        # CSV data cache for handling empty values
        self.csv_data_cache = {
            "relative_state": "",
            "voltage": "",
            "current": "",
            "temperature": "",
            "led_status": "",
            "interrupt_status": "",
            "battery_status": "",
            "cpu_usage": "",
            "memory_usage": ""
        }
        
        # Connect battery service signals
        self._connect_signals()
        
        logger.info(f"Battery Monitor Manager initialized for device: {device_id}")
    
    def _connect_signals(self):
        """Connect battery service signals"""
        self.battery_service.battery_info_received.connect(self._on_battery_info_received)
        self.battery_service.battery_info_error.connect(self._on_battery_info_error)
        self.battery_service.battery_command_executed.connect(self._on_battery_command_executed)
    
    def set_ui_components(self, components: Dict[str, Any]):
        """
        Set UI components for battery display
        
        Args:
            components: Dictionary of UI component references
            Expected keys:
            - monitor_button: QPushButton for start/stop monitoring
            - refresh_button: QPushButton for single refresh (optional)
            - status_label: QLabel for showing monitoring status
            - voltage_label: QLabel for voltage display
            - current_label: QLabel for current display
            - temperature_label: QLabel for temperature display
            - battery_level_label: QLabel for battery level display
            - progress_bar: QProgressBar for battery level (optional)
        """
        self.ui_components = components
        
        # Connect refresh button if provided
        if "refresh_button" in components:
            refresh_button = components["refresh_button"]
            
            # Disconnect any existing connections first
            try:
                refresh_button.clicked.disconnect()
                logger.debug("Disconnected existing refresh button connections")
            except:
                pass  # No existing connections
            
            # Connect to refresh_once method
            refresh_button.clicked.connect(self.refresh_once)
            logger.info(f"Refresh button connected to refresh_once method: {refresh_button}")
            logger.info(f"Button text: '{refresh_button.text()}'")
            logger.info(f"Button enabled: {refresh_button.isEnabled()}")
            logger.info(f"Button visible: {refresh_button.isVisible()}")
            
        else:
            logger.warning("No refresh_button found in UI components")
        
        # Connect interval spinbox if provided
        if "interval_spinbox" in components:
            interval_spinbox = components["interval_spinbox"]
            
            # Disconnect any existing connections first
            try:
                interval_spinbox.valueChanged.disconnect()
                logger.debug("Disconnected existing interval spinbox connections")
            except:
                pass  # No existing connections
            
            # Connect to interval change method
            interval_spinbox.valueChanged.connect(self._on_interval_changed)
            
            # Set initial value from current monitoring interval (convert ms to seconds)
            initial_seconds = self.monitoring_interval // 1000
            interval_spinbox.setValue(initial_seconds)
            
            logger.info(f"Interval spinbox connected: {interval_spinbox}")
            logger.info(f"Initial value set to: {initial_seconds} seconds")
            
        else:
            logger.warning("No interval_spinbox found in UI components")
        
        logger.debug("Battery Monitor UI components set")
    
    def set_main_controller(self, controller):
        """Set reference to main controller"""
        self.main_controller = controller
    
    def set_chart_widget(self, chart_widget):
        """Set reference to chart widget"""
        self.chart_widget = chart_widget
    
    def start_monitoring(self) -> bool:
        """
        Start battery monitoring
        
        Returns:
            bool: True if monitoring started successfully
        """
        # Check if manager is already monitoring
        if self.is_monitoring:
            logger.warning("Battery monitoring already active")
            return False
        
        # Check if service is in single reading mode
        if getattr(self.battery_service, '_single_reading_mode', False):
            logger.warning("Cannot start monitoring while single reading is in progress")
            return False
        
        logger.info(f"Starting battery monitoring for device: {self.device_id}")
        
        # Check if CSV logging is enabled
        self._check_and_setup_csv_logging()
        
        # Update state first
        self.is_monitoring = True
        self._set_monitoring_ui_state(True)
        
        # Start timer for consistent intervals
        self.monitoring_timer.start(self.monitoring_interval)
        
        # Start initial data collection immediately
        success = self.battery_service.start_battery_monitoring(self.device_id)
        
        if success:
            self.monitoring_started.emit()
            
            # Add system log
            if self.main_controller:
                self.main_controller.add_system_log("INFO", "Battery monitoring started")
        else:
            logger.error("Failed to start battery monitoring")
            # Rollback on failure
            self.is_monitoring = False
            self._set_monitoring_ui_state(False)
            self.monitoring_timer.stop()
        
        return success
    
    def stop_monitoring(self):
        """Stop battery monitoring"""
        if not self.is_monitoring:
            logger.debug("No battery monitoring to stop")
            return
        
        logger.info(f"Stopping battery monitoring for device: {self.device_id}")
        
        # Stop monitoring timer
        self.monitoring_timer.stop()
        
        # Stop battery service
        if self.battery_service:
            self.battery_service.stop_battery_monitoring(self.device_id)
        
        # Update state
        self.is_monitoring = False
        
        # Update UI state
        self._set_monitoring_ui_state(False)
        
        # Close CSV file if logging was enabled
        self._close_csv_logging()
        
        # Add system log
        if self.main_controller:
            self.main_controller.add_system_log("INFO", "Battery monitoring stopped")
        
        self.monitoring_completed.emit()
    
    def get_single_reading(self):
        """Get a single battery reading without continuous monitoring"""
        logger.info(f"get_single_reading called - is_monitoring: {self.is_monitoring}")
        
        # Only check manager monitoring state, not service state
        # (service may temporarily set is_monitoring=True during single reading)
        if self.is_monitoring:
            logger.warning(f"Cannot get single reading while continuous monitoring is active")
            return False
        
        logger.info("Getting single battery reading")
        
        # Set single reading mode flag
        self._single_reading_mode = True
        
        # Update status
        self._update_status_display("Getting battery information...")
        
        # Request single reading
        logger.info(f"Calling battery_service.get_battery_info_once with device_id: {self.device_id}")
        success = self.battery_service.get_battery_info_once(self.device_id)
        logger.info(f"battery_service.get_battery_info_once returned: {success}")
        
        if not success:
            self._update_status_display("Failed to start battery reading")
            self._single_reading_mode = False  # Reset flag on failure
            
        return success
    
    def refresh_once(self):
        """Refresh battery data once (alias for get_single_reading)"""
        logger.info("=== REFRESH ONCE BUTTON CLICKED ===")
        logger.info(f"Device ID: {self.device_id}")
        logger.info(f"Current monitoring state: {self.is_monitoring}")
        logger.info(f"Battery service available: {self.battery_service is not None}")
        
        try:
            result = self.get_single_reading()
            logger.info(f"get_single_reading returned: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in refresh_once: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def set_monitoring_interval(self, interval_ms: int):
        """
        Set monitoring interval in milliseconds
        
        Args:
            interval_ms: Interval in milliseconds (minimum 3000ms)
        """
        if interval_ms < 3000:
            interval_ms = 3000  # Minimum 3 seconds
        
        self.monitoring_interval = interval_ms
        
        if self.is_monitoring:
            self.monitoring_timer.setInterval(interval_ms)
        
        logger.debug(f"Battery monitoring interval set to {interval_ms}ms")
    
    def _on_interval_changed(self, value):
        """
        Handle interval spinbox value change
        
        Args:
            value: New interval value in seconds
        """
        interval_ms = value * 1000  # Convert seconds to milliseconds
        self.set_monitoring_interval(interval_ms)
    
    def _set_monitoring_ui_state(self, monitoring: bool):
        """
        Update UI state based on monitoring status
        
        Args:
            monitoring: True if monitoring is active
        """
        if "monitor_button" in self.ui_components:
            button = self.ui_components["monitor_button"]
            if monitoring:
                button.setText("Stop Monitoring")
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #D32F2F;
                        color: white;
                        border: none;
                        padding: 6px 15px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #F44336;
                    }
                """)
            else:
                button.setText("Start Monitoring")
                button.setStyleSheet("""
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
                """)
        
        # Update status display
        if monitoring:
            self._update_status_display("Monitoring active...")
        else:
            self._update_status_display("Ready")
    
    def _update_status_display(self, status: str):
        """Update status label"""
        if "status_label" in self.ui_components:
            label = self.ui_components["status_label"]
            label.setText(status)
            
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        logger.debug(f"[{timestamp}] Battery monitor status: {status}")
    
    def _update_battery_display(self, battery_data: Dict[str, Any]):
        """
        Update battery information display
        
        Args:
            battery_data: Dictionary containing battery information
        """
        try:
            # Update voltage - check both possible keys
            voltage = battery_data.get("voltage")
            if voltage is not None and "voltage_label" in self.ui_components:
                self.ui_components["voltage_label"].setText(f"{voltage:.2f} V")
                logger.debug(f"Updated voltage display: {voltage:.2f} V")
            elif "voltage_label" in self.ui_components:
                self.ui_components["voltage_label"].setText("-- V")
                logger.debug("No voltage data available, showing placeholder")
            
            # Update current - check both possible keys
            current = battery_data.get("current")
            if current is not None and "current_label" in self.ui_components:
                self.ui_components["current_label"].setText(f"{current:.2f} A")
                logger.debug(f"Updated current display: {current:.2f} A")
            elif "current_label" in self.ui_components:
                self.ui_components["current_label"].setText("-- A")
                logger.debug("No current data available, showing placeholder")
            
            # Update temperature
            if "temperature" in battery_data and "temperature_label" in self.ui_components:
                temperature = battery_data["temperature"]
                if temperature is not None:
                    self.ui_components["temperature_label"].setText(f"{temperature:.1f} °C")
                else:
                    self.ui_components["temperature_label"].setText("-- °C")
            
            # Update battery level
            if "relative_state" in battery_data and "battery_level_label" in self.ui_components:
                level = battery_data["relative_state"]
                if level is not None:
                    self.ui_components["battery_level_label"].setText(f"{level}%")
                    
                    # Update progress bar if available
                    if "progress_bar" in self.ui_components:
                        progress_bar = self.ui_components["progress_bar"]
                        progress_bar.setValue(level)
                else:
                    self.ui_components["battery_level_label"].setText("--%")
                    if "progress_bar" in self.ui_components:
                        self.ui_components["progress_bar"].setValue(0)
            
            # Update LED status
            if "led_status" in battery_data and "led_status_label" in self.ui_components:
                led_status = battery_data["led_status"]
                if led_status is not None:
                    led_status_str = str(led_status).lower()
                    self.ui_components["led_status_label"].setText(str(led_status))
                    
                    # Set color based on LED status string (matching actual LED colors)
                    # Check for specific colors first, then add blinking decoration if needed
                    color_style = ""
                    if "off" in led_status_str:
                        # Gray for Off state
                        color_style = "color: #888888; font-weight: bold;"
                    elif "blue" in led_status_str:
                        # Blue for Blue LED states
                        color_style = "color: #2196F3; font-weight: bold;"
                    elif "green" in led_status_str:
                        # Green for Green LED states
                        color_style = "color: #4CAF50; font-weight: bold;"
                    elif "cyan" in led_status_str:
                        # Cyan for Cyan LED states
                        color_style = "color: #00BCD4; font-weight: bold;"
                    elif "red" in led_status_str:
                        # Red for Red LED states
                        color_style = "color: #F44336; font-weight: bold;"
                    elif "fuchsia" in led_status_str or "magenta" in led_status_str:
                        # Fuchsia/Magenta for Fuchsia LED states
                        color_style = "color: #E91E63; font-weight: bold;"
                    elif "orange" in led_status_str:
                        # Orange for Orange LED states
                        color_style = "color: #FF9800; font-weight: bold;"
                    elif "white" in led_status_str:
                        # White for White LED states
                        color_style = "color: #FFFFFF; font-weight: bold;"
                    else:
                        # Default white for unknown states
                        color_style = "color: white;"
                    
                    # Add blinking decoration if it's a blinking state
                    if "blinking" in led_status_str:
                        color_style += " text-decoration: underline;"
                    
                    self.ui_components["led_status_label"].setStyleSheet(color_style)
                else:
                    self.ui_components["led_status_label"].setText("--")
                    self.ui_components["led_status_label"].setStyleSheet("color: #888888;")
            
            # Update interrupt status
            if "interrupt_status" in battery_data and "interrupt_status_label" in self.ui_components:
                interrupt_status = battery_data["interrupt_status"]
                if interrupt_status is not None:
                    self.ui_components["interrupt_status_label"].setText(str(interrupt_status))
                else:
                    self.ui_components["interrupt_status_label"].setText("--")
            
            # Update Battery status
            if "battery_status" in battery_data and "battery_status_label" in self.ui_components:
                battery_status = battery_data["battery_status"]
                if battery_status is not None:
                    battery_status_str = str(battery_status).lower()
                    self.ui_components["battery_status_label"].setText(str(battery_status))
                    
                    # Set color based on Battery status string
                    if "charging" in battery_status_str:
                        # Green for Charging states
                        self.ui_components["battery_status_label"].setStyleSheet("color: #4CAF50; font-weight: bold;")
                    elif "discharging" in battery_status_str:
                        # Red for Discharging state
                        self.ui_components["battery_status_label"].setStyleSheet("color: #F44336; font-weight: bold;")
                    elif "full charged" in battery_status_str:
                        # Blue for Full Charged state
                        self.ui_components["battery_status_label"].setStyleSheet("color: #2196F3; font-weight: bold;")
                    elif "over" in battery_status_str:
                        # Orange for Over states (Over Charged, Over Temperature, etc.)
                        self.ui_components["battery_status_label"].setStyleSheet("color: #FF9800; font-weight: bold;")
                    elif "alarm" in battery_status_str:
                        # Yellow for Alarm states
                        self.ui_components["battery_status_label"].setStyleSheet("color: #FFC107; font-weight: bold;")
                    elif "terminate" in battery_status_str:
                        # Purple for Terminate Charge
                        self.ui_components["battery_status_label"].setStyleSheet("color: #9C27B0; font-weight: bold;")
                    else:
                        # Default white for unknown states
                        self.ui_components["battery_status_label"].setStyleSheet("color: white;")
                else:
                    self.ui_components["battery_status_label"].setText("--")
                    self.ui_components["battery_status_label"].setStyleSheet("color: #888888;")
            
            # Update CPU usage
            if "cpu_usage" in battery_data and "cpu_usage_label" in self.ui_components:
                cpu_usage = battery_data["cpu_usage"]
                if cpu_usage is not None:
                    self.ui_components["cpu_usage_label"].setText(f"{cpu_usage:.1f}%")
                    logger.debug(f"Updated CPU usage display: {cpu_usage:.1f}%")
                else:
                    self.ui_components["cpu_usage_label"].setText("--%")
                    logger.debug("No CPU usage data available, showing placeholder")
            
            # Update Memory usage
            if "memory_usage" in battery_data and "memory_usage_label" in self.ui_components:
                memory_usage = battery_data["memory_usage"]
                if memory_usage is not None:
                    self.ui_components["memory_usage_label"].setText(f"{memory_usage:.1f}%")
                    logger.debug(f"Updated Memory usage display: {memory_usage:.1f}%")
                else:
                    self.ui_components["memory_usage_label"].setText("--%")
                    logger.debug("No memory usage data available, showing placeholder")
            
        except Exception as e:
            logger.error(f"Error updating battery display: {str(e)}")
    
    def _on_monitoring_timer(self):
        """Handle monitoring timer timeout"""
        if self.is_monitoring:
            logger.debug("Battery monitoring timer triggered")
            
            # Check if battery service is currently processing a request
            # to avoid overlapping requests
            if hasattr(self.battery_service, '_is_processing') and self.battery_service._is_processing:
                logger.debug("Battery service is processing, skipping this timer trigger")
                return
                
            self.battery_service.start_battery_monitoring(self.device_id)
    
    @Slot(str, dict)
    def _on_battery_info_received(self, device_id: str, battery_info: Dict[str, Any]):
        """
        Handle battery information received
        
        Args:
            device_id: Device ID
            battery_info: Dictionary containing battery information
        """
        if device_id != self.device_id:
            return
        
        logger.info(f"Battery info received: {battery_info}")
        
        # Store current data
        self.current_battery_data = battery_info.copy()
        
        # Check if this is from a single reading operation
        is_single_reading = getattr(self, '_single_reading_mode', False)
        
        # Sync monitoring state with battery service, but only for continuous monitoring
        if hasattr(self.battery_service, 'is_monitoring') and not is_single_reading:
            service_monitoring = self.battery_service.is_monitoring
            if self.is_monitoring != service_monitoring:
                logger.debug(f"Syncing monitoring state: manager={self.is_monitoring}, service={service_monitoring}")
                self.is_monitoring = service_monitoring
                self._set_monitoring_ui_state(self.is_monitoring)
                
                # If service stopped monitoring, emit completion signal
                if not service_monitoring and not self.is_monitoring:
                    logger.debug("Continuous monitoring completed, service monitoring stopped")
                    self.monitoring_completed.emit()
        elif is_single_reading:
            # For single reading, ensure we don't switch to monitoring mode
            logger.debug("Single reading completed, maintaining non-monitoring state")
            self._single_reading_mode = False  # Reset the flag
            
            # Force service to stop monitoring after single reading
            if hasattr(self.battery_service, 'is_monitoring') and self.battery_service.is_monitoring:
                logger.debug("Forcing service to stop monitoring after single reading")
                self.battery_service.stop_battery_monitoring(self.device_id)
        
        # Add timestamp and store in history
        timestamped_data = battery_info.copy()
        timestamped_data["timestamp"] = datetime.datetime.now()
        self.battery_history.append(timestamped_data)
        
        # Limit history size
        if len(self.battery_history) > self.max_history_entries:
            self.battery_history.pop(0)
        
        # Update UI display
        self._update_battery_display(battery_info)
        
        # Update chart if available
        if self.chart_widget:
            self.chart_widget.add_data_point(battery_info)
        
        # Log to CSV if enabled
        self._log_battery_data_to_csv(battery_info)
        
        # Update status
        self._update_status_display(f"Last updated: {datetime.datetime.now().strftime('%H:%M:%S')}")
        
        # Note: Timer is now running at fixed intervals, no need to restart it here
    
    @Slot(str, str)
    def _on_battery_info_error(self, device_id: str, error_message: str):
        """
        Handle battery information error
        
        Args:
            device_id: Device ID
            error_message: Error message
        """
        if device_id != self.device_id:
            return
        
        logger.error(f"Battery info error: {error_message}")
        
        # Check if device is disconnected and monitoring is active
        if "No response received from device" in error_message and self.is_monitoring:
            logger.warning("Device disconnected during monitoring, stopping battery monitoring")
            
            # Stop monitoring automatically
            self.stop_monitoring()
            
            # Show message box to inform user about device disconnection
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Device Disconnected")
            msg_box.setText("Device disconnected, battery monitoring stopped automatically.")
            msg_box.setInformativeText("Please check device connection status.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Apply dark theme style to message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: white;
                    border: 1px solid #555555;
                }
                QMessageBox QLabel {
                    color: white;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #0078D7;
                    color: white;
                    border: none;
                    padding: 6px 15px;
                    border-radius: 3px;
                    min-width: 70px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #1C97EA;
                }
                QMessageBox QPushButton:pressed {
                    background-color: #005A9E;
                }
            """)
            
            msg_box.exec()
            
            # Add system log
            if self.main_controller:
                self.main_controller.add_system_log("WARNING", "Device disconnected, battery monitoring stopped automatically")
            
            return
        
        # Update status display
        self._update_status_display(f"Error: {error_message}")
        
        # Emit error signal
        self.monitoring_error.emit(error_message)
        
        # Note: Timer continues running at fixed intervals, will retry on next trigger
    
    @Slot(str, str, str)
    def _on_battery_command_executed(self, device_id: str, command_name: str, command: str):
        """
        Handle battery command executed
        
        Args:
            device_id: Device ID
            command_name: Command name
            command: Command string
        """
        if device_id != self.device_id:
            return
        
        logger.debug(f"Battery command executed: {command_name}")
        
        # Update status to show current operation
        self._update_status_display(f"Reading {command_name}...")
    
    def get_current_battery_data(self) -> Dict[str, Any]:
        """
        Get current battery data
        
        Returns:
            Dictionary containing current battery information
        """
        return self.current_battery_data.copy()
    
    def get_battery_history(self) -> list:
        """
        Get battery history data
        
        Returns:
            List of historical battery data with timestamps
        """
        return self.battery_history.copy()
    
    def export_battery_data(self) -> Dict[str, Any]:
        """
        Export battery data for reporting
        
        Returns:
            Dictionary containing current data and history
        """
        return {
            "device_id": self.device_id,
            "current_data": self.current_battery_data,
            "history": self.battery_history,
            "export_timestamp": datetime.datetime.now().isoformat()
        }
    
    def cleanup(self):
        """Clean up resources"""
        # Stop monitoring
        if self.is_monitoring:
            self.stop_monitoring()
        
        # Disconnect signals
        try:
            self.battery_service.battery_info_received.disconnect(self._on_battery_info_received)
            self.battery_service.battery_info_error.disconnect(self._on_battery_info_error)
            self.battery_service.battery_command_executed.disconnect(self._on_battery_command_executed)
        except Exception:
            pass
        
        # Clear data
        self.current_battery_data = {}
        self.battery_history = []
        
        # Clear CSV data cache
        self.csv_data_cache = {
            "relative_state": "",
            "voltage": "",
            "current": "",
            "temperature": "",
            "led_status": "",
            "interrupt_status": "",
            "battery_status": "",
            "cpu_usage": "",
            "memory_usage": ""
        }
        
        logger.info("Battery Monitor Manager cleaned up")
    
    def _check_and_setup_csv_logging(self):
        """Check if CSV logging checkbox is checked and setup CSV file"""
        if "log_as_file_checkbox" in self.ui_components:
            checkbox = self.ui_components["log_as_file_checkbox"]
            if checkbox.isChecked():
                self._setup_csv_logging()
                logger.info("CSV logging enabled for battery monitoring")
            else:
                self.csv_logging_enabled = False
                logger.info("CSV logging disabled for battery monitoring")
        else:
            self.csv_logging_enabled = False
            logger.debug("No CSV logging checkbox found")
    
    def _setup_csv_logging(self):
        """Setup CSV file for battery data logging"""
        try:
            # Generate timestamp-based filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Save directly in the root directory
            self.csv_file_path = f"battery_monitor_{self.device_id}_{timestamp}.csv"
            
            # Open CSV file and create writer
            self.csv_file = open(self.csv_file_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Write CSV header
            header = [
                'Timestamp',
                'Relative State (%)',
                'Voltage (V)',
                'Current (A)',
                'Temperature (°C)',
                'LED Status',
                'Interrupt Status',
                'Battery Status',
                'CPU Usage (%)',
                'Memory Usage (%)'
            ]
            self.csv_writer.writerow(header)
            self.csv_file.flush()
            
            self.csv_logging_enabled = True
            logger.info(f"CSV logging setup complete: {self.csv_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup CSV logging: {str(e)}")
            self.csv_logging_enabled = False
            self._close_csv_logging()
    
    def _close_csv_logging(self):
        """Close CSV file and cleanup"""
        if self.csv_file:
            try:
                self.csv_file.close()
                logger.info(f"CSV file closed: {self.csv_file_path}")
            except Exception as e:
                logger.error(f"Error closing CSV file: {str(e)}")
            finally:
                self.csv_file = None
                self.csv_writer = None
                self.csv_file_path = None
                self.csv_logging_enabled = False
                
                # Clear CSV data cache when closing
                self.csv_data_cache = {
                    "relative_state": "",
                    "voltage": "",
                    "current": "",
                    "temperature": "",
                    "led_status": "",
                    "interrupt_status": "",
                    "battery_status": "",
                    "cpu_usage": "",
                    "memory_usage": ""
                }
    
    def _log_battery_data_to_csv(self, battery_data: Dict[str, Any]):
        """Log battery data to CSV file with caching for empty values"""
        if not self.csv_logging_enabled or not self.csv_writer:
            return
        
        try:
            # Get current timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Extract data and use cache for empty values
            data_fields = ["relative_state", "voltage", "current", "temperature", 
                          "led_status", "interrupt_status", "battery_status", "cpu_usage", "memory_usage"]
            
            processed_data = {}
            
            for field in data_fields:
                current_value = battery_data.get(field, "")
                
                # Check if current value is valid (not None, not empty string, and not just whitespace)
                # Note: 0, 0.0, False are valid values, so we need to check specifically for None and empty strings
                if current_value is not None and str(current_value).strip() != "":
                    # Valid value: update cache and use current value
                    self.csv_data_cache[field] = str(current_value).strip()
                    processed_data[field] = self.csv_data_cache[field]
                    logger.debug(f"Updated cache for {field}: {self.csv_data_cache[field]}")
                else:
                    # Empty or invalid value: use cached value
                    processed_data[field] = self.csv_data_cache[field]
                    if self.csv_data_cache[field]:
                        logger.debug(f"Using cached value for {field}: {self.csv_data_cache[field]}")
                    else:
                        logger.debug(f"No cached value available for {field}, using empty string")
            
            # Write data row
            row = [
                timestamp,
                processed_data["relative_state"],
                processed_data["voltage"],
                processed_data["current"],
                processed_data["temperature"],
                processed_data["led_status"],
                processed_data["interrupt_status"],
                processed_data["battery_status"],
                processed_data["cpu_usage"],
                processed_data["memory_usage"]
            ]
            
            self.csv_writer.writerow(row)
            self.csv_file.flush()  # Ensure data is written immediately
            
            logger.debug(f"Battery data logged to CSV: {timestamp}")
            
        except Exception as e:
            logger.error(f"Error logging battery data to CSV: {str(e)}")
            # Disable CSV logging on error to prevent spam
            self.csv_logging_enabled = False 