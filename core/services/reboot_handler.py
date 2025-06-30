"""
Reboot Handler Service

Special reboot handler for device reboot and login check
"""

from PySide6.QtCore import QObject, Signal, QTimer
from typing import Dict, Optional
import time
from util.logger import logger

class RebootHandler(QObject):
    """
    Device reboot handler
    
    Handle device reboot command and wait for device to complete login
    """
    
    # Signal definitions
    reboot_completed = Signal(str, str, str)  # device_id, command, response
    reboot_failed = Signal(str, str, str)     # device_id, command, error_message
    
    def __init__(self, device_manager):
        """
        Initialize reboot handler
        
        Args:
            device_manager: Device manager, used to execute underlying commands
        """
        super().__init__()
        self.device_manager = device_manager
        
        # Reboot status tracking
        self.rebooting_devices = {}  # device_id -> reboot_info
        
        # Configuration parameters
        self.login_check_interval = 2000  # Check interval 2 seconds
        self.max_login_attempts = 30      # Maximum attempts (60 seconds timeout)
        self.command_timeout = 3          # Single command timeout
        self.login_check_command = "root"  # Login check command
        # Optional check commands:
        # "root" - If device supports
        # "echo ready" - More general, always successful
        # "whoami" - Check current user
        # "pwd" - Check current directory
        
        # Using QTimer.singleShot to avoid thread issues
        self.check_timer = None
        
        logger.info("RebootHandler initialized")
    
    def handle_reboot(self, device_id: str, timeout: int = 60):
        """
        Handle device reboot command
        
        Args:
            device_id: Device ID
            timeout: Timeout (seconds)
        """
        if device_id in self.rebooting_devices:
            logger.warning(f"Device {device_id} is already rebooting")
            self.reboot_failed.emit(device_id, "reboot", "Device is already rebooting")
            return
        
        # Ensure reboot timeout is long enough (at least 60 seconds)
        reboot_timeout = max(timeout, 60)
        if reboot_timeout != timeout:
            logger.info(f"Extending reboot timeout from {timeout}s to {reboot_timeout}s for device {device_id}")
        
        logger.info(f"Starting reboot process for device {device_id} with {reboot_timeout}s timeout")
        
        # Record reboot status
        self.rebooting_devices[device_id] = {
            'start_time': time.time(),
            'timeout': reboot_timeout,
            'login_attempts': 0,
            'phase': 'rebooting'  # rebooting -> checking_login -> completed/failed
        }
        
        try:
            # Execute reboot command
            logger.info(f"REBOOT: [{device_id}] >>> reboot")
            response = self.device_manager.send_command(device_id, "reboot", self.command_timeout)
            logger.info(f"REBOOT: [{device_id}] <<< {response}")
            
            # Update state to checking login phase
            self.rebooting_devices[device_id]['phase'] = 'checking_login'
            
            # Use QTimer.singleShot to schedule first login check
            QTimer.singleShot(self.login_check_interval, lambda dev_id=device_id: self._check_single_device_login(dev_id))
                
            logger.info(f"Reboot command sent, starting login verification for device {device_id}")
            
        except Exception as e:
            logger.error(f"Failed to send reboot command to device {device_id}: {e}")
            self._cleanup_reboot_state(device_id)
            self.reboot_failed.emit(device_id, "reboot", f"Failed to send reboot command: {str(e)}")
    
    def _check_single_device_login(self, device_id: str):
        """Check login status of a single device"""
        reboot_info = self.rebooting_devices.get(device_id)
        if not reboot_info or reboot_info['phase'] != 'checking_login':
            # Device is no longer in reboot list or state has changed, skip check
            logger.debug(f"Device {device_id} no longer in reboot process, skipping check")
            return
        
        current_time = time.time()
        
        # Check if timeout
        elapsed_time = current_time - reboot_info['start_time']
        if elapsed_time > reboot_info['timeout']:
            logger.error(f"Reboot timeout for device {device_id} after {elapsed_time:.1f}s")
            self.reboot_failed.emit(device_id, "reboot", f"Reboot timeout after {elapsed_time:.1f}s")
            self._cleanup_reboot_state(device_id)
            return
        
        # Check if maximum attempts reached
        if reboot_info['login_attempts'] >= self.max_login_attempts:
            logger.error(f"Max login attempts reached for device {device_id}")
            self.reboot_failed.emit(device_id, "reboot", "Max login attempts reached")
            self._cleanup_reboot_state(device_id)
            return
        
        # Try sending root command to check login status
        try:
            reboot_info['login_attempts'] += 1
            
            logger.debug(f"LOGIN_CHECK: [{device_id}] >>> {self.login_check_command} (attempt {reboot_info['login_attempts']}/{self.max_login_attempts})")
            
            # Send login check command
            response = self.device_manager.send_command(device_id, self.login_check_command, self.command_timeout)
            
            logger.debug(f"LOGIN_CHECK: [{device_id}] <<< {response}")
            
            # Check if response is valid (no errors)
            if self._is_valid_login_response(response):
                # Login successful
                logger.info(f"Device {device_id} login successful after {reboot_info['login_attempts']} attempts")
                elapsed_time = time.time() - reboot_info['start_time']
                
                # Send success signal
                success_message = f"reboot and login os complete (took {elapsed_time:.1f}s, {reboot_info['login_attempts']} attempts)"
                self.reboot_completed.emit(device_id, "reboot", success_message)
                
                # Clean up state
                self._cleanup_reboot_state(device_id)
            else:
                # Login failed, schedule next check
                logger.debug(f"Device {device_id} not ready yet, will retry in {self.login_check_interval/1000}s")
                QTimer.singleShot(self.login_check_interval, lambda dev_id=device_id: self._check_single_device_login(dev_id))
                
        except Exception as e:
            logger.warning(f"Login check failed for device {device_id}: {e}")
            # Schedule next check, not immediately fail
            QTimer.singleShot(self.login_check_interval, lambda dev_id=device_id: self._check_single_device_login(dev_id))
    

    
    def _is_valid_login_response(self, response: str) -> bool:
        """
        Check if login response is valid
        
        Simplified logic: only when response is exactly "-sh: root: command not found" is considered successful
        
        Args:
            response: Command response
            
        Returns:
            bool: True if login successful, False if needs to wait
        """
        if not response or not response.strip():
            logger.debug("Empty response, device not ready")
            return False
        
        # Remove leading/trailing whitespace
        response_clean = response.strip()
        
        # Only check specific success response string
        success_response = "-sh: root: command not found"
        
        if response_clean == success_response:
            logger.debug(f"Login success detected: {response_clean}")
            return True
        
        # All other responses indicate device not ready
        logger.debug(f"Response doesn't indicate login success: {response_clean}")
        return False
    
    def _cleanup_reboot_state(self, device_id: str):
        """Clean up device reboot state"""
        if device_id in self.rebooting_devices:
            del self.rebooting_devices[device_id]
            logger.debug(f"Cleaned up reboot state for device {device_id}")
    
    def cancel_reboot(self, device_id: str):
        """Cancel device reboot waiting"""
        if device_id in self.rebooting_devices:
            logger.info(f"Cancelling reboot process for device {device_id}")
            self._cleanup_reboot_state(device_id)
            self.reboot_failed.emit(device_id, "reboot", "Reboot cancelled by user")
    
    def get_rebooting_devices(self) -> Dict[str, Dict]:
        """Get list of devices currently rebooting"""
        return self.rebooting_devices.copy()
    
    def is_device_rebooting(self, device_id: str) -> bool:
        """Check if device is currently rebooting"""
        return device_id in self.rebooting_devices
    
    def set_login_check_command(self, command: str):
        """
        Set login check command
        
        Args:
            command: Check command, e.g.:
                    "root" - Default command (if device supports)
                    "echo ready" - More general, always successful
                    "whoami" - Check current user
                    "pwd" - Check current directory
        """
        self.login_check_command = command
        logger.info(f"Login check command set to: {command}")
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("RebootHandler cleanup")
        
        # Clean up all reboot states
        self.rebooting_devices.clear() 