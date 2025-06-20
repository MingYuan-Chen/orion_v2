from PySide6.QtCore import QObject, Signal, Slot, QTimer
from typing import Dict, List, Optional, Any
import time
from core.models.device_manager_model import DeviceManagerModel
from core.workers.serial_device_worker import SerialDeviceWorker
from core.services.smart_connection_monitor import SmartConnectionMonitor
from util.logger import logger


class DeviceManagerViewModel(QObject):
    """
    Device Manager View Model
    
    Manage device connection, disconnection and command sending operations.
    Provide signals to notify the UI layer of operation results.
    """
    # Connection/disconnection signals
    connection_result = Signal(str, bool, str)  # device_id, success, message
    disconnection_result = Signal(str, bool, str)  # device_id, success, message
    device_list_changed = Signal(list)  # devices_list
    
    # Command execution signals
    command_result = Signal(str, str, str)  # device_id, command, response
    
    # Service initialization signals
    services_initialization_completed = Signal(str)  # platform_name
    platform_detection_failed = Signal(str, str)  # device_id, port
    
    # Connection monitoring signals
    device_ready_for_commands = Signal(str)  # device_id - device is ready for commands
    device_connection_lost = Signal(str, str)  # device_id, reason - device connection lost
    
    def __init__(self, device_manager: DeviceManagerModel = None, platform_name: str = "hydra_fhd", parent_widget=None):
        super().__init__()
        # Initialize device manager
        self.device_manager = device_manager or DeviceManagerModel()
        self.connected_devices = {}  # device_id: device_info
        self.platform_name = platform_name
        self.parent_widget = parent_widget  # Store parent widget for message boxes
        
        # Initialize platform detection status
        self.platform_detection_status = {}
        
        # Add PIC command retry configuration
        self.pic_command_retry_config = {
            'max_retries': 5,  # Maximum retry attempts
            'retry_delay': 1.0  # Delay between retries in seconds
        }
        
        # Create device worker thread
        self._serial_worker = SerialDeviceWorker(self.device_manager)
        
        # Connection signals
        self._serial_worker.connection_result.connect(self._on_connection_completed)
        self._serial_worker.disconnection_result.connect(self._on_disconnection_completed)
        self._serial_worker.command_result.connect(self._on_command_completed)
        
        # Initialize services as None - will be created after device connection
        self.system_info_service = None
        self.hardware_test_manager = None
        
        # Initialize smart connection monitor (delayed initialization to avoid circular dependencies)
        self.smart_monitor = None
        
        logger.info(f"DeviceManagerViewModel initialized with default platform: {platform_name}")
        
    def _initialize_services(self, platform_name: str = None):
        """Initialize services with the specified or default platform name
        
        Args:
            platform_name: Platform name to use for service initialization
        """
        if platform_name:
            self.platform_name = platform_name
            
        logger.info(f"Initializing services with platform: {self.platform_name}")
        
        try:
            # Initialize SystemInfoService with platform name
            from core.services.system_info import SystemInfoService
            self.system_info_service = SystemInfoService(self._serial_worker, platform_name=self.platform_name)
            
            # Initialize HardwareTestManagerService
            from core.services.hardware_test_manager import HardwareTestManagerService
            self.hardware_test_manager = HardwareTestManagerService(self._serial_worker, platform_name=self.platform_name)
            
            # Initialize smart connection monitor
            self.smart_monitor = SmartConnectionMonitor(self._serial_worker)
            self.smart_monitor.device_ready.connect(self.device_ready_for_commands.emit)
            self.smart_monitor.device_not_ready.connect(self.device_connection_lost.emit)
            
            logger.info(f"Services initialized successfully with platform: {self.platform_name}")
            logger.info("Smart connection monitor initialized")
            
            # Emit signal to notify UI that services are ready
            self.services_initialization_completed.emit(self.platform_name)
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
        
    def cleanup(self):
        """Release resources and clean up"""
        # Prevent duplicate cleanup
        if hasattr(self, '_is_cleaning_up') and self._is_cleaning_up:
            logger.warning("DeviceManagerViewModel is already in the cleanup process, avoid duplicate cleanup")
            return
            
        # Security check: If the C++ object has been deleted, skip cleanup
        try:
            # Try a simple operation to check if the object is valid
            self.blockSignals(True)
        except RuntimeError as e:
            if "C++ object" in str(e) and "deleted" in str(e):
                logger.warning("DeviceManagerViewModel C++ object has been deleted, skip cleanup")
                return
            # If it's another RuntimeError, continue trying to clean up
        except Exception as e:
            logger.warning(f"Error checking object validity: {e}")
        
        # Set cleanup flag
        self._is_cleaning_up = True
        
        logger.info("DeviceManagerViewModel starts cleaning up resources")
        
        try:
            # 1. Ensure any active timers are stopped
            if hasattr(self, '_refresh_timer') and self._refresh_timer and self._refresh_timer.isActive():
                self._refresh_timer.stop()
                logger.debug("Stopped device refresh timer")
            
            # 2. Disconnect all signal connections - Disconnect signals before disconnecting devices to avoid triggering callbacks
            try:
                # First block sending new signals
                self.blockSignals(True)
                
                # Then disconnect signals from worker
                if hasattr(self, '_serial_worker') and self._serial_worker:
                    try:
                        # Check if signals have receivers
                        try:
                            self._serial_worker.connection_result.disconnect(self._on_connection_completed)
                        except Exception:
                            pass
                            
                        try:
                            self._serial_worker.disconnection_result.disconnect(self._on_disconnection_completed)
                        except Exception:
                            pass
                            
                        try:
                            self._serial_worker.command_result.disconnect(self._on_command_completed)
                        except Exception:
                            pass
                            
                        logger.debug("Worker signal connections disconnected")
                    except Exception as e:
                        logger.warning(f"Error disconnecting worker signals: {e}")
            except Exception as e:
                logger.warning(f"Error disconnecting signal connections: {e}")
            
            # 3. Disconnect all connected devices - Since signals have been disconnected, this will not trigger callbacks
            if hasattr(self, 'device_manager') and self.device_manager:
                try:
                    # Directly use the disconnect_all method of device_manager, not through this class
                    logger.info("Disconnect all devices directly")
                    self.device_manager.disconnect_all()
                except Exception as e:
                    logger.error(f"Error disconnecting all devices: {e}")
            
            # 4. Stop and release worker thread
            if hasattr(self, '_serial_worker') and self._serial_worker:
                try:
                    logger.info("Stopping and releasing worker thread")
                    # Ensure the thread object exists and is accessible
                    if hasattr(self._serial_worker, 'thread') and self._serial_worker.thread:
                        # Check if the thread is still running
                        if self._serial_worker.thread.isRunning():
                            # Try to exit the worker thread normally
                            self._serial_worker.thread.requestInterruption()
                            if not self._serial_worker.thread.wait(1000):
                                logger.warning("Worker thread unresponsive, force termination")
                                self._serial_worker.thread.terminate()
                                self._serial_worker.thread.wait(1000)  # Give the thread more time to terminate
                            logger.debug("Device worker thread stopped")
                        
                    # Call the cleanup method of serial_worker (if it exists)
                    if hasattr(self._serial_worker, 'cleanup'):
                        try:
                            self._serial_worker.cleanup()
                        except Exception as e:
                            logger.warning(f"Error calling serial_worker.cleanup(): {e}")
                        
                    # Clear the reference and notify Python to reclaim memory
                    worker_ref = self._serial_worker
                    self._serial_worker = None
                    del worker_ref
                    
                except Exception as e:
                    logger.error(f"Error stopping worker thread: {e}")
            
            # 5. Release device manager model
            if hasattr(self, 'device_manager') and self.device_manager:
                try:
                    logger.info("Cleaning up device manager model")
                    device_manager_ref = self.device_manager
                    self.device_manager = None
                    del device_manager_ref
                    logger.debug("Device manager model cleaned up")
                except Exception as e:
                    logger.error(f"Error cleaning up device manager model: {e}")
            
            # 6. Clean up services
            try:
                if hasattr(self, 'system_info_service') and self.system_info_service:
                    # Clear service reference
                    self.system_info_service = None
                    logger.debug("System info service cleaned up")
                
                if hasattr(self, 'hardware_test_manager') and self.hardware_test_manager:
                    # Clear service reference
                    self.hardware_test_manager = None
                    logger.debug("Hardware test manager cleaned up")
                    
                if hasattr(self, 'smart_monitor') and self.smart_monitor:
                    # Stop all monitoring activities
                    for device_id in list(self.smart_monitor.monitoring_devices.keys()):
                        self.smart_monitor.stop_monitoring(device_id)
                    # Clear service reference
                    self.smart_monitor = None
                    logger.debug("Smart connection monitor cleaned up")
                    
            except Exception as e:
                logger.error(f"Error cleaning up services: {e}")
            
            # 7. Clear all device-related collections
            if hasattr(self, 'connected_devices'):
                self.connected_devices.clear()
            
            # 8. Clear platform detection status
            if hasattr(self, 'platform_detection_status'):
                self.platform_detection_status.clear()
            
        except Exception as e:
            logger.error(f"Error cleaning up DeviceManagerViewModel resources: {e}")
        finally:
            # Regardless of success or failure, reset the cleanup flag and record completion
            self._is_cleaning_up = False
            logger.info("DeviceManagerViewModel resources cleaned up")
        
    def __del__(self):
        """Ensure resources are released"""
        try:
            # Check if the object is still valid
            if hasattr(self, 'blockSignals'):
                try:
                    # Try a simple operation to test object validity
                    self.blockSignals(True)
                    # If the object is valid and not in the cleanup process, call cleanup
                    if not hasattr(self, '_is_cleaning_up') or not self._is_cleaning_up:
                        logger.debug("DeviceManagerViewModel destructor calling cleanup")
                        self.cleanup()
                except Exception:
                    # Object is invalid, ignore cleanup
                    pass
        except Exception:
            # Avoid throwing exceptions in the destructor
            pass
        
    @Slot(str, bool, str)
    def _on_connection_completed(self, device_id: str, success: bool, message: str):
        """Handle connection operation completion"""
        if success:
            # Parse device ID information to create device info object
            parts = device_id.split('_')
            device_type = parts[0] if len(parts) > 0 else "serial"
            address = parts[1] if len(parts) > 1 else device_id
            
            # Create device info
            device_info = {
                'id': device_id,
                'name': f"{device_type.capitalize()} Device ({address})",
                'type': device_type.capitalize(),
                'address': address,
                'status': 'Connected',
                'details': {}  # Specific details can be added according to device type in other places
            }
            
            # Store device info
            self.connected_devices[device_id] = device_info

            # Initialize platform detection status for this device
            self.platform_detection_status[device_id] = {
                'command_results': {},
                'completed_commands': set(),
                'detected_platform': None,
                'panel_id_response': '',  # Store panel_id response for panel_id=01 cases
                'status': 'checking_connection',  # 'checking_connection' -> 'detecting_platform' -> 'completed'
                'pic_retry_count': 0  # Track PIC command retry attempts
            }

            # First, send the root command to check if device is responsive
            logger.info(f"Checking device responsiveness for {device_id}")
            self._serial_worker.send_command(device_id, "root", 10)
            
            # Note: Services will be initialized in _on_command_completed when all platform detection responses are received
                
            # Emit signal
            self.connection_result.emit(device_id, success, message)
            self.device_list_changed.emit(list(self.connected_devices.values()))
        else:
            # Connection failed - also emit signal to notify UI
            logger.error(f"Device connection failed: {device_id} - {message}")
            self.connection_result.emit(device_id, success, message)
        
    @Slot(str, bool, str)
    def _on_disconnection_completed(self, device_id: str, success: bool, message: str):
        """Handle disconnection operation completion"""
        if success and device_id in self.connected_devices:
            del self.connected_devices[device_id]
            
        # Clean up platform detection status for this device if it exists
        if device_id in self.platform_detection_status:
            del self.platform_detection_status[device_id]
            logger.debug(f"Cleared platform detection status for device {device_id}")
        
        # Check if all devices are now disconnected
        if not self.connected_devices:
            logger.info("All devices disconnected, resetting services to allow re-initialization")
            # Reset services to None so they can be re-initialized on next connection
            self.system_info_service = None
            self.hardware_test_manager = None
            logger.debug("Services reset to None - ready for re-initialization")
            
        # Emit signal
        self.disconnection_result.emit(device_id, success, message)
        self.device_list_changed.emit(list(self.connected_devices.values()))
        
    @Slot(str, str, str)
    def _on_command_completed(self, device_id: str, command: str, response: str):
        """Handle command execution completion"""
        
        # Check if this device is in platform detection process
        if device_id in self.platform_detection_status:
            status = self.platform_detection_status[device_id]['status']
            response_lower = response.strip().lower()
            
            # Handle root command (connection check)
            if command == "root" and status == 'checking_connection':
                if "error: no response received from device" in response_lower:
                    logger.warning(f"Device {device_id} is not responsive, indicating unsupported device")
                    
                    # Get device port information
                    device_port = self.connected_devices.get(device_id, {}).get('port', 'Unknown')
                    
                    # Emit platform detection failed signal immediately
                    self.platform_detection_failed.emit(device_id, device_port)
                    
                    # Clean up detection status for this device
                    del self.platform_detection_status[device_id]
                    
                    # Always emit the command result signal for other components
                    self.command_result.emit(device_id, command, response)
                    return
                else:
                    # Device is responsive, proceed to platform detection
                    logger.info(f"Device {device_id} is responsive, starting platform detection")
                    self.platform_detection_status[device_id]['status'] = 'detecting_platform'
                    
                    # Now send platform detection commands
                    logger.info(f"Sending platform detection commands to device {device_id}")
                    self._serial_worker.send_command(device_id, "cat /proc/panel_id", 10)
                    self._serial_worker.send_command(device_id, "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2", 10)
                    
                    # Always emit the command result signal for other components
                    self.command_result.emit(device_id, command, response)
                    return
        
        # Check if this is one of the platform detection commands
        detected_platform = None
        is_platform_detection_command = False
        
        # Only process platform detection commands if we're in the detecting_platform status
        if device_id in self.platform_detection_status and self.platform_detection_status[device_id]['status'] == 'detecting_platform':
            if command == "cat /proc/panel_id":
                logger.info(f"Received platform detection response from {device_id}: {response}")
                detected_platform = self._detect_platform_from_panel_id(response)
                if detected_platform:
                    logger.info(f"Detected platform from panel_id for device {device_id}: {detected_platform}")
                else:
                    # Check if this is panel_id = 01 (needs PIC version check)
                    panel_id = response.strip().lower()
                    if "01" in panel_id:
                        logger.info(f"panel_id = 01 detected for device {device_id}, waiting for PIC version to determine argo vs hydra_fhd")
                        # Store panel_id response for later use
                        self.platform_detection_status[device_id]['panel_id_response'] = response
                    else:
                        logger.warning(f"Unable to detect platform from panel_id for device {device_id}: {response}")
                is_platform_detection_command = True
            
            elif command == "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2":
                logger.info(f"Received PIC version response from {device_id}: {response}")
                
                # Validate PIC response format
                if not self._is_valid_pic_response(response):
                    logger.warning(f"Invalid PIC version response format from {device_id}: '{response}'")
                    # Retry the PIC command
                    self._retry_pic_command(device_id)
                    # Don't process this as a completed command yet
                    self.command_result.emit(device_id, command, response)
                    return
                
                # Valid PIC response received
                pic_version = self._get_pic_version_from_response(response)
                logger.info(f"Valid PIC version received from {device_id}: {pic_version}")
                
                # Check if we have panel_id = 01 that needs PIC version check
                panel_id_response = self.platform_detection_status[device_id].get('panel_id_response', '')
                if "01" in panel_id_response.strip().lower():
                    detected_platform = self._detect_platform_from_panel_id_01(panel_id_response, response)
                    logger.info(f"Detected platform from panel_id=01 + PIC version for device {device_id}: {detected_platform}")
                else:
                    # Legacy logic for direct PIC version detection (if panel_id was not 01)
                    if '0x72' in response:
                        detected_platform = "argo"
                        logger.info(f"Detected platform from PIC version for device {device_id}: {detected_platform}")
                
                is_platform_detection_command = True
        
        # Handle platform detection command completion
        if is_platform_detection_command and device_id in self.platform_detection_status:
            # Store command result
            self.platform_detection_status[device_id]['command_results'][command] = response
            self.platform_detection_status[device_id]['completed_commands'].add(command)
            
            # Update detected platform if we found one
            if detected_platform:
                self.platform_detection_status[device_id]['detected_platform'] = detected_platform
            
            # Check if all platform detection commands are completed
            expected_commands = {
                "cat /proc/panel_id",
                "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2"
            }
            completed_commands = self.platform_detection_status[device_id]['completed_commands']
            
            if expected_commands.issubset(completed_commands):
                logger.info(f"All platform detection commands completed for device {device_id}")
                
                # Get the final detected platform
                final_platform = self.platform_detection_status[device_id]['detected_platform']
                
                # Special handling for panel_id = 01 cases
                panel_id_response = self.platform_detection_status[device_id].get('panel_id_response', '')
                if "01" in panel_id_response.strip().lower() and not final_platform:
                    # For panel_id = 01, we need both commands to complete and final platform to be determined
                    pic_version_response = self.platform_detection_status[device_id]['command_results'].get(
                        "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2", 
                        ""
                    )
                    if pic_version_response:
                        final_platform = self._detect_platform_from_panel_id_01(panel_id_response, pic_version_response)
                        self.platform_detection_status[device_id]['detected_platform'] = final_platform
                        logger.info(f"Final platform determination for panel_id=01 device {device_id}: {final_platform}")
                
                # Use the new completion method
                self._complete_platform_detection(device_id)
        
        # Always emit the command result signal for other components
        self.command_result.emit(device_id, command, response)
    
    def _detect_platform_from_panel_id(self, panel_id_response: str) -> Optional[str]:
        """Detect platform name based on panel_id response
        
        Args:
            panel_id_response: Response from 'cat /proc/panel_id' command
            
        Returns:
            Optional[str]: Detected platform name, or None if detection failed or needs PIC version check
        """
        # Remove whitespace and convert to lowercase for comparison
        response = panel_id_response.strip().lower()
        
        logger.debug(f"Analyzing panel_id response: '{response}'")
        
        # Check if this is an error response
        if "error" in response or "no response" in response or response == "":
            logger.warning(f"Invalid panel_id response: '{panel_id_response}', platform detection failed")
            return None
        
        # Platform detection logic based on panel_id
        if "01" in response:
            # panel_id = 01 needs PIC version check to distinguish between argo and hydra_fhd
            logger.debug("panel_id = 01 detected, need PIC version check to distinguish argo vs hydra_fhd")
            return None  # Return None to indicate need for PIC version check
        elif "00" in response:
            return "hydra"
        elif "10" in response:
            return "gemini_fhd"
        elif "11" in response:
            return "gemini"
        else:
            # Unknown but valid response - log for debugging
            logger.warning(f"Unknown panel_id response: '{panel_id_response}', platform detection failed")
            return None
    
    def _detect_platform_from_panel_id_01(self, panel_id_response: str, pic_version_response: str) -> Optional[str]:
        """Detect platform when panel_id = 01 using PIC version
        
        Args:
            panel_id_response: Response from 'cat /proc/panel_id' command
            pic_version_response: Response from PIC version command
            
        Returns:
            Optional[str]: Detected platform name (argo or hydra_fhd), or None if detection failed
        """
        logger.debug(f"Analyzing panel_id=01 with PIC version: '{pic_version_response}'")
        
        # Check if PIC version response is valid
        pic_response_lower = pic_version_response.strip().lower()
        if "error" in pic_response_lower or "no response" in pic_response_lower:
            logger.warning(f"Invalid PIC version response for panel_id=01: '{pic_version_response}', defaulting to hydra_fhd")
            return "hydra_fhd"
        
        # Check for argo signature (0x72 in PIC version)
        if '0x72' in pic_version_response:
            logger.info(f"Detected argo platform: panel_id=01 + PIC version contains 0x72")
            return "argo"
        else:
            logger.info(f"Detected hydra_fhd platform: panel_id=01 + PIC version does not contain 0x72")
            return "hydra_fhd"
    
    def _is_valid_pic_response(self, response: str) -> bool:
        """Validate if PIC version response is in expected format
        
        Args:
            response: Raw response from PIC version command
            
        Returns:
            bool: True if response matches expected format, False otherwise
        """
        # Remove whitespace and normalize response
        clean_response = response.strip()
        
        # Check for error responses
        response_lower = clean_response.lower()
        if "error" in response_lower or "no response" in response_lower or not clean_response:
            return False
        
        # Expected valid PIC version patterns:
        # v100: 0x02 0x00 0x64
        # v110: 0x02 0x00 0x6d  
        # v114: 0x02 0x00 0x72
        valid_patterns = [
            '0x00 0x64',  # v100
            '0x00 0x6e',  # v110
            '0x00 0x72'   # v114
        ]
        
        # Check if response contains any valid pattern
        for pattern in valid_patterns:
            if pattern in clean_response:
                logger.debug(f"Valid PIC response pattern found: {pattern}")
                return True
        
        logger.debug(f"Invalid PIC response format: '{clean_response}'")
        return False
    
    def _get_pic_version_from_response(self, response: str) -> Optional[str]:
        """Extract PIC version string from response
        
        Args:
            response: Raw response from PIC version command
            
        Returns:
            Optional[str]: Version string (v100, v110, v114) or None if not found
        """
        clean_response = response.strip()
        
        if '0x00 0x64' in clean_response:
            return 'v100'
        elif '0x00 0x6d' in clean_response:
            return 'v110'
        elif '0x00 0x72' in clean_response:
            return 'v114'
        else:
            return None
    
    def _retry_pic_command(self, device_id: str):
        """Retry PIC version command for platform detection with delay
        
        Args:
            device_id: Device ID to retry command for
        """
        if device_id not in self.platform_detection_status:
            logger.error(f"Cannot retry PIC command: device {device_id} not in platform detection status")
            return
        
        # Get current retry count
        retry_count = self.platform_detection_status[device_id].get('pic_retry_count', 0)
        max_retries = self.pic_command_retry_config['max_retries']
        
        if retry_count >= max_retries:
            logger.error(f"PIC command retry limit reached for device {device_id} ({retry_count}/{max_retries})")
            # Use default platform detection logic
            panel_id_response = self.platform_detection_status[device_id].get('panel_id_response', '')
            if "01" in panel_id_response.strip().lower():
                # Default to hydra_fhd for panel_id = 01 when PIC command fails
                logger.warning(f"Defaulting to hydra_fhd for device {device_id} due to PIC command failure")
                self.platform_detection_status[device_id]['detected_platform'] = 'hydra_fhd'
                self._complete_platform_detection(device_id)
            return
        
        # Increment retry count
        self.platform_detection_status[device_id]['pic_retry_count'] = retry_count + 1
        
        logger.info(f"Retrying PIC command for device {device_id} (attempt {retry_count + 1}/{max_retries}) in {self.pic_command_retry_config['retry_delay']} seconds")
        
        # Use QTimer to delay the retry
        retry_timer = QTimer()
        retry_timer.timeout.connect(lambda: self._execute_pic_retry(device_id, retry_timer))
        retry_timer.setSingleShot(True)
        retry_timer.start(int(self.pic_command_retry_config['retry_delay'] * 1000))  # Convert to milliseconds
    
    def _execute_pic_retry(self, device_id: str, timer: QTimer):
        """Execute the actual PIC command retry
        
        Args:
            device_id: Device ID to retry command for
            timer: Timer object to clean up
        """
        # Clean up timer
        timer.deleteLater()
        
        # Check if device is still in detection status
        if device_id not in self.platform_detection_status:
            logger.warning(f"Device {device_id} no longer in platform detection status, skipping retry")
            return
        
        logger.info(f"Executing PIC command retry for device {device_id}")
        
        # Send PIC command again
        pic_command = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2"
        self._serial_worker.send_command(device_id, pic_command, 10)
    
    def _complete_platform_detection(self, device_id: str):
        """Complete platform detection process for a device
        
        Args:
            device_id: Device ID to complete detection for
        """
        if device_id not in self.platform_detection_status:
            return
        
        final_platform = self.platform_detection_status[device_id].get('detected_platform')
        
        if not final_platform:
            logger.warning(f"No platform detected from commands for device {device_id}")
            
            # Get device port information
            device_port = self.connected_devices.get(device_id, {}).get('port', 'Unknown')
            
            # Emit platform detection failed signal
            self.platform_detection_failed.emit(device_id, device_port)
            
            # Clean up detection status for this device
            del self.platform_detection_status[device_id]
            return
        
        logger.info(f"Platform detection completed for device {device_id}: {final_platform}")
        
        # Initialize services if this is the first connected device or if services are not initialized
        if self.system_info_service is None or self.hardware_test_manager is None:
            # Update platform name and initialize services
            self.platform_name = final_platform
            self._initialize_services()
            logger.info(f"Services initialized with detected platform: {final_platform}")
        else:
            logger.debug(f"Services already initialized, skipping for device {device_id}")
        
        # Clean up detection status for this device
        del self.platform_detection_status[device_id]
    
    def connect_serial_device(self, device_id: str, port: str, baudrate: int = 115200, timeout: int = 3):
        """Connect serial device"""
        logger.info(f"Request to connect device {device_id} to port {port}")
        
        if device_id in self.connected_devices:
            self.connection_result.emit(device_id, False, f"Device {device_id} is already connected")
            return
        
        # Use worker thread to connect device
        self._serial_worker.connect_device(device_id, port, baudrate, timeout)
        
    def disconnect_device(self, device_id: str):
        """Disconnect device"""
        logger.info(f"Request to disconnect device {device_id}")
        
        if device_id not in self.connected_devices:
            self.disconnection_result.emit(device_id, False, f"Device {device_id} is not connected")
            return
            
        # Use worker thread to disconnect device
        self._serial_worker.disconnect_device(device_id)
        
    def send_command(self, device_id: str, command: str, timeout: int = 5):
        """Send command to device"""
        logger.info(f"Request to send command to device {device_id}: {command}")
        
        if device_id not in self.connected_devices:
            self.command_result.emit(device_id, command, f"Error: Device {device_id} is not connected")
            return
            
        # Use worker thread to send command
        self._serial_worker.send_command(device_id, command, timeout)
        
    def get_connected_devices(self) -> List[Dict[str, Any]]:
        """Get list of connected devices"""
        return list(self.connected_devices.values())
        
    def disconnect_all_devices(self):
        """Disconnect all devices"""
        logger.info("Request to disconnect all devices")
        
        for device_id in list(self.connected_devices.keys()):
            self.disconnect_device(device_id)

    def update_device_info(self, device_id: str, details: Dict[str, Any]):
        """Update device details
        
        Args:
            device_id: device ID
            details: details dictionary
        """
        if device_id in self.connected_devices:
            # Update details
            self.connected_devices[device_id]['details'].update(details)
            # Notify device list has changed
            self.device_list_changed.emit(list(self.connected_devices.values()))

    def set_platform(self, platform_name: str):
        """
        Set the platform name and update dependent services
        
        Args:
            platform_name: Platform name to use
        """
        logger.info(f"Changing platform to: {platform_name}")
        self.platform_name = platform_name
        
        # Update platform for services if they are already initialized
        if hasattr(self, 'system_info_service') and self.system_info_service:
            self.system_info_service.set_platform(platform_name)
            logger.debug("Updated system_info_service platform")
        
        if hasattr(self, 'hardware_test_manager') and self.hardware_test_manager:
            # Check if hardware_test_manager has set_platform method
            if hasattr(self.hardware_test_manager, 'set_platform'):
                self.hardware_test_manager.set_platform(platform_name)
                logger.debug("Updated hardware_test_manager platform")
        
        # Note: If services are not yet initialized, they will use the updated 
        # platform_name when _initialize_services() is called

    def are_services_initialized(self) -> bool:
        """Check if all required services are initialized
        
        Returns:
            bool: True if all services are initialized, False otherwise
        """
        return (self.system_info_service is not None and 
                self.hardware_test_manager is not None and
                self.smart_monitor is not None)
    
    def get_services_status(self) -> dict:
        """Get detailed status of service initialization
        
        Returns:
            dict: Status information about services
        """
        return {
            'system_info_service': self.system_info_service is not None,
            'hardware_test_manager': self.hardware_test_manager is not None,
            'smart_monitor': self.smart_monitor is not None,
            'all_initialized': self.are_services_initialized(),
            'platform_name': self.platform_name
        }
        
    # Connection monitoring methods
    def start_device_monitoring(self, device_id: str, check_interval: int = 10000):
        """Start smart monitoring for device connection status, especially for system restart detection
        
        Args:
            device_id: device ID
            check_interval: check interval (milliseconds), default 10 seconds to avoid frequent interference
        """
        if self.smart_monitor:
            self.smart_monitor.start_monitoring(device_id, check_interval)
            logger.info(f"Started smart monitoring for device {device_id} with {check_interval}ms interval")
        else:
            logger.warning("Smart monitor not initialized, cannot start monitoring")
            
    def stop_device_monitoring(self, device_id: str):
        """Stop monitoring device connection status"""
        if self.smart_monitor:
            self.smart_monitor.stop_monitoring(device_id)
            logger.info(f"Stopped smart monitoring for device {device_id}")
        else:
            logger.warning("Smart monitor not initialized, cannot stop monitoring")
            
    def set_device_busy(self, device_id: str, is_busy: bool):
        """Set device busy status
        When the device is executing tests or other important operations, pause monitoring
        
        Args:
            device_id: device ID
            is_busy: True=device busy, pause monitoring; False=device free, can monitor
        """
        if self.smart_monitor:
            self.smart_monitor.set_device_busy(device_id, is_busy)
            state = "busy" if is_busy else "free"
            logger.debug(f"Device {device_id} marked as {state}")
        else:
            logger.warning("Smart monitor not initialized, cannot set device busy state")
            
    def check_device_ready_immediately(self, device_id: str):
        """Immediately check if the device is ready to receive commands (trigger a single monitoring check)"""
        if self.smart_monitor and device_id not in self.smart_monitor.get_busy_devices():
            current_config = self.smart_monitor.monitoring_devices.get(device_id)
            if current_config:
                current_config['last_check_time'] = 0  # reset check time
                self.smart_monitor._check_single_device(device_id)
                logger.info(f"Triggered immediate health check for device {device_id}")
        else:
            logger.warning(f"Cannot perform immediate check for device {device_id} (monitor not ready or device busy)")
            
    def is_device_ready_for_commands(self, device_id: str) -> bool:
        """Check if the device is ready to receive commands"""
        if self.smart_monitor:
            return self.smart_monitor.is_device_ready(device_id)
        return False
        
    def get_device_connection_status(self, device_id: str) -> Dict:
        """Get device connection status detailed information"""
        if self.smart_monitor:
            return self.smart_monitor.get_device_status(device_id)
        return {'monitored': False, 'error': 'Smart monitor not initialized'}
