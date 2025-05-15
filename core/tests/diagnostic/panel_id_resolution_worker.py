"""
Panel ID resolution test worker module
Implement panel ID resolution test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType


class PanelIdResolutionWorker(BaseTestWorker):
    """Panel ID resolution worker, implement panel ID resolution test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.process_id = None
        self.test_id = "diagnostic_panel_id_resolution"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare panel ID resolution test steps
        
        Returns:
            panel ID resolution test steps list
        """
        logger.info("Preparing panel ID resolution test steps")
        
        # Get commands from the platform command set
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        # When creating steps, the process_id is not available yet.
        # It will be set during the execution of the first step.
        # The variable reference in the command string will be replaced at runtime.
        steps = [
            TestStep(
                command=commands[0], 
                validation_func=self._validate_evtest_process_is_running,
                timeout=5, 
                description="Check evtest process is running",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                # This command contains a placeholder that will be replaced at runtime
                # after the process_id is determined from step 1.
                command=commands[1],
                timeout=5,
                description="Kill evtest process",
            ),
            TestStep(
                command=commands[2],
                validation_func=self._validate_evtlog,
                timeout=5,
                description="Check evtlog",
            ),
            TestStep(
                command=commands[3],
                timeout=5,
                description="Remove evtlog",
            )
        ]
        
        return steps
    
    def _validate_evtest_process_is_running(self, response: str) -> Tuple[bool, str]:
        """
        Validate evtest process is running and extract the process ID
        
        Args:
            response: Command execution response
            
        Returns:
            (success, message): Validation result
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
        lines = response.split("\n")
        current_axis = None
        
        for i, line in enumerate(lines):
            if "Input device ID:" in line:
                parts = line.split(":")
                if len(parts) != 2:
                    return False, "Invalid input device ID format"
                    
                # get id parts
                id_parts = parts[1].strip().split()
                
                # use dict to store expected values
                expected_values = {
                    "bus": "0x3",
                    "vendor": "0x3eb",
                    "product": "0x214e",
                    "version": "0x111"
                }
                
                # validate each value
                for i, (key, expected) in enumerate(expected_values.items()):
                    if i * 2 + 1 >= len(id_parts) or id_parts[i * 2 + 1] != expected:
                        return False, f"{key} ID detected failed"
            
            # Record the current axis
            if "ABS_X" in line:
                current_axis = "X"
            elif "ABS_Y" in line:
                current_axis = "Y"
            
            # validate resolution
            if "Max" in line and current_axis:
                if current_axis == "X" and "1919" not in line:
                    return False, "x-axis resolution detected failed"
                elif current_axis == "Y" and "1079" not in line:
                    return False, "y-axis resolution detected failed"
        
        return True, "All validations passed"
