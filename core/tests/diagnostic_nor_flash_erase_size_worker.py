"""
Diagnostic nor flash erase size test worker module
Implement diagnostic nor flash erase size test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class DiagnosticNorFlashEraseSizeWorker(BaseTestWorker):
    """Diagnostic nor flash erase size worker, implement diagnostic nor flash erase size test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic nor flash erase size test steps
        
        Returns:
            diagnostic nor flash erase size test steps list
        """
        return [
            TestStep(
                command="cat /proc/mtd | grep 'mtd0'", 
                expected_response="00020000", # 128KB
                timeout=5, 
                description="Check NOR flash erase size",
                max_retries=1,           # Maximum retries 1 time
                retry_delay=500          # 0.5 seconds later retry
            )
        ]

