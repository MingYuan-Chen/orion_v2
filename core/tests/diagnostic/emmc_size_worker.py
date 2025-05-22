"""
Diagnostic emmc size test worker module
Implement diagnostic emmc size test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class EmmcSizeWorker(BaseTestWorker):
    """Diagnostic emmc size worker, implement diagnostic emmc size test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic emmc size test steps
        
        Returns:
            diagnostic emmc size test steps list
        """
        return [
            TestStep(
                command="cat /sys/block/mmcblk2/size", 
                expected_response="244629504", # get sector size * 512 = expected bytes: 125250306048 = 116.65GB
                timeout=5, 
                description="Check emmc size",
                criteria="The emmc size is 125250306048 bytes(116.65GB)",
                max_retries=1,
                retry_delay=500
            )
        ]

