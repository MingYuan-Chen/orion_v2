"""
Diagnostic wifi and bluetooth test worker module
Implement diagnostic wifi and bluetooth test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class WifiBtWorker(BaseTestWorker):
    """Diagnostic wifi and bluetooth worker, implement diagnostic wifi and bluetooth test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic wifi and bluetooth test steps
        
        Returns:
            diagnostic wifi and bluetooth test steps list
        """
        return [
            TestStep(
                command="lsusb", 
                expected_response="1286:2046",            # Get the ID
                timeout=5, 
                description="Check bluetooth device ID",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command="lspci", 
                expected_response="Marvell",            # Get the wifi device name
                timeout=5, 
                description="Check wifi device name",
                max_retries=1,
                retry_delay=500
            )
        ]

