"""
Diagnostic pic version test worker module
Implement diagnostic pic version test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class PicVersionWorker(BaseTestWorker):
    """Diagnostic pic version worker, implement diagnostic pic version test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic pic version test steps
        
        Returns:
            diagnostic pic version test steps list
        """
        return [
            TestStep(
                command="i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2", 
                expected_response="0x64",           # convert to decimal: 100
                timeout=5, 
                description="Check PIC Version",
                max_retries=1,
                retry_delay=500
            )
        ]

