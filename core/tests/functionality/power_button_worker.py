"""
Power button test worker module
Implement power button test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class PowerButtonWorker(BaseTestWorker):
    """Power button worker, implement power button test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_power_button"
        self.process_id = None
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare power button test steps
        
        Returns:
            power button test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
            TestStep(
                command=commands[0], 
                validation_func=self._validate_evtest_process_is_running,
                timeout=5, 
                description="Check evtest process is running",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[1],
                validation_func=self._validate_evtlog,
                pre_condition="Please press the power button then release it",
                timeout=5,
                description="Check evtlog",
                criteria="Power button event triggered",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[2],
                timeout=5,
                description="Kill evtest process",
            ),
            TestStep(
                command=commands[3],
                timeout=5,
                description="Remove evtlog",
            )
        ]
    
    def _validate_evtest_process_is_running(self, response: str) -> Tuple[bool, str]:
        """
        Validate evtest process is running
        """
        try:
            # Split response into lines
            lines = response.split("\n")
            
            # Look for process ID in the format of "[X] YYYY" where YYYY is the PID
            for line in lines:
                line = line.strip()
                
                # In most shells, background processes are shown as [job_number] process_id
                if "[" in line and "]" in line:
                    self.process_id = line.split()[1]
                    logger.info(f"Found process ID: {self.process_id}")
                    return True, f"evtest process is running"
            
            if self.process_id is None:
                logger.error("Failed to find process ID in the response")
                return False, "Failed to extract process ID from evtest command output"
            
        except Exception as e:
            logger.error(f"Error in _validate_evtest_process_is_running: {str(e)}", exc_info=True)
            return False, f"Error extracting process ID: {str(e)}"
    
    def _validate_evtlog(self, response: str) -> Tuple[bool, str]:
        """
        Validate evtlog
        """
        if "code 116 (KEY_POWER), value 1" in response and "code 116 (KEY_POWER), value 0" in response:
            return True, "Power button event triggered"
        else:
            return False, "Power button event triggered failed"
