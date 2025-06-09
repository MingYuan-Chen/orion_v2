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
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        # When creating steps, the process_id is not available yet.
        # It will be set during the execution of the first step.
        # The variable reference in the command string will be replaced at runtime.
        steps = [
            TestStep(
                command=commands[0], 
                validation_func=self._validate_evtest_process_is_running,
                expected_response=expected_responses[0] if len(expected_responses) > 0 else None,
                timeout=5, 
                description="Check evtest process is running",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                # This command contains a placeholder that will be replaced at runtime
                # after the process_id is determined from step 1.
                command=commands[1],
                expected_response=expected_responses[1] if len(expected_responses) > 1 else None,
                timeout=5,
                description="Kill evtest process",
            ),
            TestStep(
                command=commands[2],
                validation_func=self._validate_evtlog,
                expected_response=expected_responses[2] if len(expected_responses) > 2 else None,
                timeout=5,
                description="Check panel resolution",
                criteria=self._get_expected_resolution_criteria(),
            ),
            TestStep(
                command=commands[3],
                expected_response=expected_responses[3] if len(expected_responses) > 3 else None,
                timeout=5,
                description="Remove evtlog",
            ),
            TestStep(
                command=commands[4],
                expected_response=expected_responses[4] if len(expected_responses) > 4 else None,
                timeout=5,
                description="Check panel ID",
                criteria=f"Panel ID is {self.platform_name}",
            )
        ]
        
        return steps
    
    def _get_expected_resolution_criteria(self) -> str:
        """
        Get expected resolution criteria based on platform_name
        
        Returns:
            Criteria string describing expected resolution
        """
        if self.platform_name in ["argo", "gemini_fhd", "hydra_fhd"]:
            return "Panel resolution is 1920x1080"
        elif self.platform_name in ["hydra"]:
            return "Panel resolution is 1366x768"
        elif self.platform_name in ["gemini"]:
            return "Panel resolution is 1280x800"
        else:
            return "Panel resolution is 1920x1080"  # Default
    
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
        Validate evtlog based on platform-specific resolution expectations
        """
        # Define expected resolutions based on platform_name
        if self.platform_name in ["argo", "gemini_fhd", "hydra_fhd"]:
            expected_x = "1919"
            expected_y = "1079"
            resolution_desc = "1920x1080"
        elif self.platform_name in ["hydra"]:
            expected_x = "1365"
            expected_y = "767"
            resolution_desc = "1366x768"
        elif self.platform_name in ["gemini"]:
            expected_x = "1279"
            expected_y = "799"
            resolution_desc = "1280x800"
        else:
            # Default fallback for unknown platforms
            logger.warning(f"Unknown platform: {self.platform_name}, using default FHD resolution")
            expected_x = "1919"
            expected_y = "1079"
            resolution_desc = "1920x1080"
        
        logger.info(f"Platform: {self.platform_name}, Expected resolution: {resolution_desc} (X={expected_x}, Y={expected_y})")
        
        lines = response.split("\n")
        current_axis = None
        x_resolution_correct = False
        y_resolution_correct = False
        
        for line in lines:
            line = line.strip()
            
            # Record the current axis based on the event code
            if "Event code 0 (ABS_X)" in line:
                current_axis = "X"
            elif "Event code 1 (ABS_Y)" in line:
                current_axis = "Y"
            elif line.startswith("Event code") and ("ABS_X" not in line and "ABS_Y" not in line):
                # Reset axis when encountering other event codes (not ABS_X or ABS_Y)
                current_axis = None
            
            # Check Max value for current axis
            if line.startswith("Max") and current_axis:
                if current_axis == "X":
                    if expected_x in line:
                        x_resolution_correct = True
                        logger.debug(f"Found correct ABS_X Max value: {line}")
                    else:
                        return False, f"x-axis resolution detected failed - expected {expected_x}, found: {line}"
                elif current_axis == "Y":
                    if expected_y in line:
                        y_resolution_correct = True
                        logger.debug(f"Found correct ABS_Y Max value: {line}")
                    else:
                        return False, f"y-axis resolution detected failed - expected {expected_y}, found: {line}"
        
        # Check if both resolutions were found and correct
        if not x_resolution_correct:
            return False, f"x-axis resolution not found or incorrect (expected {expected_x})"
        if not y_resolution_correct:
            return False, f"y-axis resolution not found or incorrect (expected {expected_y})"
        
        return True, f"Panel resolution is {resolution_desc}"
