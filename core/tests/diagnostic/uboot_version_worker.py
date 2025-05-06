"""
Diagnostic u-boot version test worker module
Implement diagnostic u-boot version test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class UbootVersionWorker(BaseTestWorker):
    """Diagnostic u-boot version worker, implement diagnostic u-boot version test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic u-boot version test steps
        
        Returns:
            diagnostic u-boot version test steps list
        """
        return [
            TestStep(
                command="strings /dev/mtd0 | grep -E 'U-Boot'", 
                expected_response="2016.03",            # Get the version
                timeout=5, 
                description="Check U-Boot Version",
                max_retries=1,
                retry_delay=500
            )
        ]

