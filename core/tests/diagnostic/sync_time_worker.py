"""
Diagnostic sync time test worker module
Implement diagnostic sync time test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class SyncTimeWorker(BaseTestWorker):
    """Diagnostic sync time worker, implement diagnostic sync time test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic sync time test steps
        
        Returns:
            diagnostic sync time test steps list
        """
        return [
            TestStep(
                command="sudo ntpdate -u time.stdtime.gov.tw", 
                validation_func=self._validate_sync_time,
                timeout=5, 
                description="Sync time with time.stdtime.gov.tw",
                criteria="Can sync time with time.stdtime.gov.tw",
                max_retries=1,
                retry_delay=500
            )
        ]
    
    def _validate_sync_time(self, response: str) -> Tuple[bool, str]:
        """
        Validate sync time
        """
        if "error" in response.lower():
            return False, "Failed to sync time"
        
        synced_time = response.split(" ntpdate")[0].split("\n")[1]
        return True, f"Synced time: {synced_time}"

