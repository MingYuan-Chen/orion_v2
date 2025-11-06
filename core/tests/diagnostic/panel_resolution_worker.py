"""
Panel resolution test worker module
Implement panel resolution test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType


class PanelResolutionWorker(BaseTestWorker):
    """Panel resolution worker, implement panel resolution test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.process_id = None
        self.test_id = "diagnostic_panel_resolution"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare panel resolution test steps
        
        Returns:
            panel resolution test steps list
        """
        
        # Get commands from the platform command set
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        # When creating steps, the process_id is not available yet.
        # It will be set during the execution of the first step.
        # The variable reference in the command string will be replaced at runtime.
        steps = [
            TestStep(
                command=commands[0], 
                validation_func=self._validate_panel_resolution,
                expected_response=expected_responses[0] if len(expected_responses) > 0 else None,
                timeout=5, 
                description="Check panel resolution",
                criteria=self._get_expected_resolution_criteria()
            )
        ]
        
        return steps
    
    def _get_expected_resolution_criteria(self) -> str:
        """
        Get expected resolution criteria based on platform_name
        
        Returns:
            Criteria string describing expected resolution
        """
        if self.platform_name in ["argo", "gemini_fhd", "hydra_fhd", "athena"]:
            return "Panel resolution is 1920x1080"
        elif self.platform_name in ["hydra"]:
            return "Panel resolution is 1366x768"
        elif self.platform_name in ["gemini", "odin"]:
            return "Panel resolution is 1280x800"
        else:
            return "Panel resolution is 1920x1080"  # Default
    
    def _validate_panel_resolution(self, response: str) -> Tuple[bool, str]:
        """
        Validate panel resolution
        
        Args:
            response: Command execution response
            
        Returns:
            (success, message): Validation result
        """
        # Define expected resolutions based on platform_name
        if self.platform_name in ["argo", "gemini_fhd", "hydra_fhd", "athena"]:
            expected_x = "1920"
            expected_y = "1080"
            resolution_desc = "1920x1080"
        elif self.platform_name in ["hydra"]:
            expected_x = "1366"
            expected_y = "768"
            resolution_desc = "1366x768"
        elif self.platform_name in ["gemini", "odin"]:
            expected_x = "1280"
            expected_y = "800"
            resolution_desc = "1280x800"
        else:
            # Default fallback for unknown platforms
            logger.warning(f"Unknown platform: {self.platform_name}, using default FHD resolution")
            expected_x = "1920"
            expected_y = "1080"
            resolution_desc = "1920x1080"

        try:
            # Split response into lines
            lines = response.split(" ")
            if lines[0] == "geometry":
                if lines[1] == expected_x and lines[2] == expected_y:
                    return True, f"Panel resolution is {resolution_desc}"
                else:
                    return False, f"Panel resolution is {lines[1]}x{lines[2]}"
            else:
                return False, "Failed to find panel resolution in the response"
            
        except Exception as e:
            logger.error(f"Error in _validate_panel_resolution: {str(e)}", exc_info=True)
            return False, f"Error validating panel resolution: {str(e)}"
