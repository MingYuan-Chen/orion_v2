"""
Diagnostic design voltage test worker module
Implement diagnostic design voltage test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class DesignVoltageWorker(BaseTestWorker):
    """Diagnostic design voltage worker, implement diagnostic design voltage test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic design voltage test steps
        
        Returns:
            diagnostic design voltage test steps list
        """
        return [
            TestStep(
                command="i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x19 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x19 r2", 
                expected_response="0x1c 0x20",           # concatenate the two bytes as 0x1c20 then convert to decimal: 7200
                timeout=5, 
                description="Check Design Voltage",
                max_retries=3,
                retry_delay=500
            )
        ]

