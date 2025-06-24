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
            self.system_info_service.command_executed.connect(self._on_command_executed)
    
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
                    "voltage": QLabel,
                    "current": QLabel,
                    "design_voltage": QLabel,
                    "design_capacity": QLabel,
                }
        """
        self.ui_components = components
        
        # no longer connect the refresh button directly, let main_window.py handle the pre-check
        # Connect refresh button
        # if "refresh_button" in components and isinstance(components["refresh_button"], QPushButton):
        #     components["refresh_button"].clicked.connect(self.refresh_system_info)
        
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
            self.ui_components["cpu"].setText("...")
        if "memory" in self.ui_components:
            self.ui_components["memory"].setText("...")
        if "storage" in self.ui_components:
            self.ui_components["storage"].setText("...")
        
        # Battery info
        if "battery_model" in self.ui_components:
            self.ui_components["battery_model"].setText("...")
        if "battery_serial" in self.ui_components:
            self.ui_components["battery_serial"].setText("...")
        if "voltage" in self.ui_components:
            self.ui_components["voltage"].setText("...")
        if "current" in self.ui_components:
            self.ui_components["current"].setText("...")
        if "design_voltage" in self.ui_components:
            self.ui_components["design_voltage"].setText("...")
        if "design_capacity" in self.ui_components:
            self.ui_components["design_capacity"].setText("...")
    
    def refresh_system_info(self):
        """Refresh system information"""
        # If already updating, ignore this click
        if self.is_updating:
            return
        
        # 设置更新状态
        self.is_updating = True
        
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
                # Only record debug information
                logger.debug(f"Trigger system info service update, device ID: {self.device_id}")
                # Start system info update
                update_success = self.system_info_service.update_system_info(self.device_id)
                
                # If update did not start successfully, complete directly
                if not update_success:
                    logger.warning("System info update did not start successfully")
                    self._handle_update_completed()
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
            
        # MainWindowController has already recorded the system info update completed message
        # so here we don't add duplicate logs, only record debug information
        logger.debug(f"System info update completed for {self.device_id}")
    
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
        
        # Update firmware and OS information if available
        if "firmware_os" in system_info:
            self._update_firmware_os_display(system_info["firmware_os"])
        
        # get the cpu model information
        cpu_model = system_info.get('cpu', {}).get('model', 'N/A')
        
        # only record detailed information at debug level
        logger.debug(f"System info received for {device_id} - CPU: {cpu_model}")
        
        # Mark update as completed
        self._handle_update_completed()
    
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
        
        # only add to system log, not use logger to record duplicate information
        error_msg = f"System info update failed: {error_message}"
        if hasattr(self, 'add_system_log'):
            self.add_system_log("ERROR", error_msg)
        else:
            # only use logger when there is no add_system_log method
            logger.error(error_msg)
    
    def _update_system_info_display(self, system_info: Dict[str, Any]):
        """
        Update system information display
        
        Args:
            system_info: System information dictionary
        """
        logger.debug(f"Updating system info display with data: {system_info}")
        
        # CPU info
        if "cpu" in system_info and "model" in system_info["cpu"] and "cpu" in self.ui_components:
            cpu_model = system_info["cpu"]["model"]
            logger.debug(f"Updating CPU info: {cpu_model}")
            self.ui_components["cpu"].setText(cpu_model)
            logger.debug("CPU info updated in UI")
        else:
            logger.debug(f"CPU info not updated - cpu in system_info: {'cpu' in system_info}, "
                        f"model in cpu: {'model' in system_info.get('cpu', {})}, "
                        f"cpu in ui_components: {'cpu' in self.ui_components}")
        
        # Memory info
        if "memory" in system_info and "memory" in self.ui_components:
            mem_info = system_info["memory"]
            if "total" in mem_info and "used" in mem_info:
                mem_text = f"{mem_info['total']} ({mem_info['used']} Used)"
                logger.debug(f"Updating memory info: {mem_text}")
                self.ui_components["memory"].setText(mem_text)
        
        # Storage info
        if "storage" in system_info and "storage" in self.ui_components:
            storage_info = system_info["storage"]
            if "total" in storage_info and "available" in storage_info:
                storage_text = f"{storage_info['total']} ({storage_info['available']} Available)"
                logger.debug(f"Updating storage info: {storage_text}")
                self.ui_components["storage"].setText(storage_text)
        
        # Battery info
        if "battery" in system_info:
            battery_info = system_info["battery"]
            logger.debug(f"Updating battery info: {battery_info}")
            
            # Voltage (prefer charging_voltage, fallback to voltage)
            voltage_value = None
            if "charging_voltage" in battery_info:
                voltage_value = battery_info["charging_voltage"]
            elif "voltage" in battery_info:
                voltage_value = battery_info["voltage"]
            
            if voltage_value is not None and "voltage" in self.ui_components:
                self.ui_components["voltage"].setText(f"{voltage_value} V")
            
            # Current (prefer charging_current, fallback to current)
            current_value = None
            if "charging_current" in battery_info:
                current_value = battery_info["charging_current"]
            elif "current" in battery_info:
                current_value = battery_info["current"]
            
            if current_value is not None and "current" in self.ui_components:
                self.ui_components["current"].setText(f"{current_value} A")
            
            # Design voltage
            if "design_voltage" in battery_info and "design_voltage" in self.ui_components:
                design_voltage = battery_info["design_voltage"]
                self.ui_components["design_voltage"].setText(f"{design_voltage} V")
            
            # Design capacity
            if "design_capacity" in battery_info and "design_capacity" in self.ui_components:
                design_capacity = battery_info["design_capacity"]
                self.ui_components["design_capacity"].setText(f"{design_capacity} mAh")
    
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
    
    def _update_firmware_os_display(self, firmware_os_info: Dict[str, Any]):
        """
        Update firmware and OS information display
        
        Args:
            firmware_os_info: Firmware and OS information dictionary
        """
        # Update firmware and OS information through the main controller
        if hasattr(self, 'main_controller') and hasattr(self.main_controller, 'firmware_os_manager'):
            firmware_os_manager = self.main_controller.firmware_os_manager
            if firmware_os_manager:
                firmware_os_manager.set_firmware_os_data(firmware_os_info)
                logger.debug(f"Updated firmware and OS information: {firmware_os_info}")
    
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
    
    def edit_model_name(self):
        """Provide the full functionality of editing the model name"""
        current_text = self.ui_components["model_name"].text()
        
        # use the dialog to get the new value
        from gui.views.main_window import DarkEditDialog
        dialog = DarkEditDialog(
            self.ui_components["model_name"].window(), 
            "Edit model name",
            "Please enter the new model name:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                self.update_model_name(new_text)
                # if need to update the backend data, add the code here
                return True
        return False

    def edit_serial_number(self):
        """Provide the full functionality of editing the serial number"""
        current_text = self.ui_components["serial_number"].text()
        
        from gui.views.main_window import DarkEditDialog
        dialog = DarkEditDialog(
            self.ui_components["serial_number"].window(), 
            "Edit serial number",
            "Please enter the new serial number:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                self.update_serial_number(new_text)
                return True
        return False

    def edit_battery_model(self):
        """Provide the full functionality of editing the battery model"""
        current_text = self.ui_components["battery_model"].text()
        
        from gui.views.main_window import DarkEditDialog
        dialog = DarkEditDialog(
            self.ui_components["battery_model"].window(), 
            "Edit battery model",
            "Please enter the new battery model:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                self.update_battery_model(new_text)
                return True
        return False

    def edit_battery_serial(self):
        """Provide the full functionality of editing the battery serial number"""
        current_text = self.ui_components["battery_serial"].text()
        
        from gui.views.main_window import DarkEditDialog
        dialog = DarkEditDialog(
            self.ui_components["battery_serial"].window(), 
            "Edit battery serial number",
            "Please enter the new battery serial number:",
            current_text
        )
        
        if dialog.exec_():
            new_text = dialog.get_text()
            if new_text:
                self.update_battery_serial(new_text)
                return True
        return False

    @Slot(str, str, str)
    def _on_command_executed(self, device_id, command_name, command):
        """
        Handle command execution event
        
        Args:
            device_id: Device ID
            command_name: Command name
            command: Command string
        """
        # Only process current device info
        if device_id != self.device_id:
            return
            
        # Record executed command to system log
        if hasattr(self, 'add_system_log'):
            self.add_system_log("INFO", f"[Command][{command_name}]: {command}")
            
            # 將命令標記為已記錄，避免重複記錄
            if hasattr(self, 'main_controller') and hasattr(self.main_controller, 'mark_command_as_logged'):
                # 標記命令為已記錄
                self.main_controller.mark_command_as_logged(command) 