"""
Diagnostic set and get rtc time test worker module
Implement diagnostic set and get rtc time test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class SetGetRtcTimeWorker(BaseTestWorker):
    """Diagnostic set and get rtc time worker, implement diagnostic set and get rtc time test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_set_get_rtc_time"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic set and get rtc time test steps
        
        Returns:
            diagnostic set and get rtc time test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if len(expected_responses) > 0 else None,
                timeout=5, 
                description="Set Date Time",
                criteria="Can set date time to 2024-02-28 23:59:59",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[1],
                expected_response=expected_responses[1] if len(expected_responses) > 1 else None,
                timeout=5, 
                description="Write RTC Time",
            ),
            TestStep(
                command=commands[2],
                expected_response=expected_responses[2] if len(expected_responses) > 2 else None,
                timeout=5, 
                description="Read RTC Time and verify leap year is handled",
                criteria="Can read RTC time Thu Feb 29",
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

