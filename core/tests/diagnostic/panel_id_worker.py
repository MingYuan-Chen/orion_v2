"""
Panel ID test worker module
Implement panel ID test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType


class PanelIdWorker(BaseTestWorker):
    """Panel ID worker, implement panel ID test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.process_id = None
        self.test_id = "diagnostic_panel_id"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare panel ID test steps
        
        Returns:
            panel ID test steps list
        """
        
        # Get commands from the platform command set
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        # When creating steps, the process_id is not available yet.
        # It will be set during the execution of the first step.
        # The variable reference in the command string will be replaced at runtime.
        steps = [
            # 01: hydra_fhd
            # 00: hydra
            # 10: gemini_fhd
            # 11: gemini
            # 01 + PIC=114: argo
            TestStep(
                command=commands[0],
                expected_response=expected_responses[4] if len(expected_responses) > 4 else None,
                timeout=5,
                description="Check panel ID",
                criteria=f"Panel ID is {self.platform_name}",
            )
        ]
        return steps