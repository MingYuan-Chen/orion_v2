"""
Power button test worker module
Implement power button test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class PowerButtonWorker(BaseTestWorker):
    """Power button worker, implement power button test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.process_id = None
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare power button test steps
        
        Returns:
            power button test steps list
        """
        return [
            TestStep(
                command="evtest /dev/input/event2 > evtlog &", 
                validation_func=self._validate_evtest_process_is_running,
                timeout=5, 
                description="Check evtest process is running",
                criteria=f"process id exists",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command="cat evtlog",
                validation_func=self._validate_evtlog,
                pre_condition="Please press the power button then release it",
                timeout=5,
                description="Check evtlog",
                criteria="Power button event triggered",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=f"kill {self.process_id}",
                timeout=5,
                description="Kill evtest process",
            ),
            TestStep(
                command="rm evtlog",
                timeout=5,
                description="Remove evtlog",
            )
        ]
    
    def _validate_evtest_process_is_running(self, response: str) -> Tuple[bool, str]:
        """
        Validate evtest process is running
        """
        value = response.split("\n")[1].split(" ")[1]
        if value:
            self.process_id = value
            return True, "evtest process is running"
        else:
            return False, "evtest process is not running"
    
    def _validate_evtlog(self, response: str) -> Tuple[bool, str]:
        """
        Validate evtlog
        """
        if "code 116 (KEY_POWER), value 1" in response and "code 116 (KEY_POWER), value 0" in response:
            return True, "Power button event triggered"
        else:
            return False, "Power button event triggered failed"
