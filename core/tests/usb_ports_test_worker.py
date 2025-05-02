"""
USB ports test worker module
Implement USB port function test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class UsbPortsTestWorker(BaseTestWorker):
    """USB ports test worker, implement USB port function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare USB test steps
        
        Returns:
            USB test steps list
        """
        return [
            TestStep(
                command="dd if=/dev/zero of=/run/media/sda1/usb_throughput bs=1M count=200 status=progress", 
                expected_response="copied", 
                timeout=5, 
                description="Write to usb_throughput",
                max_retries=1,           # Maximum retries 1 time
                retry_delay=500          # 0.5 seconds later retry
            ),
            TestStep(
                command="dd if=/run/media/sda1/usb_throughput of=/dev/null bs=1M", 
                expected_response="copied", 
                timeout=10, 
                description="Read from usb_throughput",
                max_retries=3,           # Read operation may need multiple attempts
                retry_delay=1000         # 1 second later retry
            ),
            TestStep(
                command="sudo umount /run/media/sda1", 
                validation_func=self._validate_usb_unmount, 
                timeout=10, 
                description="Unmount sda1",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            ),
            TestStep(
                command="sudo mount /dev/sda1 /run/media/sda1", 
                expected_response="sda1", 
                timeout=10, 
                description="Mount sda1",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            ),
            TestStep(
                command="mount | grep sda1", 
                validation_func=self._validate_usb_mount,
                timeout=10, 
                description="Validate sda1 mounted",
                max_retries=2,           # Speed test may be affected by transient factors
                retry_delay=2000         # 2 seconds later retry
            )
        ]
    
    def _validate_usb_mount(self, response: str) -> Tuple[bool, str]:
        """
        Validate USB mount test result
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            # Check if target device is mounted
            if "/dev/sda1" not in response:
                return False, "Target device not mounted"
                
            if "/run/media/sda1" not in response:
                return False, "Unexpected mount point"
            
            if "vfat" not in response:
                return False, "Unexpected file system"
                
            return True, "Device:sda1 mount at /run/media/sda1 with vfat file system"
            
        except Exception as e:
            logger.error(f"Mount validation error: {str(e)}", exc_info=True)
            return False, f"Mount validation error: {str(e)}" 
        
    def _validate_usb_unmount(self, response: str) -> Tuple[bool, str]:
        """
        Validate USB unmount test result
        """
        try:
            if response == "\n":
                return True, "Device unmounted successfully"
            elif "/run/media/sda1: not mounted" in response:
                return True, "Device unmounted successfully"
            else:
                return False, "Device not unmounted"
        except Exception as e:
            logger.error(f"Unmount validation error: {str(e)}", exc_info=True)
            return False, f"Unmount validation error: {str(e)}"