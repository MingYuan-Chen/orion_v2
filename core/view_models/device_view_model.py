
import sys
from typing import List, Optional, Dict
from PySide6.QtCore import QObject, Signal, Slot, Property, QStringListModel, Qt, QTimer
from core.models.serial_device_model import SerialDeviceModel
from core.services.platform_detection_service import PlatformDetectionService
from core.services.hw_config_service import HWConfigService
from util.logger import logger

class DeviceViewModel(QObject):
    """
    ViewModel for the serial device view. It mediates between the View and the Model.
    """
    def __init__(self, model: SerialDeviceModel, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._model = model
        self._command_text = ""
        self._is_connected = False
        self._platform_name = "Unknown"
        self._platform_detected = False
        self._system_info = {}
        self._system_info_service = None
        self._diagnostic_service = None
        self._battery_monitor_service = None
        self._led_worker = None
        self._backlight_worker = None
        self._battery_monitor_is_running = False
        self._network_service = None
        self._stress_test_service = None
        
        self._hw_config_list = []
        self._current_hw_config = {}
        self._hw_config_service = HWConfigService()

        # --- Port list management ---
        self._port_list_model = QStringListModel()
        self.refresh_ports()

        # --- Services ---
        self._detection_service = PlatformDetectionService(device_model=self._model)

        # --- Connect signals from the model to ViewModel slots ---
        self._model.connection_result.connect(self.on_connection_result)
        self._model.disconnection_result.connect(self.on_disconnection_result)
        self._model.data_received.connect(self.on_data_received)
        self._detection_service.platform_detected.connect(self.on_platform_detected)
        self._detection_service.login_required.connect(self.on_login_required)

    # =================================================================================
    # Signals to notify the View of property changes
    # =================================================================================
    log_text_changed = Signal()
    is_connected_changed = Signal()
    command_text_changed = Signal()
    login_required = Signal()
    platform_name_changed = Signal()
    system_info_changed = Signal(str, str)
    system_info_reset = Signal()
    system_info_keys_changed = Signal()
    open_system_info_requested = Signal()
    open_hw_config_requested = Signal()
    hw_config_list_changed = Signal()
    current_hw_config_changed = Signal()
    hw_config_reset = Signal()
    diagnostic_reset = Signal()
    
    # Diagnostic signals
    diagnostic_result = Signal(str, bool, str) # key, success, message
    diagnostic_start = Signal(str) # key
    diagnostic_step = Signal(str, str) # cmd, output
    manual_check_requested = Signal(str, str) # key, message
    all_diagnostics_completed = Signal()

    # Battery Monitor signals
    battery_data_updated = Signal(dict)

    # Signal to append log instead of full refresh
    log_appended = Signal(str)

    # LED signals
    led_status_updated = Signal(str)

    # Backlight signals
    backlight_updated = Signal(str)

    # WiFi signals
    wifi_scan_finished = Signal(list)
    wifi_connection_result = Signal(bool, str)
    wifi_status_updated = Signal(dict)
    network_status_updated = Signal(dict)

    # Stress Test signal
    stress_test_status_updated = Signal(dict)

    # =================================================================================
    # Properties accessible by the View
    # =================================================================================
    @Property(bool, notify=is_connected_changed)
    def is_connected(self) -> bool:
        return self._is_connected
    
    @Property(bool)
    def platform_detected(self) -> bool:
        return self._platform_detected

    @Property(str, notify=command_text_changed)
    def command_text(self) -> str:
        return self._command_text

    @command_text.setter
    def command_text(self, value: str):
        if self._command_text != value:
            self._command_text = value
            self.command_text_changed.emit()

    @Property(QObject, constant=True)
    def port_list_model(self) -> QStringListModel:
        return self._port_list_model

    @Property(str, notify=platform_name_changed)
    def platform_name(self) -> str:
        return self._platform_name

    @Property(dict, notify=system_info_changed)
    def system_info(self) -> dict:
        return self._system_info

    @Property(list, notify=system_info_keys_changed)
    def system_info_keys(self) -> list:
        if self._system_info_service and hasattr(self._system_info_service, 'commands'):
            return list(self._system_info_service.commands.keys())
        return []

    @Property(list, notify=hw_config_list_changed)
    def hw_config_list(self) -> list:
        return self._hw_config_list

    @Property(dict, notify=current_hw_config_changed)
    def current_hw_config(self) -> dict:
        return self._current_hw_config

    @Slot()
    def refresh_ports(self):
        """Refreshes the list of available serial ports."""
        ports = self._model.get_available_ports()
        if not ports:
            self._append_log("No serial ports found.")
            port_strings = []
        else:
            port_strings = [f"{p.device} - {p.description}" for p in sorted(ports, key=lambda p: p.device)]
        
        self._port_list_model.setStringList(port_strings)

    @Slot(str, str)
    def toggle_connection(self, port_text: str, baud_rate_text: str):
        """Connects or disconnects the device based on the current state."""
        if self._is_connected:
            if self._platform_name == "Athena":
                self.toggle_production_tool_service("start")
            self._model.disconnect_device()
        else:
            if not port_text:
                self._append_log("Please select a port.")
                return
            if not baud_rate_text:
                self._append_log("Please select a baud rate.")
                return

            try:
                baud_rate = int(baud_rate_text)
                # Extract device path from "COM3 - Description"
                port_device = port_text.split(' ')[0]
                self._append_log(f"Attempting to connect to {port_device} at {baud_rate} baud...")
                self._model.connect_device(port=port_device, baudrate=baud_rate)
            except ValueError:
                self._append_log(f"Invalid baud rate: {baud_rate_text}")

    @Slot()
    def open_system_info_view(self):
        """Opens the system info view and starts data collection."""
        self.open_system_info_requested.emit()
        self._system_info_service.collect_system_info()
    
    @Slot()
    def open_hw_config_view(self):
        """Opens the hardware config view and starts data collection."""
        self.refresh_hw_config_list()
        self.open_hw_config_requested.emit()
    
    @Slot()
    def interrupt_diagnostic(self):
        if self._diagnostic_service:
            self._diagnostic_service.disconnect()

    @Slot(str)
    def resume_diagnostic(self, result: str):
        if self._diagnostic_service:
            self._diagnostic_service.resume_diagnostic(result)

    @Slot()
    def refresh_hw_config_list(self):
        """Refreshes the list of available HW config files for the current platform."""
        # Map platform name if needed, similar to system_info_service
        mapper_folder_name = {
            "Athena": "athena",
            "Odin": "odin",
            "Gemini FHD": "gemini_fhd",
            "Gemini": "gemini",
            "Hydra FHD": "hydra_fhd",
            "Hydra": "hydra",
            "Argo": "argo"
        }
        mapped_name = mapper_folder_name.get(self._platform_name, self._platform_name.lower())
        self._hw_config_list = self._hw_config_service.get_config_files(mapped_name)
        self.hw_config_list_changed.emit()

    @Slot(str)
    def load_hw_config(self, filename: str):
        """Loads a specific HW config file."""
        self._current_hw_config = self._hw_config_service.load_config(filename)
        self.current_hw_config_changed.emit()

    @Slot(str, dict)
    def save_hw_config(self, filename: str, data: dict):
        """Saves the HW config data to a file."""
        if self._hw_config_service.save_config(filename, data):
            self.refresh_hw_config_list() # Refresh list in case it's a new file
            # If we saved to the current file, update the current config data in memory too
            # But usually the view sends the data that is already "current" in UI terms.
            # Let's update our internal state to match what was saved.
            self._current_hw_config = data
            self.current_hw_config_changed.emit()
        else:
            self._append_log(f"Failed to save HW config to {filename}")

    def start_platform_detection(self):
        """Starts the platform detection service."""
        if self._detection_service:
            self._detection_service.start_detection()
        else:
            logger.error("Detection service not initialized.")
    
    @Slot()
    def run_all_diagnostics(self):
        """Runs all diagnostics for the current platform."""
        if self._diagnostic_service:
            self._append_log("Starting diagnostics...")
            self._diagnostic_service.run_diagnostics()
        else:
            self._append_log("Diagnostic service not initialized.")

    @Slot()
    def start_battery_monitor(self, interval_ms: int = 2000):
        """Starts the battery monitor service."""
        if self._battery_monitor_service:
            self._battery_monitor_service.start_monitoring(interval_ms)
            self._append_log(f"[Notification] Started battery monitoring service.\n[Notification] System will block command message until service stops.")
            self._battery_monitor_is_running = True
        else:
            self._append_log("Battery monitor service not initialized.")

    @Slot()
    def stop_battery_monitor(self):
        """Stops the battery monitor service."""
        if self._battery_monitor_service:
            self._battery_monitor_service.stop_monitoring()
            self._battery_monitor_is_running = False
    
    @Slot(str)
    def set_led_status(self, status: str):
        """Sets the LED status via the worker."""
        if self._led_worker:
            self._led_worker.set_led_status(status)
            if status == "default":
                QTimer.singleShot(2000, self.get_led_status)

    @Slot()
    def get_led_status(self):
        """Requests the current LED status via the worker."""
        if self._led_worker:
            self._led_worker.get_led_status()

    @Slot(result=list)
    def get_available_led_commands(self) -> list:
        """Returns a list of available LED commands for the current platform."""
        if self._led_worker:
            # Access the private dictionary in LedWorker to get keys
            # This relies on LedWorker implementation details, but they are in the same module/package
            platform = self._led_worker._platform_name
            commands = self._led_worker.SET_LED_STATUS.get(platform, {})
            if not commands:
                 commands = self._led_worker.SET_LED_STATUS.get("other", {})
            return list(commands.keys())
        return []

    # --- Backlight Control Slots ---
    @Slot(str)
    def set_backlight_brightness(self, brightness: str):
        """Sets the backlight brightness."""
        if self._backlight_worker:
            self._backlight_worker.set_backlight_brightness(brightness)
            self._append_log(f"Set Backlight brightness to: {brightness}")
            # Auto-refresh status after setting
            QTimer.singleShot(500, self.get_backlight_brightness)

    @Slot()
    def get_backlight_brightness(self):
        """Requests the current backlight brightness."""
        if self._backlight_worker:
            self._backlight_worker.get_backlight_brightness()

    @Slot(bool)
    def toggle_backlight(self, on: bool):
        """Toggles the backlight on or off."""
        if self._backlight_worker:
            self._backlight_worker.toggle_backlight(on)
            self._append_log(f"Toggled Backlight {'On' if on else 'Off'}")
            QTimer.singleShot(500, self.get_backlight_status)

    @Slot()
    def get_backlight_status(self):
        """Requests the current backlight power status."""
        if self._backlight_worker:
            self._backlight_worker.get_backlight_status()
    
    @Slot()
    def init_screen_for_backlight_control(self):
        """Initializes the screen for backlight control."""
        if self._model:
            self._model.send_command_sync("/usr/bin/drawfb -p white")

    @Slot()
    def send_command(self):
        """Sends the command from the command_text property."""
        if self._command_text:
            self._append_log(f"[SEND]: {self._command_text}")
            self._model.send_command_queued(self._command_text)
            self.command_text = "" # Clear input after sending

    @Slot(bytes)
    def send_interrupt_bytes(self, interrupt_bytes: bytes):
        """Sends an interrupt byte sequence from the view."""
        if self._is_connected:
            # For logging purposes, map bytes to a friendly name
            log_message = f"[SEND]: Interrupt ({interrupt_bytes.hex()})"
            if interrupt_bytes == b'\x03':
                log_message = "[SEND]: Ctrl+C (Interrupt)"
            elif interrupt_bytes == b'\x04':
                log_message = "[SEND]: Ctrl+D (EOF)"
            elif interrupt_bytes == b'\x1b':
                log_message = "[SEND]: ESC"
            
            self._append_log(log_message)
            self._model.send_bytes_immediate(interrupt_bytes)

    @Slot(str)
    def toggle_production_tool_service(self, command: str):
        """Toggles the production tool mode."""
        if self._model and command in ["enable", "disable", "start", "stop"]:
            self._model.send_command_sync(f"systemctl {command} athena-production-tool.service")
            if command in ["enable", "disable"]:
                self._model.send_command_sync("reboot", wait_for="login:", timeout=90)
                self._model.send_command_sync("root")
    
    @Slot()
    def toggle_USBC_dmesg_disable(self):
        """Disable the USB-C dmesg."""
        if self._model:
            self._model.send_command_sync("dmesg -n 3")
    
    @Slot()
    def toggle_cursor_blink_disable(self):
        """Disable the cursor blink."""
        if self._model:
            self._model.send_command_sync("echo 0 > /sys/class/graphics/fbcon/cursor_blink")

    @Slot()
    def toggle_USB_port_power_enable(self):
        """Enable the USB port power."""
        if self._model:
            self._model.send_command_sync("echo 1 > /sys/class/gpio/usb3_1_h2_1_pwr_en/value && echo 1 > /sys/class/gpio/usb3_1_h2_2_pwr_en/value && echo 0 > /sys/class/gpio/mx8_usbc_pd/value")
            self._model.send_command_sync("mount -o remount,rw /")

    @Slot()
    def clean_up(self):
        """Should be called before application quits to ensure clean disconnection."""
        if self._platform_name == "Athena":
                self.toggle_production_tool_service("start")
        self._model.disconnect_device()

    # --- WiFi Slots ---
    
    @Slot()
    def scan_wifi(self):
        if self._network_service:
            self._network_service.scan_networks()

    @Slot(str, str)
    def connect_wifi(self, ssid: str, password: str):
        if self._network_service:
            self._network_service.connect_network(ssid, password)
            
    @Slot()
    def check_wifi_status(self):
        if self._network_service:
            self._network_service.check_status()

    @Slot()
    def check_network_status(self):
        """Checks both Ethernet and WiFi status."""
        if self._network_service:
            self._network_service.check_network_status()



    # =================================================================================
    # Private slots to handle signals from the Model and Services
    # =================================================================================
    @Slot(bool, str)
    def on_connection_result(self, success: bool, message: str):
        self._append_log(message)
        if success != self._is_connected:
            self._is_connected = success
            self.is_connected_changed.emit()

    @Slot(bool, str)
    def on_disconnection_result(self, success: bool, message: str):
        self._append_log(message)
        # Stop detection service regardless of disconnection success
        if self._detection_service:
            self._detection_service.stop_detection()
        if self._system_info_service:
            self._system_info_service.stop_collection()
        if self._diagnostic_service:
            self._diagnostic_service.disconnect()
        if self._battery_monitor_service:
            self._battery_monitor_service.stop_monitoring()
        
        # Only update state if disconnection was successful or wasn't already disconnected
        if success and self._is_connected:
            self._is_connected = False
            self._platform_detected = False
            self.is_connected_changed.emit()
            self._system_info.clear()
            self.system_info_reset.emit()
            self.hw_config_reset.emit()
            self.diagnostic_reset.emit()
        
        # Reset platform name on disconnect
        self.on_platform_detected("Unknown")

    @Slot(str)
    def on_data_received(self, data: str):
        self._append_log(data)

    @Slot(str)
    def on_login_required(self, message: str):
        self._append_log(message)

        if "Device not logged in" in message:
            self.login_required.emit()
    
    @Slot(str)
    def on_platform_detected(self, platform_name: str):
        if self._platform_name != platform_name:
            self._platform_name = platform_name

            if self.platform_name == "Unknown":
                self._platform_detected = False
                self.platform_name_changed.emit()
                return
            else:
                self._platform_detected = True
                self.platform_name_changed.emit()

            # Lazy load services
            from core.services.system_info_service import SystemInfoService
            from core.services.diagnostic_service import DiagnosticService
            from core.services.battery_monitor_service import BatteryMonitorService
            from core.services.network_service import NetworkService
            from core.services.stress_test_service import StressTestService
            from core.workers.led_worker import LedWorker
            from core.workers.backlight_worker import BacklightWorker

            # Initialize system info service with the detected platform name
            self._system_info_service = SystemInfoService(device_model=self._model, platform_name=self._platform_name)
            self._system_info_service.info_updated.connect(self.on_info_updated)
            self.system_info_keys_changed.emit()
            
            # Refresh HW config list for the new platform
            self.refresh_hw_config_list()
            
            # Initialize Diagnostic Service
            self._diagnostic_service = DiagnosticService(self._model, self._platform_name)
            self._diagnostic_service.diagnostic_finished.connect(self.on_diagnostic_finished)
            self._diagnostic_service.diagnostic_start.connect(self.on_diagnostic_start)
            self._diagnostic_service.all_diagnostics_finished.connect(self.on_all_diagnostics_finished)
            self._diagnostic_service.manual_check_requested.connect(self.on_manual_check_requested)

            # Initialize Battery Monitor Service
            self._battery_monitor_service = BatteryMonitorService(self._model, self._platform_name)
            self._battery_monitor_service.battery_data_updated.connect(self.on_battery_data_updated)
            
            # Initialize LED Worker
            self._led_worker = LedWorker(self._model, self._platform_name)
            self._led_worker.led_status_updated.connect(self.led_status_updated)

            # Initialize Backlight Worker
            self._backlight_worker = BacklightWorker(self._model, self._platform_name)
            self._backlight_worker.backlight_updated.connect(self.backlight_updated)
            
            # Initialize WiFi Service
            self._network_service = NetworkService(self._model)
            self._network_service.scan_finished.connect(self.wifi_scan_finished)
            self._network_service.connection_result.connect(self.wifi_connection_result)
            self._network_service.status_updated.connect(self.wifi_status_updated)
            self._network_service.network_status_updated.connect(self.on_network_status_updated)

            # Initialize Stress Test Service
            self._stress_test_service = StressTestService(self._model, self._platform_name)
            self._stress_test_service.status_updated.connect(self.on_stress_test_status_updated)

        
        if self.platform_name == "Athena":
            self.toggle_production_tool_service("stop")
        if self.platform_name == "Odin":
            self.toggle_USBC_dmesg_disable()
            self.toggle_USB_port_power_enable()
            self.toggle_cursor_blink_disable()
    
    @Slot(bool, str)
    def on_info_updated(self, key: str, result: str):
        self._system_info[key] = result
        self.system_info_changed.emit(key, result)

    @Slot(str, bool, str)
    def on_diagnostic_finished(self, key: str, success: bool, message: str):
        self.diagnostic_result.emit(key, success, message)

    @Slot(str)
    def on_diagnostic_start(self, key: str):
        self.diagnostic_start.emit(key)

    @Slot(str, str)
    def on_manual_check_requested(self, key: str, message: str):
        self.manual_check_requested.emit(key, message)

    @Slot()
    def on_all_diagnostics_finished(self):
        self._append_log("All diagnostics completed.")
        self.all_diagnostics_completed.emit()

    @Slot(dict)
    def on_battery_data_updated(self, data: dict):
        self.battery_data_updated.emit(data)

    @Slot(dict)
    def on_network_status_updated(self, status: dict):
        self.network_status_updated.emit(status)

    # --- Stress Test Slots ---
    
    @Slot(int, int)
    def start_stress_test(self, cpu_loading: int, mem_loading: int):
        """Starts the stress test."""
        if self._stress_test_service:
            self._stress_test_service.start_stress_test(cpu_loading, mem_loading)
            self._append_log(f"Started stress test: CPU={cpu_loading}%, Mem={mem_loading}MB")

    @Slot()
    def stop_stress_test(self):
        """Stops the stress test."""
        if self._stress_test_service:
            self._stress_test_service.stop_stress_test()
            self._append_log("Stopped stress test.")

    @Slot(result=float)
    def get_free_memory_mb(self) -> float:
        """Returns the free memory in MB."""
        if self._stress_test_service:
            return self._stress_test_service.get_free_memory_mb()
        return 0.0

    @Slot(dict)
    def on_stress_test_status_updated(self, status: dict):
        self.stress_test_status_updated.emit(status)

    def _append_log(self, message: str):
        """Appends a message to the log and emits change signal."""
        if not self._battery_monitor_is_running:
            self.log_appended.emit(message)
