"""
Diagnostic memory size test worker module
Implement diagnostic memory size test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class MemorySizeWorker(BaseTestWorker):
    """Diagnostic memory size worker, implement diagnostic memory size test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic memory size test steps
        
        Returns:
            diagnostic memory size test steps list
        """
        return [
            TestStep(
                command="grep MemTotal /proc/meminfo", 
                expected_response="3886520", 
                timeout=5, 
                description="Check Memory Size by proc/meminfo",
                criteria="The memory size is 3886520 (3.7GB)",
                max_retries=1,
                retry_delay=500
            )
        ]

