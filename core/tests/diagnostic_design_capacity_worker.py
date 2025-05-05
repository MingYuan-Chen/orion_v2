"""
Diagnostic design capacity test worker module
Implement diagnostic design capacity test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class DiagnosticDesignCapacityWorker(BaseTestWorker):
    """Diagnostic design capacity worker, implement diagnostic design capacity test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic design capacity test steps
        
        Returns:
            diagnostic design capacity test steps list
        """
        return [
            TestStep(
                command="i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x18 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x18 r2", 
                expected_response="0x0d 0x16",           # concatenate the two bytes as 0x0d16 then convert to decimal: 3350
                timeout=5, 
                description="Check Design Capacity",
                max_retries=1,
                retry_delay=500
            )
        ]

