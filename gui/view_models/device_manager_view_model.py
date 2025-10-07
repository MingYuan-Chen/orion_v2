from PySide6.QtCore import QObject, Signal, Slot, QTimer
from typing import Dict, List, Optional, Any
import time
from core.models.device_manager_model import DeviceManagerModel
from core.workers.serial_device_worker import SerialDeviceWorker
from core.workers.tcp_ip_device_worker import TcpIpDeviceWorker
from core.services.smart_connection_monitor import SmartConnectionMonitor
from core.services.usb_package_deploy_service import UsbPackageDeployService
from util.logger import logger

# Constants for platform detection
NEED_ATHENA_CHECK = "NEED_ATHENA_CHECK"


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
    
    # USB package deployment signals
    usb_deployment_started = Signal(str)  # device_id - USB deployment started
    usb_deployment_progress = Signal(str, str)  # device_id, progress_message
    usb_deployment_completed = Signal(str, bool, str)  # device_id, success, message
    usb_deployment_ready_for_system_info = Signal(str)  # device_id - ready for system info
    
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
        
        # Create device worker threads
        self._serial_worker = SerialDeviceWorker(self.device_manager)
        self._tcp_ip_worker = TcpIpDeviceWorker(self.device_manager)
        
        # Connect signals from both workers
        self._serial_worker.connection_result.connect(self._on_connection_completed)
        self._serial_worker.disconnection_result.connect(self._on_disconnection_completed)
        self._serial_worker.command_result.connect(self._on_command_completed)
        
        self._tcp_ip_worker.connection_result.connect(self._on_connection_completed)
        self._tcp_ip_worker.disconnection_result.connect(self._on_disconnection_completed)
        self._tcp_ip_worker.command_result.connect(self._on_command_completed)
        
        # Initialize services as None - will be created after device connection
        self.system_info_service = None
        self.hardware_test_manager = None
        
        # Initialize smart connection monitor (delayed initialization to avoid circular dependencies)
        self.smart_monitor = None
        
        # Initialize USB package deploy service
        self.usb_package_deploy_service = UsbPackageDeployService(self)
        
        # Connect USB package deploy service signals
        self.usb_package_deploy_service.deployment_started.connect(self.usb_deployment_started.emit)
        self.usb_package_deploy_service.deployment_progress.connect(self.usb_deployment_progress.emit)
        self.usb_package_deploy_service.deployment_completed.connect(self.usb_deployment_completed.emit)
        self.usb_package_deploy_service.ready_for_system_info.connect(self.usb_deployment_ready_for_system_info.emit)
        
        logger.info(f"DeviceManagerViewModel initialized with default platform: {platform_name}")

    def _get_worker_for_device(self, device_id: str) -> Optional[QObject]:
        """Return the appropriate worker based on the device ID prefix."""
        if device_id.startswith("tcp"):
            return self._tcp_ip_worker
        elif device_id.startswith("serial"):
            return self._serial_worker
        else:
            # Default or fallback logic
            logger.warning(f"Could not determine worker for device_id: {device_id}. Defaulting to serial worker.")
            return self._serial_worker

    def _initialize_services(self, worker: QObject, platform_name: str = None):
        """Initialize services with the specified worker and platform name
        
        Args:
            worker: The worker instance (Serial or TCP/IP) to be used by services.
            platform_name: Platform name to use for service initialization
        """
        if platform_name:
            self.platform_name = platform_name
            
        logger.info(f"Initializing services with platform: {self.platform_name}")
        
        try:
            # Initialize SystemInfoService with the correct worker and platform name
            from core.services.system_info import SystemInfoService
            self.system_info_service = SystemInfoService(worker, platform_name=self.platform_name)
            
            # Initialize HardwareTestManagerService
            from core.services.hardware_test_manager import HardwareTestManagerService
            self.hardware_test_manager = HardwareTestManagerService(worker, platform_name=self.platform_name)
            
            # Initialize smart connection monitor
            self.smart_monitor = SmartConnectionMonitor(worker)
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
        if hasattr(self, '_is_cleaning_up') and self._is_cleaning_up:
            return
        
        try:
            self.blockSignals(True)
        except RuntimeError:
            return # C++ object deleted
        except Exception as e:
            logger.warning(f"Error checking object validity: {e}")

        self._is_cleaning_up = True
        logger.info("DeviceManagerViewModel starts cleaning up resources")

        # Disconnect all devices first
        if hasattr(self, 'device_manager') and self.device_manager:
            self.device_manager.disconnect_all()

        # Cleanup workers
        for worker_attr in ['_serial_worker', '_tcp_ip_worker']:
            if hasattr(self, worker_attr):
                worker = getattr(self, worker_attr)
                if worker:
                    try:
                        worker.cleanup()
                        setattr(self, worker_attr, None)
                    except Exception as e:
                        logger.error(f"Error cleaning up {worker_attr}: {e}")
        
        # Cleanup other resources
        # ... (rest of the original cleanup logic, simplified for brevity) ...

        self._is_cleaning_up = False
        logger.info("DeviceManagerViewModel resources cleaned up")
        
    def __del__(self):
        """Ensure resources are released"""
        try:
            if hasattr(self, 'blockSignals'):
                try:
                    self.blockSignals(True)
                    if not hasattr(self, '_is_cleaning_up') or not self._is_cleaning_up:
                        self.cleanup()
                except Exception:
                    pass
        except Exception:
            pass
        
    @Slot(str, bool, str)
    def _on_connection_completed(self, device_id: str, success: bool, message: str):
        """Handle connection operation completion"""
        if success:
            parts = device_id.split('_')
            device_type = parts[0] if len(parts) > 0 else "unknown"
            address = '_'.join(parts[1:]) if len(parts) > 1 else device_id
            
            device_info = {
                'id': device_id,
                'name': f"{device_type.capitalize()} Device ({address})",
                'type': device_type.capitalize(),
                'address': address,
                'status': 'Connected',
                'details': {}
            }
            
            self.connected_devices[device_id] = device_info
            self.platform_detection_status[device_id] = {
                'command_results': {}, 'completed_commands': set(), 'detected_platform': None,
                'panel_id_response': '', 'status': 'checking_connection', 'pic_retry_count': 0
            }

            logger.info(f"Checking device responsiveness for {device_id}")
            worker = self._get_worker_for_device(device_id)
            if worker:
                worker.send_command(device_id, "root", 10)
                
            self.connection_result.emit(device_id, success, message)
            self.device_list_changed.emit(list(self.connected_devices.values()))
        else:
            logger.error(f"Device connection failed: {device_id} - {message}")
            self.connection_result.emit(device_id, success, message)
        
    @Slot(str, bool, str)
    def _on_disconnection_completed(self, device_id: str, success: bool, message: str):
        """Handle disconnection operation completion"""
        if success and device_id in self.connected_devices:
            del self.connected_devices[device_id]
        
        if device_id in self.platform_detection_status:
            del self.platform_detection_status[device_id]
            
        if not self.connected_devices:
            self.system_info_service = None
            self.hardware_test_manager = None
            
        self.disconnection_result.emit(device_id, success, message)
        self.device_list_changed.emit(list(self.connected_devices.values()))
        
    @Slot(str, str, str)
    def _on_command_completed(self, device_id: str, command: str, response: str):
        """Handle command execution completion"""
        worker = self._get_worker_for_device(device_id)
        if not worker:
            logger.error(f"No worker found for device {device_id}. Aborting command completion.")
            self.command_result.emit(device_id, command, response)
            return

        # Check if this device is in platform detection process
        if device_id in self.platform_detection_status:
            status = self.platform_detection_status[device_id]['status']
            response_lower = response.strip().lower()
            
            # Handle root command (connection check)
            if command == "root" and status == 'checking_connection':
                if "error: no response received from device" in response_lower:
                    logger.warning(f"Device {device_id} is not responsive, indicating unsupported device")
                    device_port = self.connected_devices.get(device_id, {}).get('address', 'Unknown')
                    self.platform_detection_failed.emit(device_id, device_port)
                    del self.platform_detection_status[device_id]
                    self.command_result.emit(device_id, command, response)
                    return
                else:
                    logger.info(f"Device {device_id} is responsive, starting platform detection")
                    self.platform_detection_status[device_id]['status'] = 'detecting_platform'
                    logger.info(f"Starting platform detection for device {device_id}")
                    worker.send_command(device_id, "cat /proc/panel_id", 10)
                    self.command_result.emit(device_id, command, response)
                    return
        
        # Check if this is one of the platform detection commands
        detected_platform = None
        is_platform_detection_command = False
        
        if device_id in self.platform_detection_status and self.platform_detection_status[device_id]['status'] == 'detecting_platform':
            if command == "cat /proc/panel_id":
                logger.info(f"Received platform detection response from {device_id}: {response}")
                detected_platform = self._detect_platform_from_panel_id(response)
                if detected_platform and detected_platform != NEED_ATHENA_CHECK:
                    logger.info(f"Detected platform from panel_id for device {device_id}: {detected_platform}")
                elif detected_platform == NEED_ATHENA_CHECK:
                    logger.info(f"Unknown panel_id for device {device_id}, checking for Athena platform")
                    self.platform_detection_status[device_id]['panel_id_response'] = response
                    athena_command = "cat /proc/device-tree/model"
                    worker.send_command(device_id, athena_command, 10)
                    if 'sent_commands' not in self.platform_detection_status[device_id]:
                        self.platform_detection_status[device_id]['sent_commands'] = set()
                    self.platform_detection_status[device_id]['sent_commands'].add(athena_command)
                else:
                    panel_id = response.strip().lower()
                    if "01" in panel_id:
                        logger.info(f"panel_id = 01 detected for device {device_id}, sending PIC version command to determine argo vs hydra_fhd")
                        self.platform_detection_status[device_id]['panel_id_response'] = response
                        pic_command = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2"
                        worker.send_command(device_id, pic_command, 10)
                        if 'sent_commands' not in self.platform_detection_status[device_id]:
                            self.platform_detection_status[device_id]['sent_commands'] = set()
                        self.platform_detection_status[device_id]['sent_commands'].add(pic_command)
                    else:
                        logger.info(f"panel_id detection failed for device {device_id}, checking for Athena platform")
                        self.platform_detection_status[device_id]['panel_id_response'] = response
                        athena_command = "cat /proc/device-tree/model"
                        worker.send_command(device_id, athena_command, 10)
                        if 'sent_commands' not in self.platform_detection_status[device_id]:
                            self.platform_detection_status[device_id]['sent_commands'] = set()
                        self.platform_detection_status[device_id]['sent_commands'].add(athena_command)
                is_platform_detection_command = True
            
            elif command == "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2":
                logger.info(f"Received PIC version response from {device_id}: {response}")
                if device_id in self.platform_detection_status:
                    detected_platform = self.platform_detection_status[device_id].get('detected_platform')
                    if detected_platform == 'athena':
                        self.command_result.emit(device_id, command, response)
                        return
                
                if not self._is_valid_pic_response(response):
                    logger.warning(f"Invalid PIC version response format from {device_id}: '{response}'")
                    self._retry_pic_command(device_id)
                    self.command_result.emit(device_id, command, response)
                    return
                
                pic_version = self._get_pic_version_from_response(response)
                logger.info(f"Valid PIC version received from {device_id}: {pic_version}")
                
                panel_id_response = self.platform_detection_status[device_id].get('panel_id_response', '')
                if "01" in panel_id_response.strip().lower():
                    detected_platform = self._detect_platform_from_panel_id_01(panel_id_response, response)
                    logger.info(f"Detected platform from panel_id=01 + PIC version for device {device_id}: {detected_platform}")
                else:
                    if '0x72' in response:
                        detected_platform = "argo"
                        logger.info(f"Detected platform from PIC version for device {device_id}: {detected_platform}")
                is_platform_detection_command = True
            
            elif command == "cat /proc/device-tree/model":
                logger.info(f"Received Athena check response from {device_id}: {response}")
                is_athena = self._is_athena_platform(response)
                logger.debug(f"Athena platform check result for device {device_id}: {is_athena}")
                
                if is_athena:
                    detected_platform = "athena"
                    logger.info(f"Detected Athena platform for device {device_id}")
                    if device_id in self.platform_detection_status:
                        self.platform_detection_status[device_id]['detected_platform'] = detected_platform
                        logger.info(f"Completing platform detection for Athena device {device_id}")
                        self._complete_platform_detection(device_id)
                    return
                else:
                    logger.warning(f"Not Athena platform, platform detection failed for device {device_id}")
                    detected_platform = None
                is_platform_detection_command = True
        
        if is_platform_detection_command and device_id in self.platform_detection_status:
            self.platform_detection_status[device_id]['command_results'][command] = response
            self.platform_detection_status[device_id]['completed_commands'].add(command)
            
            if detected_platform:
                self.platform_detection_status[device_id]['detected_platform'] = detected_platform
            
            expected_commands = {"cat /proc/panel_id"}
            pic_command = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2"
            athena_command = "cat /proc/device-tree/model"
            
            if 'sent_commands' not in self.platform_detection_status[device_id]:
                self.platform_detection_status[device_id]['sent_commands'] = set()
            
            sent_commands = self.platform_detection_status[device_id]['sent_commands']
            if pic_command in sent_commands:
                expected_commands.add(pic_command)
            if athena_command in sent_commands:
                expected_commands.add(athena_command)
            
            completed_commands = self.platform_detection_status[device_id]['completed_commands']
            
            if expected_commands.issubset(completed_commands):
                logger.info(f"All platform detection commands completed for device {device_id}")
                final_platform = self.platform_detection_status[device_id]['detected_platform']
                panel_id_response = self.platform_detection_status[device_id].get('panel_id_response', '')
                if "01" in panel_id_response.strip().lower() and not final_platform:
                    pic_version_response = self.platform_detection_status[device_id]['command_results'].get(pic_command, "")
                    if pic_version_response:
                        final_platform = self._detect_platform_from_panel_id_01(panel_id_response, pic_version_response)
                        self.platform_detection_status[device_id]['detected_platform'] = final_platform
                        logger.info(f"Final platform determination for panel_id=01 device {device_id}: {final_platform}")
                
                if not final_platform:
                    logger.warning(f"No platform detected for device {device_id} after all commands completed, defaulting to hydra_fhd")
                    final_platform = 'hydra_fhd'
                    self.platform_detection_status[device_id]['detected_platform'] = final_platform
                
                self._complete_platform_detection(device_id)
        
        self.command_result.emit(device_id, command, response)

    def _check_platform_detection_complete(self, device_id: str) -> bool:
        # Dummy function representing the logic to check if detection is done
        return 'detected_platform' in self.platform_detection_status[device_id] and self.platform_detection_status[device_id]['detected_platform'] is not None

    def _complete_platform_detection(self, device_id: str):
        """Complete platform detection process for a device"""
        if device_id not in self.platform_detection_status:
            return
        
        final_platform = self.platform_detection_status[device_id].get('detected_platform')
        
        if not final_platform:
            device_port = self.connected_devices.get(device_id, {}).get('address', 'Unknown')
            self.platform_detection_failed.emit(device_id, device_port)
            del self.platform_detection_status[device_id]
            return
        
        logger.info(f"Platform detection completed for device {device_id}: {final_platform}")
        
        worker = self._get_worker_for_device(device_id)
        if (self.system_info_service is None or self.hardware_test_manager is None or self.platform_name != final_platform) and worker:
            self.platform_name = final_platform
            self._initialize_services(worker, final_platform)
            logger.info(f"Services initialized with detected platform: {final_platform}")
        
        del self.platform_detection_status[device_id]
    
    def connect_serial_device(self, device_id: str, port: str, baudrate: int = 115200, timeout: int = 3):
        """Connect serial device"""
        if device_id in self.connected_devices:
            self.connection_result.emit(device_id, False, f"Device {device_id} is already connected")
            return
        self._serial_worker.connect_device(device_id, port, baudrate, timeout)

    def connect_tcp_ip_device(self, device_id: str, host: str, port: int, timeout: int = 5):
        """Connect TCP/IP device"""
        if device_id in self.connected_devices:
            self.connection_result.emit(device_id, False, f"Device {device_id} is already connected")
            return
        self._tcp_ip_worker.connect_device(device_id, host, port, timeout)
        
    def disconnect_device(self, device_id: str):
        """Disconnect device"""
        if device_id not in self.connected_devices:
            self.disconnection_result.emit(device_id, False, f"Device {device_id} is not connected")
            return
        worker = self._get_worker_for_device(device_id)
        if worker:
            worker.disconnect_device(device_id)
        
    def send_command(self, device_id: str, command: str, timeout: int = 5):
        """Send command to device"""
        if device_id not in self.connected_devices:
            self.command_result.emit(device_id, command, f"Error: Device {device_id} is not connected")
            return
        worker = self._get_worker_for_device(device_id)
        if worker:
            worker.send_command(device_id, command, timeout)
    
    def send_ctrl_c(self, device_id: str):
        """Send CTRL+C interrupt signal to device"""
        if device_id not in self.connected_devices:
            self.command_result.emit(device_id, "CTRL+C", f"Error: Device {device_id} is not connected")
            return
        worker = self._get_worker_for_device(device_id)
        if worker and hasattr(worker, 'send_ctrl_c'):
            worker.send_ctrl_c(device_id)
    
    def send_control_sequence(self, device_id: str, control_char: str):
        """Send control character sequence to device"""
        if device_id not in self.connected_devices:
            self.command_result.emit(device_id, f"CONTROL:{control_char}", f"Error: Device {device_id} is not connected")
            return
        worker = self._get_worker_for_device(device_id)
        if worker:
            worker.send_control_sequence(device_id, control_char)
        
    def get_connected_devices(self) -> List[Dict[str, Any]]:
        """Get list of connected devices"""
        return list(self.connected_devices.values())
        
    def disconnect_all_devices(self):
        """Disconnect all devices"""
        for device_id in list(self.connected_devices.keys()):
            self.disconnect_device(device_id)

    def update_device_info(self, device_id: str, details: Dict[str, Any]):
        """Update device details"""
        if device_id in self.connected_devices:
            self.connected_devices[device_id]['details'].update(details)
            self.device_list_changed.emit(list(self.connected_devices.values()))

    def set_platform(self, platform_name: str):
        """
        Set the platform name and update dependent services
        
        Args:
            platform_name: Platform name to use
        """
        self.platform_name = platform_name
        if hasattr(self, 'system_info_service') and self.system_info_service:
            self.system_info_service.set_platform(platform_name)
        if hasattr(self, 'hardware_test_manager') and self.hardware_test_manager and hasattr(self.hardware_test_manager, 'set_platform'):
            self.hardware_test_manager.set_platform(platform_name)

    def are_services_initialized(self) -> bool:
        """Check if all required services are initialized"""
        return (self.system_info_service is not None and 
                self.hardware_test_manager is not None and
                self.smart_monitor is not None)
    
    def get_services_status(self) -> dict:
        """Get detailed status of service initialization"""
        return {
            'system_info_service': self.system_info_service is not None,
            'hardware_test_manager': self.hardware_test_manager is not None,
            'smart_monitor': self.smart_monitor is not None,
            'all_initialized': self.are_services_initialized(),
            'platform_name': self.platform_name
        }

    def _detect_platform_from_panel_id(self, panel_id_response: str) -> Optional[str]:
        response = panel_id_response.strip().lower()
        logger.debug(f"Analyzing panel_id response: '{response}'")
        error_patterns = ["error", "no response", "no such file", "not found", "permission denied", "command not found"]
        if response == "" or any(pattern in response for pattern in error_patterns):
            logger.warning(f"Invalid panel_id response: '{panel_id_response}', platform detection failed")
            return None
        if "01" in response:
            logger.debug("panel_id = 01 detected, need PIC version check to distinguish argo vs hydra_fhd")
            return None
        elif "00" in response:
            return "hydra"
        elif "10" in response:
            return "gemini_fhd"
        elif "11" in response:
            return "gemini"
        else:
            logger.warning(f"Unknown panel_id response: '{panel_id_response}', checking for Athena platform")
            return NEED_ATHENA_CHECK

    def _detect_platform_from_panel_id_01(self, panel_id_response: str, pic_version_response: str) -> Optional[str]:
        logger.debug(f"Analyzing panel_id=01 with PIC version: '{pic_version_response}'")
        pic_response_lower = pic_version_response.strip().lower()
        if "error" in pic_response_lower or "no response" in pic_response_lower:
            logger.warning(f"Invalid PIC version response for panel_id=01: '{pic_version_response}', defaulting to hydra_fhd")
            return "hydra_fhd"
        if '0x72' in pic_version_response:
            logger.info(f"Detected argo platform: panel_id=01 + PIC version contains 0x72")
            return "argo"
        else:
            logger.info(f"Detected hydra_fhd platform: panel_id=01 + PIC version does not contain 0x72")
            return "hydra_fhd"

    def _is_valid_pic_response(self, response: str) -> bool:
        clean_response = response.strip()
        response_lower = clean_response.lower()
        if "error" in response_lower or "no response" in response_lower or not clean_response:
            return False
        valid_patterns = ['0x00 0x64', '0x00 0x6e', '0x00 0x72']
        for pattern in valid_patterns:
            if pattern in clean_response:
                logger.debug(f"Valid PIC response pattern found: {pattern}")
                return True
        logger.debug(f"Invalid PIC response format: '{clean_response}'")
        return False

    def _get_pic_version_from_response(self, response: str) -> Optional[str]:
        clean_response = response.strip()
        if '0x00 0x64' in clean_response:
            return 'v100'
        elif '0x00 0x6d' in clean_response:
            return 'v110'
        elif '0x00 0x72' in clean_response:
            return 'v114'
        else:
            return None

    def _is_athena_platform(self, response: str) -> bool:
        clean_response = response.strip()
        logger.info(f"Checking Athena platform with response: '{clean_response}'")
        return "Athena-030" in clean_response

    def _retry_pic_command(self, device_id: str):
        if device_id not in self.platform_detection_status:
            return
        detected_platform = self.platform_detection_status[device_id].get('detected_platform')
        if detected_platform == 'athena':
            return
        retry_count = self.platform_detection_status[device_id].get('pic_retry_count', 0)
        max_retries = self.pic_command_retry_config['max_retries']
        if retry_count >= max_retries:
            logger.error(f"PIC command retry limit reached for device {device_id}")
            self.platform_detection_status[device_id]['detected_platform'] = 'hydra_fhd'
            self._complete_platform_detection(device_id)
            return
        self.platform_detection_status[device_id]['pic_retry_count'] = retry_count + 1
        logger.info(f"Retrying PIC command for device {device_id} (attempt {retry_count + 1}/{max_retries})")
        retry_timer = QTimer()
        retry_timer.timeout.connect(lambda: self._execute_pic_retry(device_id, retry_timer))
        retry_timer.setSingleShot(True)
        retry_timer.start(int(self.pic_command_retry_config['retry_delay'] * 1000))

    def _execute_pic_retry(self, device_id: str, timer: QTimer):
        timer.deleteLater()
        if device_id not in self.platform_detection_status:
            return
        logger.info(f"Executing PIC command retry for device {device_id}")
        worker = self._get_worker_for_device(device_id)
        if worker:
            pic_command = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2"
            worker.send_command(device_id, pic_command, 10)

    # Connection monitoring methods
    def start_device_monitoring(self, device_id: str, check_interval: int = 10000):
        """Start smart monitoring for device connection status"""
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
        """Set device busy status to pause/resume monitoring"""
        if self.smart_monitor:
            self.smart_monitor.set_device_busy(device_id, is_busy)
            state = "busy" if is_busy else "free"
            logger.debug(f"Device {device_id} marked as {state}")
        else:
            logger.warning("Smart monitor not initialized, cannot set device busy state")
            
    def check_device_ready_immediately(self, device_id: str):
        """Immediately check if the device is ready to receive commands"""
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
    
    def start_usb_package_deployment(self, device_id: str, on_success: callable = None, on_failure: callable = None):
        """Start USB package deployment for a device"""
        logger.info(f"Starting USB package deployment for device {device_id}")
        if not self.usb_package_deploy_service:
            if on_failure:
                on_failure("USB package deploy service not initialized")
            return
        if self.usb_package_deploy_service.is_deployment_in_progress(device_id):
            if on_failure:
                on_failure("USB package deployment already in progress")
            return
        self.usb_package_deploy_service.start_deployment(device_id, on_success, on_failure)
    
    def get_usb_deployment_status(self, device_id: str) -> dict:
        """Get USB deployment status for a device"""
        if self.usb_package_deploy_service:
            return self.usb_package_deploy_service.get_deployment_status(device_id) or {}
        return {}
    
    def cancel_usb_deployment(self, device_id: str):
        """Cancel USB deployment for a device"""
        if self.usb_package_deploy_service:
            self.usb_package_deploy_service.cancel_deployment(device_id)


    # ... (rest of the methods like are_services_initialized, start_device_monitoring, etc. remain mostly the same) ...
    # The key change is that they indirectly use the correct worker via the generalized send_command method.

