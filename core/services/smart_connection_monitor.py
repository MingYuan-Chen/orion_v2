from PySide6.QtCore import QObject, Signal, QTimer
from typing import Dict, List, Set
from util.logger import logger
import time

class SmartConnectionMonitor(QObject):
    """
    Smart connection monitor service
    
    A connection monitoring service that avoids conflicts with running tests or commands
    """
    
    # Signal definitions
    device_ready = Signal(str)  # device_id - device is ready
    device_not_ready = Signal(str, str)  # device_id, reason - device is not ready
    connection_status_changed = Signal(str, bool)  # device_id, is_ready
    
    def __init__(self, serial_worker):
        super().__init__()
        self.serial_worker = serial_worker
        self.monitoring_devices = {}  # device_id -> monitor_config
        self.busy_devices = set()  # devices that are executing other operations
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._perform_health_checks)
        
        # Connect to the serial device worker's signal
        self.serial_worker.command_result.connect(self._on_command_result)
        
        # Monitor command identifier
        self.monitor_command_prefix = "CONNECTION_MONITOR_"
        
    def start_monitoring(self, device_id: str, check_interval: int = 10000, 
                        max_failures: int = 1):
        """
        Start monitoring device connection status
        
        Args:
            device_id: device ID
            check_interval: check interval (milliseconds), default 10 seconds to avoid frequent interference
            max_failures: maximum failure count (default 1, report error after one failure)
        """
        # Use a longer check interval to reduce interference with other operations
        self.monitoring_devices[device_id] = {
            'max_failures': max_failures,
            'failure_count': 0,
            'last_success_time': None,
            'is_ready': False,
            'last_check_time': 0,
            'check_interval': check_interval,
            'original_check_interval': check_interval,  # save original check interval
            'failed_completely': False  # mark if it has completely failed
        }
        
        logger.info(f"Started smart monitoring for device {device_id} with {check_interval}ms interval")
        
        # If this is the first device being monitored, start the timer
        if len(self.monitoring_devices) == 1:
            # Use a shorter timer interval to check, but the actual check frequency is controlled by the device configuration
            self.check_timer.setInterval(5000)  # check every 5 seconds to see if monitoring needs to be performed
            self.check_timer.start()
            
    def stop_monitoring(self, device_id: str):
        """Stop monitoring the specified device"""
        if device_id in self.monitoring_devices:
            del self.monitoring_devices[device_id]
            logger.info(f"Stopped smart monitoring for device {device_id}")
            
        # If no devices need to be monitored, stop the timer
        if not self.monitoring_devices:
            self.check_timer.stop()
            
    def set_device_busy(self, device_id: str, is_busy: bool):
        """
        Set device busy status
        When the device is executing tests or other important operations, pause monitoring
        
        Args:
            device_id: device ID
            is_busy: True=device busy, pause monitoring; False=device free, can monitor
        """
        if is_busy:
            self.busy_devices.add(device_id)
            logger.debug(f"Device {device_id} marked as busy - monitoring paused")
        else:
            self.busy_devices.discard(device_id)
            logger.debug(f"Device {device_id} marked as free - monitoring resumed")
            
    def _perform_health_checks(self):
        """Perform health checks, but only check non-busy devices"""
        current_time = time.time() * 1000  # convert to milliseconds
        
        for device_id, config in self.monitoring_devices.items():
            # Skip busy devices
            if device_id in self.busy_devices:
                logger.debug(f"Skipping health check for busy device {device_id}")
                continue
                
            # Check if it's time to check
            time_since_last_check = current_time - config['last_check_time']
            if time_since_last_check >= config['check_interval']:
                self._check_single_device(device_id)
                config['last_check_time'] = current_time
                
    def _check_single_device(self, device_id: str):
        """Check the connection status of a single device"""
        monitor_config = self.monitoring_devices.get(device_id)
        if not monitor_config:
            return
            
        # Confirm the device is not busy
        if device_id in self.busy_devices:
            return
            
        # Generate a unique monitoring command to avoid conflicts with other commands
        timestamp = int(time.time() * 1000)
        unique_ping_command = f"{self.monitor_command_prefix}{timestamp}"
        monitor_command = f"root"
        
        logger.debug(f"Smart health check for device {device_id}: {monitor_command}")
        
        # Send the monitoring command, using a shorter timeout
        self.serial_worker.send_command(device_id, monitor_command, 3)
        
    def _on_command_result(self, device_id: str, command: str, response: str):
        """Process command results, only process the monitor's own commands"""
        # Only process the monitor's own commands
        if command != "root":
            return
            
        monitor_config = self.monitoring_devices.get(device_id)
        if not monitor_config:
            return
        
        # Check if the response is valid
        is_success = self._is_valid_monitor_response(response)
        
        if is_success:
            # Device response successful
            monitor_config['failure_count'] = 0
            monitor_config['last_success_time'] = time.time()
            
            # If the device recovers from a failed state, reset the check interval
            if monitor_config['failed_completely']:
                monitor_config['failed_completely'] = False
                monitor_config['check_interval'] = monitor_config['original_check_interval']
                logger.info(f"Device {device_id} recovered, restoring normal check frequency")
            
            if not monitor_config['is_ready']:
                monitor_config['is_ready'] = True
                logger.info(f"Device {device_id} is ready (smart monitor)")
                self.device_ready.emit(device_id)
                self.connection_status_changed.emit(device_id, True)
        else:
            # Device response failed - report immediately, no retry
            monitor_config['failure_count'] += 1
            logger.warning(f"Device {device_id} health check failed ({monitor_config['failure_count']}/{monitor_config['max_failures']})")
            
            # If it fails once, report immediately and stop monitoring
            monitor_config['is_ready'] = False
            reason = f"Device connection check failed"
            logger.error(f"Device {device_id} not ready: {reason}")
            
            # Immediately stop monitoring the device
            logger.info(f"Stopping monitoring for device {device_id} due to connection failure")
            self.stop_monitoring(device_id)
            
            # Send failure signal
            self.device_not_ready.emit(device_id, reason)
            self.connection_status_changed.emit(device_id, False)
                    
    def _is_valid_monitor_response(self, actual_response: str) -> bool:
        """Verify the response of the monitoring command"""
            
        # Check for login-related indicators (device needs authentication)
        login_indicators = ["Password:", "Login incorrect", "gemini login:", "login:", "Username:"]
        response_lower = actual_response.lower()
        for login_indicator in login_indicators:
            if login_indicator.lower() in response_lower:
                logger.warning(f"Device requires authentication: {actual_response.strip()}")
                return False
            
        # Check for obvious error indicators
        error_indicators = ["Error:", "No such file", "Permission denied"]
        for error in error_indicators:
            if error.lower() in response_lower:
                return False
                
        return True
        
    def get_device_status(self, device_id: str) -> Dict:
        """Get device status information"""
        monitor_config = self.monitoring_devices.get(device_id)
        if not monitor_config:
            return {'monitored': False}
            
        return {
            'monitored': True,
            'is_ready': monitor_config['is_ready'],
            'failure_count': monitor_config['failure_count'],
            'max_failures': monitor_config['max_failures'],
            'last_success_time': monitor_config['last_success_time'],
            'is_busy': device_id in self.busy_devices,
            'check_interval': monitor_config['check_interval'],
            'failed_completely': monitor_config['failed_completely']
        }
        
    def is_device_ready(self, device_id: str) -> bool:
        """Check if the device is ready"""
        monitor_config = self.monitoring_devices.get(device_id)
        return monitor_config['is_ready'] if monitor_config else False
        
    def get_busy_devices(self) -> Set[str]:
        """Get the list of currently busy devices"""
        return self.busy_devices.copy() 