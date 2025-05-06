"""
Diagnostic mac address test worker module
Implement diagnostic mac address test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class MacAddressWorker(BaseTestWorker):
    """Diagnostic mac address worker, implement diagnostic mac address test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic mac address test steps
        
        Returns:
            diagnostic mac address test steps list
        """
        return [
            TestStep(
                command="cat /sys/class/net/eth0/address", 
                expected_response="5a:31:e7:6b:68:2a",
                timeout=5, 
                description="Check mac address",
                max_retries=1,
                retry_delay=500
            )
        ]

