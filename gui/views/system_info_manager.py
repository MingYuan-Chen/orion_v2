"""
System information manager view module
Responsible for displaying and updating system information
"""
from typing import Dict, Any
import datetime
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton

from util.logger import logger
from core.services.system_info import SystemInfoService


class SystemInfoManagerView(QObject):
    """
    System information manager view class
    Responsible for displaying and updating system information
    """
    
    # Define signals
    info_update_started = Signal()
    info_update_completed = Signal()
    info_update_error = Signal(str)  # error_message
    
    def __init__(self, device_id: str, system_info_service: SystemInfoService):
        """
        Initialize system information manager view
        
        Args:
            device_id: Device ID
            system_info_service: System information service
        """
        super().__init__()
        
        # Save device ID and system info service
        self.device_id = device_id
        self.system_info_service = system_info_service
        
        # UI components references
        self.ui_components = {}
        
        # Update status
        self.is_updating = False
        
        # Connect signals
        self._connect_signals()
        
        logger.info("System information manager view initialized")
    
    def _connect_signals(self):
        """Connect system info service signals"""
        if self.system_info_service:
            self.system_info_service.info_received.connect(self._on_system_info_received)
            self.system_info_service.info_error.connect(self._on_system_info_error)
    
    def set_ui_components(self, components: Dict[str, Any]):
        """
        Set UI components references
        
        Args:
            components: Dictionary of UI components
                {
                    "refresh_button": QPushButton,
                    "last_updated_label": QLabel,
                    
                    # System basic info
                    "model_name": QLabel,
                    "serial_number": QLabel,
                    "cpu": QLabel,
                    "memory": QLabel,
                    "storage": QLabel,
                    
                    # Battery info
                    "battery_model": QLabel,
                    "battery_serial": QLabel,
                    "charge_progress": QProgressBar,
                    "charge": QLabel,
                    "voltage": QLabel,
                    "current": QLabel,
                    "temperature": QLabel,
                }
        """
        self.ui_components = components
        
        # Connect refresh button
        if "refresh_button" in components and isinstance(components["refresh_button"], QPushButton):
            components["refresh_button"].clicked.connect(self.refresh_system_info)
        
        # Set initializing state
        self.set_initializing_state()
    
    def set_initializing_state(self):
        """Set all system info display to initializing state"""
        # System basic info
        if "model_name" in self.ui_components:
            self.ui_components["model_name"].setText("...")
        if "serial_number" in self.ui_components:
            self.ui_components["serial_number"].setText("...")
        if "cpu" in self.ui_components:
            self.ui_components["cpu"].setText("Initializing...")
        if "memory" in self.ui_components:
            self.ui_components["memory"].setText("Initializing...")
        if "storage" in self.ui_components:
            self.ui_components["storage"].setText("Initializing...")
        
        # Battery info
        if "battery_model" in self.ui_components:
            self.ui_components["battery_model"].setText("...")
        if "battery_serial" in self.ui_components:
            self.ui_components["battery_serial"].setText("...")
        if "charge_progress" in self.ui_components:
            self.ui_components["charge_progress"].setValue(0)
        if "charge" in self.ui_components:
            self.ui_components["charge"].setText("Initializing...")
        if "voltage" in self.ui_components:
            self.ui_components["voltage"].setText("Initializing...")
        if "current" in self.ui_components:
            self.ui_components["current"].setText("Initializing...")
        if "temperature" in self.ui_components:
            self.ui_components["temperature"].setText("Initializing...")
    
    def refresh_system_info(self):
        """Refresh system information"""
        # If already updating, ignore this click
        if self.is_updating:
            return
        
        self.is_updating = True
        logger.info(f"Refreshing system info for {self.device_id}...")
        
        # Emit update started signal
        self.info_update_started.emit()
        
        # Update timestamp, add updating mark
        if "last_updated_label" in self.ui_components:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.ui_components["last_updated_label"].setText(f"Last updated: {current_time} (updating...)")
        
        # Request system info update
        if self.system_info_service:
            # Ensure update_system_info method exists
            if hasattr(self.system_info_service, 'update_system_info'):
                logger.info(f"Trigger system info service update, device ID: {self.device_id}")
                self.system_info_service.update_system_info(self.device_id)
            else:
                logger.error("system_info_service does not have update_system_info method")
                self._handle_update_completed()
        else:
            logger.warning("system_info_service not found, using simulated data")
            # If no system info service, wait a while then restore button status
            QTimer.singleShot(2000, self._handle_update_completed)
    
    def _handle_update_completed(self):
        """Handle system info update completed"""
        # Restore status
        self.is_updating = False
        
        # Emit update completed signal
        self.info_update_completed.emit()
        
        # Update timestamp
        if "last_updated_label" in self.ui_components:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.ui_components["last_updated_label"].setText(f"Last updated: {current_time}")
    
    @Slot(str, dict)
    def _on_system_info_received(self, device_id, system_info):
        """
        Handle system info received event
        
        Args:
            device_id: Device ID
            system_info: System information dictionary
        """
        # Only process current device info
        if device_id != self.device_id:
            return
        
        # Update UI with received data
        self._update_system_info_display(system_info)
        
        # Mark update as completed
        self._handle_update_completed()
        
        logger.info("System info update completed")
    
    @Slot(str, str)
    def _on_system_info_error(self, device_id, error_message):
        """
        Handle system info error event
        
        Args:
            device_id: Device ID
            error_message: Error message
        """
        # Only process current device info
        if device_id != self.device_id:
            return
        
        # Emit error signal
        self.info_update_error.emit(error_message)
        
        # Restore status
        self.is_updating = False
        
        # Update timestamp
        if "last_updated_label" in self.ui_components:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.ui_components["last_updated_label"].setText(f"Last updated: {current_time} (failed)")
        
        logger.error(f"System info update failed: {error_message}")
    
    def _update_system_info_display(self, system_info: Dict[str, Any]):
        """
        Update system information display
        
        Args:
            system_info: System information dictionary
        """
        # CPU info
        if "cpu" in system_info and "model" in system_info["cpu"] and "cpu" in self.ui_components:
            self.ui_components["cpu"].setText(system_info["cpu"]["model"])
        
        # Memory info
        if "memory" in system_info and "memory" in self.ui_components:
            mem_info = system_info["memory"]
            if "total" in mem_info and "used" in mem_info:
                mem_text = f"{mem_info['total']} ({mem_info['used']} Used)"
                self.ui_components["memory"].setText(mem_text)
        
        # Storage info
        if "storage" in system_info and "storage" in self.ui_components:
            storage_info = system_info["storage"]
            if "total" in storage_info and "available" in storage_info:
                storage_text = f"{storage_info['total']} ({storage_info['available']} Available)"
                self.ui_components["storage"].setText(storage_text)
        
        # Battery info
        if "battery" in system_info:
            battery_info = system_info["battery"]
            
            # Battery charge percentage
            if "relative_state" in battery_info and "charge" in self.ui_components:
                percentage = battery_info["relative_state"]
                self.ui_components["charge"].setText(f"{percentage}%")
                
                # Update progress bar if available
                if "charge_progress" in self.ui_components:
                    self.ui_components["charge_progress"].setValue(int(percentage))
            
            # Charging voltage
            if "charging_voltage" in battery_info and "voltage" in self.ui_components:
                voltage = battery_info["charging_voltage"]
                self.ui_components["voltage"].setText(f"{voltage} V")
            
            # Charging current
            if "charging_current" in battery_info and "current" in self.ui_components:
                current = battery_info["charging_current"]
                self.ui_components["current"].setText(f"{current} mA")
            
            # Battery temperature
            if "temperature" in battery_info and "temperature" in self.ui_components:
                temperature = battery_info["temperature"]
                self.ui_components["temperature"].setText(f"{temperature} °C")
    
    def update_model_name(self, name: str):
        """
        Update model name
        
        Args:
            name: Model name
        """
        if "model_name" in self.ui_components:
            self.ui_components["model_name"].setText(name)
    
    def update_serial_number(self, serial: str):
        """
        Update serial number
        
        Args:
            serial: Serial number
        """
        if "serial_number" in self.ui_components:
            self.ui_components["serial_number"].setText(serial)
    
    def update_battery_model(self, model: str):
        """
        Update battery model
        
        Args:
            model: Battery model
        """
        if "battery_model" in self.ui_components:
            self.ui_components["battery_model"].setText(model)
    
    def update_battery_serial(self, serial: str):
        """
        Update battery serial
        
        Args:
            serial: Battery serial
        """
        if "battery_serial" in self.ui_components:
            self.ui_components["battery_serial"].setText(serial)
    
    def cleanup(self):
        """Clean up system info manager resources"""
        try:
            logger.debug("Cleaning up SystemInfoManagerView resources")
            
            # Disconnect signals
            if self.system_info_service:
                try:
                    self.system_info_service.info_received.disconnect(self._on_system_info_received)
                    self.system_info_service.info_error.disconnect(self._on_system_info_error)
                except Exception:
                    # Signals may already be disconnected
                    pass
            
            # Clear references
            self.ui_components = {}
            
        except Exception as e:
            logger.error(f"Error during SystemInfoManagerView cleanup: {e}") 