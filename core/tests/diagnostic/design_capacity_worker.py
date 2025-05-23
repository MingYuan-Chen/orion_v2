"""
Diagnostic design capacity test worker module
Implement diagnostic design capacity test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class DesignCapacityWorker(BaseTestWorker):
    """Diagnostic design capacity worker, implement diagnostic design capacity test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic design capacity test steps
        
        Returns:
            diagnostic design capacity test steps list
        """
        return [
            TestStep(
                command="i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x18 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x18 r2", 
                expected_response="0x0c 0xb2",           # concatenate the two bytes as 0x0d16 then convert to decimal: 3350
                timeout=5, 
                description="Check Design Capacity",
                criteria="The design capacity is 3250 mAh",
                max_retries=3,
                retry_delay=500
            )
        ]

