"""
Diagnostic set and get rtc time test worker module
Implement diagnostic set and get rtc time test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class DiagnosticSetGetRtcTimeWorker(BaseTestWorker):
    """Diagnostic set and get rtc time worker, implement diagnostic set and get rtc time test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic set and get rtc time test steps
        
        Returns:
            diagnostic set and get rtc time test steps list
        """
        return [
            TestStep(
                command="date -s '2024-02-28 23:59:59'", 
                expected_response="Wed Feb 28 23:59:59 UTC 2024",
                timeout=5, 
                description="Set Date Time",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command="hwclock -w",
                timeout=5, 
                description="Write RTC Time",
            ),
            TestStep(
                command="hwclock -r",
                expected_response="Thu Feb 29",
                timeout=5, 
                description="Read RTC Time",
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

