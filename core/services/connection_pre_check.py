"""
Connection pre-check service module

A service that confirms the normal connection status of the device before executing the main operation
"""

from PySide6.QtCore import QObject, Signal, QTimer
from typing import Dict, Callable, Optional
from util.logger import logger
import time

class ConnectionPreCheckService(QObject):
    """
    Connection pre-check service
    
    Provides connection status confirmation for main operations:
    1. Start a brief connection monitoring
    2. Confirm the device connection is normal
    3. Close the connection monitoring
    4. Execute the main operation
    """
    
    # Signal definitions
    pre_check_started = Signal(str)  # device_id - pre-check started
    pre_check_completed = Signal(str, bool)  # device_id, success - pre-check completed
    pre_check_failed = Signal(str, str)  # device_id, reason - pre-check failed
    operation_ready_to_start = Signal(str)  # device_id - can start executing operation
    
    def __init__(self, device_manager_vm):
        super().__init__()
        self.device_manager_vm = device_manager_vm
        self.pending_operations = {}  # device_id -> operation_info
        self.check_timeout = 5000  # 8 seconds timeout
        
        # Connect to the smart connection monitor signal
        if hasattr(self.device_manager_vm, 'device_ready_for_commands'):
            self.device_manager_vm.device_ready_for_commands.connect(self._on_device_ready)
        if hasattr(self.device_manager_vm, 'device_connection_lost'):
            self.device_manager_vm.device_connection_lost.connect(self._on_device_lost)
    
    def execute_with_pre_check(self, device_id: str, operation_name: str, 
                              operation_callback: Callable, 
                              on_success: Optional[Callable] = None,
                              on_failure: Optional[Callable] = None,
                              check_timeout: int = 5000):
        """
        Execute the operation with pre-check
        
        Args:
            device_id: device ID
            operation_name: operation name (for logging)
            operation_callback: the operation callback function to be executed
            on_success: success callback function
            on_failure: failure callback function
            check_timeout: check timeout (milliseconds)
        """
        logger.info(f"Starting pre-check for {operation_name} on device {device_id}")
        
        # Save operation information
        self.pending_operations[device_id] = {
            'operation_name': operation_name,
            'operation_callback': operation_callback,
            'on_success': on_success,
            'on_failure': on_failure,
            'check_timeout': check_timeout,
            'start_time': time.time()
        }
        
        # Send pre-check started signal
        self.pre_check_started.emit(device_id)
        
        # Check if it is already being monitored
        if self._is_already_monitoring(device_id):
            logger.debug(f"Device {device_id} already being monitored, checking status immediately")
            self._check_immediate_status(device_id)
        else:
            # Start connection monitoring
            logger.debug(f"Starting connection monitoring for device {device_id}")
            self._start_monitoring(device_id, check_timeout)
        
        # Set timeout timer
        QTimer.singleShot(check_timeout, lambda: self._handle_check_timeout(device_id))
    
    def _is_already_monitoring(self, device_id: str) -> bool:
        """Check if the device is already being monitored"""
        try:
            status = self.device_manager_vm.get_device_connection_status(device_id)
            return status.get('monitored', False)
        except Exception as e:
            logger.warning(f"Error checking monitoring status for {device_id}: {e}")
            return False
    
    def _check_immediate_status(self, device_id: str):
        """Immediately check the device status"""
        try:
            # Trigger immediate health check
            self.device_manager_vm.check_device_ready_immediately(device_id)
            
            # Check the result after a brief delay
            QTimer.singleShot(500, lambda: self._verify_device_status(device_id))
            
        except Exception as e:
            logger.error(f"Error during immediate status check for {device_id}: {e}")
            self._handle_check_failure(device_id, f"Status check error: {str(e)}")
    
    def _verify_device_status(self, device_id: str):
        """Verify the device status"""
        try:
            is_ready = self.device_manager_vm.is_device_ready_for_commands(device_id)
            
            if is_ready:
                logger.info(f"Device {device_id} verified as ready")
                self._handle_check_success(device_id)
            else:
                # Wait longer for the monitor to complete the check
                QTimer.singleShot(500, lambda: self._final_status_check(device_id))
                
        except Exception as e:
            logger.error(f"Error verifying device status for {device_id}: {e}")
            self._handle_check_failure(device_id, f"Status verification error: {str(e)}")
    
    def _final_status_check(self, device_id: str):
        """Final status check"""
        try:
            is_ready = self.device_manager_vm.is_device_ready_for_commands(device_id)
            
            if is_ready:
                logger.info(f"Device {device_id} ready after final check")
                self._handle_check_success(device_id)
            else:
                status = self.device_manager_vm.get_device_connection_status(device_id)
                reason = f"Device not ready after monitoring. Status: {status}"
                logger.warning(f"Device {device_id} not ready: {reason}")
                self._handle_check_failure(device_id, reason)
                
        except Exception as e:
            logger.error(f"Error during final status check for {device_id}: {e}")
            self._handle_check_failure(device_id, f"Final check error: {str(e)}")
    
    def _start_monitoring(self, device_id: str, check_timeout: int):
        """Start device monitoring"""
        try:
            # Use a shorter check interval for quick monitoring
            self.device_manager_vm.start_device_monitoring(device_id, check_interval=500)
            logger.debug(f"Connection monitoring started for device {device_id}")
            
        except Exception as e:
            logger.error(f"Error starting monitoring for {device_id}: {e}")
            self._handle_check_failure(device_id, f"Monitoring start error: {str(e)}")
    
    def _on_device_ready(self, device_id: str):
        """Device ready callback"""
        if device_id in self.pending_operations:
            logger.info(f"Device {device_id} confirmed ready via signal")
            self._handle_check_success(device_id)
    
    def _on_device_lost(self, device_id: str, reason: str):
        """Device connection lost callback"""
        if device_id in self.pending_operations:
            logger.warning(f"Device {device_id} connection lost during pre-check: {reason}")
            self._handle_check_failure(device_id, reason)
    
    def _handle_check_success(self, device_id: str):
        """Handle check success"""
        if device_id not in self.pending_operations:
            return
            
        operation_info = self.pending_operations[device_id]
        operation_name = operation_info['operation_name']
        
        logger.info(f"Pre-check successful for {operation_name} on device {device_id}")
        
        # Stop monitoring (if we started it)
        self._stop_monitoring_if_needed(device_id)
        
        # Send check completed signal
        self.pre_check_completed.emit(device_id, True)
        self.operation_ready_to_start.emit(device_id)
        
        # Execute the target operation
        try:
            operation_callback = operation_info['operation_callback']
            operation_callback()
            
            # Call success callback
            if operation_info['on_success']:
                operation_info['on_success']()
                
        except Exception as e:
            logger.error(f"Error executing operation {operation_name} for {device_id}: {e}")
            if operation_info['on_failure']:
                operation_info['on_failure'](f"Operation execution error: {str(e)}")
        
        # Clean up pending operations - 添加檢查避免KeyError
        if device_id in self.pending_operations:
            del self.pending_operations[device_id]
    
    def _handle_check_failure(self, device_id: str, reason: str):
        """Handle check failure"""
        if device_id not in self.pending_operations:
            return
            
        operation_info = self.pending_operations[device_id]
        operation_name = operation_info['operation_name']
        
        logger.error(f"Pre-check failed for {operation_name} on device {device_id}: {reason}")
        
        # Stop monitoring (if we started it)
        self._stop_monitoring_if_needed(device_id)
        
        # Send check failed signal
        self.pre_check_failed.emit(device_id, reason)
        self.pre_check_completed.emit(device_id, False)
        
        # Call failure callback
        if operation_info['on_failure']:
            operation_info['on_failure'](reason)
        
        # Clean up pending operations - add check to avoid KeyError
        if device_id in self.pending_operations:
            del self.pending_operations[device_id]
    
    def _handle_check_timeout(self, device_id: str):
        """Handle check timeout"""
        if device_id in self.pending_operations:
            operation_info = self.pending_operations[device_id]
            elapsed_time = time.time() - operation_info['start_time']
            
            if elapsed_time >= (operation_info['check_timeout'] / 1000):
                logger.warning(f"Pre-check timeout for device {device_id} after {elapsed_time:.1f}s")
                self._handle_check_failure(device_id, f"Pre-check timeout after {elapsed_time:.1f}s")
    
    def _stop_monitoring_if_needed(self, device_id: str):
        """Stop monitoring if needed"""
        try:
            # Stop device monitoring
            self.device_manager_vm.stop_device_monitoring(device_id)
            logger.debug(f"Stopped monitoring for device {device_id}")
            
        except Exception as e:
            logger.warning(f"Error stopping monitoring for {device_id}: {e}")
    
    def cancel_pre_check(self, device_id: str):
        """Cancel pre-check"""
        if device_id in self.pending_operations:
            operation_info = self.pending_operations[device_id]
            operation_name = operation_info['operation_name']
            
            logger.info(f"Cancelling pre-check for {operation_name} on device {device_id}")
            
            # Stop monitoring
            self._stop_monitoring_if_needed(device_id)
            
            # Clean up pending operations
            del self.pending_operations[device_id]
    
    def get_pending_operations(self) -> Dict[str, Dict]:
        """Get pending operations list"""
        return self.pending_operations.copy()
    
    def cleanup(self):
        """Clean up resources"""
        logger.debug("Cleaning up ConnectionPreCheckService")
        
        # Cancel all pending operations
        for device_id in list(self.pending_operations.keys()):
            self.cancel_pre_check(device_id)
        
        # Dis
        try:
            if hasattr(self.device_manager_vm, 'device_ready_for_commands'):
                self.device_manager_vm.device_ready_for_commands.disconnect(self._on_device_ready)
            if hasattr(self.device_manager_vm, 'device_connection_lost'):
                self.device_manager_vm.device_connection_lost.disconnect(self._on_device_lost)
        except Exception:
            pass
        
        logger.info("ConnectionPreCheckService cleanup completed") 