"""
Diagnostic cpu name test worker module
Implement diagnostic cpu name test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class CpuNameWorker(BaseTestWorker):
    """Diagnostic cpu name worker, implement diagnostic cpu name test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic cpu name test steps
        
        Returns:
            diagnostic cpu name test steps list
        """
        return [
            TestStep(
                command="grep \"Hardware\" /proc/cpuinfo | cut -d':' -f2- | sed 's/^[ \t]*//'", 
                expected_response="i.MX6", 
                timeout=5, 
                description="Check CPU Name",
                max_retries=1,
                retry_delay=500
            )
        ]

