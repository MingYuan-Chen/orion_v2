"""
Diagnostic emmc size test worker module
Implement diagnostic emmc size test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class DiagnosticEmmcSizeWorker(BaseTestWorker):
    """Diagnostic emmc size worker, implement diagnostic emmc size test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic emmc size test steps
        
        Returns:
            diagnostic emmc size test steps list
        """
        return [
            TestStep(
                command="cat /sys/block/mmcblk2/size", 
                expected_response="244629504", # get sector size * 512 = expected bytes: 125250306048
                timeout=5, 
                description="Check emmc size",
                max_retries=1,
                retry_delay=500
            )
        ]

