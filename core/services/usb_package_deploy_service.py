"""
USB Package Deploy Service Module

A service that scans USB devices and deploys dqa_package to the device root directory
"""

from PySide6.QtCore import QObject, Signal, QTimer
from typing import Dict, Optional, List
from util.logger import logger
import os
import time

class UsbPackageDeployService(QObject):
    """
    USB Package Deploy Service
    
    Scans connected USB devices and deploys dqa_package to device root directory:
    1. Scan all connected USB devices
    2. Check if dqa_package folder exists on each USB device
    3. Copy dqa_package to device root directory /dqa_package
    4. Complete and signal ready for system info service
    """
    
    # Signal definitions
    deployment_started = Signal(str)  # device_id - deployment started
    deployment_progress = Signal(str, str)  # device_id, progress_message
    deployment_completed = Signal(str, bool, str)  # device_id, success, message
    deployment_failed = Signal(str, str)  # device_id, reason
    ready_for_system_info = Signal(str)  # device_id - ready to start system info service
    
    def __init__(self, device_manager_vm):
        """
        Initialize USB Package Deploy Service
        
        Args:
            device_manager_vm: Device manager view model for device communication
        """
        super().__init__()
        self.device_manager_vm = device_manager_vm
        self.pending_deployments = {}  # device_id -> deployment_info
        self.deployment_timeout = 60000  # 60 seconds timeout
        
        logger.info("USB Package Deploy Service initialized")
    
    def start_deployment(self, device_id: str, on_success: Optional[callable] = None, 
                        on_failure: Optional[callable] = None):
        """
        Start USB package deployment for a device
        
        Args:
            device_id: Target device ID
            on_success: Success callback function
            on_failure: Failure callback function
        """
        logger.info(f"Starting USB package deployment for device {device_id}")
        
        # Save deployment information
        self.pending_deployments[device_id] = {
            'on_success': on_success,
            'on_failure': on_failure,
            'start_time': time.time(),
            'usb_devices_found': [],
            'packages_deployed': []
        }
        
        # Emit deployment started signal
        self.deployment_started.emit(device_id)
        
        # Start deployment process
        self._scan_usb_devices(device_id)
        
        # Set timeout timer
        QTimer.singleShot(self.deployment_timeout, lambda: self._handle_deployment_timeout(device_id))
    
    def _scan_usb_devices(self, device_id: str):
        """
        Scan for connected USB devices
        
        Args:
            device_id: Target device ID
        """
        try:
            logger.info(f"Scanning USB devices for device {device_id}")
            self.deployment_progress.emit(device_id, "Scanning USB devices...")
            
            # Get USB device names by sending command to device
            usb_devices = self._get_usb_device_paths(device_id)
            
            if not usb_devices:
                logger.warning(f"No USB devices found for device {device_id}")
                self.deployment_progress.emit(device_id, "No USB devices found")
                self._complete_deployment(device_id, True, "No USB devices found, skipping deployment")
                return
            
            logger.info(f"Found {len(usb_devices)} USB device(s) for device {device_id}: {usb_devices}")
            self.pending_deployments[device_id]['usb_devices_found'] = usb_devices
            
            # Check each USB device for dqa_package
            self._check_dqa_packages(device_id, usb_devices)
            
        except Exception as e:
            logger.error(f"Error scanning USB devices for device {device_id}: {e}")
            self._handle_deployment_failure(device_id, f"USB scan failed: {str(e)}")
    
    def _get_usb_device_paths(self, device_id: str) -> List[str]:
        """
        Get USB device mount points by sending command to device
        
        Args:
            device_id: Target device ID
            
        Returns:
            List of USB device names (e.g., ['sda1', 'sdb1'])
        """
        usb_devices = []
        
        try:
            logger.info(f"Scanning /run/media for USB devices on device {device_id}")
            
            # Send command to list mounted USB devices
            command = "ls /run/media"
            response = self._send_command_sync(device_id, command, timeout=10)
            
            if response:
                # Parse the response to get device names
                # Remove any command echo and extra formatting
                clean_response = response.strip()
                if "cannot access" in clean_response or "No such file or directory" in clean_response:
                    logger.warning(f"No USB devices found for device {device_id}")
                    return []
                
                # Handle responses that might include command echo
                if clean_response.startswith('ls /run/media'):
                    lines = clean_response.split('\n')
                    if len(lines) > 1:
                        clean_response = lines[1].strip()  # Take the second line (actual output)
                
                # Split by whitespace to get individual device names
                device_names = clean_response.split()
                for device_name in device_names:
                    device_name = device_name.strip()
                    if device_name and not device_name.startswith('ls:'):  # Filter out error messages
                        logger.info(f"Found potential USB device: {device_name}")
                        usb_devices.append(device_name)
            else:
                logger.warning("No response from ls /run/media command")
                
        except Exception as e:
            logger.error(f"Error scanning /run/media for USB devices: {e}")
        
        return usb_devices
    
    def _check_dqa_packages(self, device_id: str, usb_devices: List[str]):
        """
        Check each USB device for dqa_package folder by sending test commands
        
        Args:
            device_id: Target device ID
            usb_devices: List of USB device names (e.g., ['sda1', 'sdb1'])
        """
        try:
            packages_found = []
            
            for i, usb_device in enumerate(usb_devices):
                # Add small delay between commands to prevent overwhelming the device
                if i > 0:
                    import time
                    time.sleep(0.5)
                
                # Send test command to check if dqa_package exists
                test_command = f'test -d /run/media/{usb_device}/dqa_package && echo "Pass" || echo "Fail"'
                logger.info(f"Testing dqa_package on device {usb_device}: {test_command}")
                
                response = self._send_command_sync(device_id, test_command, timeout=10)
                
                if response:
                    # Parse response, look for "Pass" in the response
                    response_lines = response.strip().split('\n')
                    last_line = response_lines[-1].strip() if response_lines else ""
                    
                    if last_line == "Pass":
                        logger.info(f"Found dqa_package on USB device: {usb_device}")
                        packages_found.append(usb_device)
                    else:
                        logger.info(f"No dqa_package found on USB device: {usb_device} (response: {last_line})")
                else:
                    logger.warning(f"No response for USB device test: {usb_device}")
            
            if not packages_found:
                logger.info(f"No dqa_package found on any USB devices for device {device_id}")
                self.deployment_progress.emit(device_id, "No dqa_package folder found")
                self._complete_deployment(device_id, True, "No dqa_package folder found, skipping deployment")
                return
            
            logger.info(f"Found {len(packages_found)} dqa_package(s) for device {device_id}: {packages_found}")
            self.deployment_progress.emit(device_id, f"Found {len(packages_found)} dqa_package(s)")
            
            # Deploy packages to device
            self._deploy_packages(device_id, packages_found)
            
        except Exception as e:
            logger.error(f"Error checking dqa_packages for device {device_id}: {e}")
            self._handle_deployment_failure(device_id, f"Check dqa_package failed: {str(e)}")
    
    def _deploy_packages(self, device_id: str, usb_devices: List[str]):
        """
        Deploy dqa_package to device root directory using cp command
        
        Args:
            device_id: Target device ID
            usb_devices: List of USB device names that contain dqa_package
        """
        try:
            deployed_packages = []
            
            for i, usb_device in enumerate(usb_devices):
                # Add delay between deployment operations
                if i > 0:
                    import time
                    time.sleep(1.0)
                
                logger.info(f"Deploying package {i+1}/{len(usb_devices)} from USB device: {usb_device}")
                self.deployment_progress.emit(device_id, f"Deploying dqa_package ({i+1}/{len(usb_devices)})")
                
                # First ensure target directory exists, then copy
                mkdir_command = f"mkdir -p /dqa_package"
                logger.info(f"Ensuring target directory exists: {mkdir_command}")
                mkdir_response = self._send_command_sync(device_id, mkdir_command, timeout=10)
                
                # Send command to copy dqa_package contents to root directory
                cp_command = f"cp -ru /run/media/{usb_device}/dqa_package/* /dqa_package/"
                logger.info(f"Executing copy command: {cp_command}")
                
                response = self._send_command_sync(device_id, cp_command, timeout=30)  # Longer timeout for copy
                
                # Check if copy was successful
                if response is not None:
                    # Parse response for any error messages
                    if "cp:" in response.lower() and "error" in response.lower():
                        logger.warning(f"Copy command had errors for USB device {usb_device}: {response}")
                    else:
                        deployed_packages.append(usb_device)
                        logger.info(f"Successfully deployed package from USB device: {usb_device}")
                else:
                    logger.warning(f"Failed to deploy package from USB device: {usb_device} - no response")
            
            # Update deployment info
            self.pending_deployments[device_id]['packages_deployed'] = deployed_packages
            
            if deployed_packages:
                message = f"Successfully deployed {len(deployed_packages)} dqa_package(s)"
                logger.info(f"Deployment successful for device {device_id}: {message}")
                self._complete_deployment(device_id, True, message)
            else:
                message = "All dqa_package deployment failed"
                logger.error(f"Deployment failed for device {device_id}: {message}")
                self._handle_deployment_failure(device_id, message)
                
        except Exception as e:
            logger.error(f"Error deploying packages for device {device_id}: {e}")
            self._handle_deployment_failure(device_id, f"Deploy dqa_package failed: {str(e)}")
    

    
    def _send_command_sync(self, device_id: str, command: str, timeout: int = 5) -> Optional[str]:
        """
        Send synchronous command to device and wait for response
        
        Args:
            device_id: Target device ID
            command: Command to send
            timeout: Timeout in seconds
            
        Returns:
            Command response or None if failed
        """
        try:
            from PySide6.QtCore import QEventLoop, QTimer
            import time
            
            if not hasattr(self.device_manager_vm, '_serial_worker'):
                logger.error("Serial worker not available")
                return None
            
            # Store the response
            response_container = {'response': None, 'received': False}
            
            def on_response(resp_device_id, resp_command, resp_response):
                if resp_device_id == device_id and resp_command == command:
                    response_container['response'] = resp_response
                    response_container['received'] = True
            
            # Connect to the command result signal temporarily
            self.device_manager_vm._serial_worker.command_result.connect(on_response)
            
            try:
                # Send the command
                self.device_manager_vm._serial_worker.send_command(device_id, command, timeout)
                
                # Wait for response with timeout
                start_time = time.time()
                while not response_container['received'] and (time.time() - start_time) < timeout:
                    # Process events to allow signal handling
                    from PySide6.QtWidgets import QApplication
                    QApplication.processEvents()
                    time.sleep(0.05)  # Small delay to prevent busy waiting
                
                if response_container['received']:
                    return response_container['response']
                else:
                    logger.warning(f"Command timeout for device {device_id}: {command}")
                    return None
                    
            finally:
                # Always disconnect the signal
                self.device_manager_vm._serial_worker.command_result.disconnect(on_response)
                
        except Exception as e:
            logger.error(f"Error sending command to device {device_id}: {e}")
            return None
    
    def _complete_deployment(self, device_id: str, success: bool, message: str):
        """
        Complete deployment process
        
        Args:
            device_id: Target device ID
            success: Whether deployment was successful
            message: Completion message
        """
        if device_id not in self.pending_deployments:
            return
        
        deployment_info = self.pending_deployments[device_id]
        
        logger.info(f"Deployment completed for device {device_id}: {message}")
        
        # Emit completion signal
        self.deployment_completed.emit(device_id, success, message)
        
        # Signal ready for system info service
        self.ready_for_system_info.emit(device_id)
        
        # Call success callback
        if success and deployment_info['on_success']:
            deployment_info['on_success']()
        elif not success and deployment_info['on_failure']:
            deployment_info['on_failure'](message)
        
        # Clean up
        del self.pending_deployments[device_id]
    
    def _handle_deployment_failure(self, device_id: str, reason: str):
        """
        Handle deployment failure
        
        Args:
            device_id: Target device ID
            reason: Failure reason
        """
        logger.error(f"Deployment failed for device {device_id}: {reason}")
        
        # Emit failure signal
        self.deployment_failed.emit(device_id, reason)
        
        # Complete with failure
        self._complete_deployment(device_id, False, reason)
    
    def _handle_deployment_timeout(self, device_id: str):
        """
        Handle deployment timeout
        
        Args:
            device_id: Target device ID
        """
        if device_id in self.pending_deployments:
            logger.warning(f"Deployment timeout for device {device_id}")
            self._handle_deployment_failure(device_id, "Deployment timeout")
    
    def is_deployment_in_progress(self, device_id: str) -> bool:
        """
        Check if deployment is in progress for a device
        
        Args:
            device_id: Target device ID
            
        Returns:
            bool: True if deployment is in progress
        """
        return device_id in self.pending_deployments
    
    def cancel_deployment(self, device_id: str):
        """
        Cancel ongoing deployment for a device
        
        Args:
            device_id: Target device ID
        """
        if device_id in self.pending_deployments:
            logger.info(f"Cancelling deployment for device {device_id}")
            self._handle_deployment_failure(device_id, "Deployment cancelled")
    
    def get_deployment_status(self, device_id: str) -> Optional[Dict]:
        """
        Get deployment status for a device
        
        Args:
            device_id: Target device ID
            
        Returns:
            Dictionary containing deployment status or None if not found
        """
        if device_id in self.pending_deployments:
            deployment_info = self.pending_deployments[device_id]
            return {
                'start_time': deployment_info['start_time'],
                'usb_devices_found': deployment_info['usb_devices_found'],
                'packages_deployed': deployment_info['packages_deployed'],
                'elapsed_time': time.time() - deployment_info['start_time']
            }
        return None 