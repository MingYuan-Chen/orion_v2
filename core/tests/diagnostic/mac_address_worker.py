"""
Diagnostic mac address test worker module
Implement diagnostic mac address test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class MacAddressWorker(BaseTestWorker):
    """Diagnostic mac address worker, implement diagnostic mac address test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic mac address test steps
        
        Returns:
            diagnostic mac address test steps list
        """
        return [
            TestStep(
                command="cat /sys/class/net/eth0/address", 
                expected_response="5a:31:e7:6b:68:2a",       # sometimes it changes to 1a:33:65:6d:72:09
                timeout=5, 
                description="Check mac address",
                criteria="The mac address is 5a:31:e7:6b:68:2a",
                max_retries=1,
                retry_delay=500
            )
        ]

