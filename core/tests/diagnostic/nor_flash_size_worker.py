"""
Diagnostic nor flash size test worker module
Implement diagnostic nor flash size test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class NorFlashSizeWorker(BaseTestWorker):
    """Diagnostic nor flash size worker, implement diagnostic nor flash size test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic nor flash size test steps
        
        Returns:
            diagnostic nor flash size test steps list
        """
        return [
            TestStep(
                command="cat /proc/mtd | grep 'mtd0'", 
                expected_response="04000000", # 64MB
                timeout=5, 
                description="Check NOR flash size",
                max_retries=1,
                retry_delay=500
            )
        ]

