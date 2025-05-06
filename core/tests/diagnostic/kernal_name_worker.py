"""
Diagnostic kernal name test worker module
Implement diagnostic kernal name test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class KernalNameWorker(BaseTestWorker):
    """Diagnostic kernal name worker, implement diagnostic kernal name test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic kernal name test steps
        
        Returns:
            diagnostic kernal name test steps list
        """
        return [
            TestStep(
                command="uname -a", 
                expected_response="gemini", # get the kernal name
                description="Check kernal name",
                max_retries=1,
                retry_delay=500
            )
        ]

