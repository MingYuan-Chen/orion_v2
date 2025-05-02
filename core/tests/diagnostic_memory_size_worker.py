"""
Diagnostic memory size test worker module
Implement diagnostic memory size test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class DiagnosticMemorySizeWorker(BaseTestWorker):
    """Diagnostic memory size worker, implement diagnostic memory size test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
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
                description="Check Memory Size",
                max_retries=1,           # Maximum retries 1 time
                retry_delay=500          # 0.5 seconds later retry
            )
        ]

