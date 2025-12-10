"""
Diagnostic ethernet test worker module
Implement diagnostic ethernet test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType


class EthernetWorker(BaseTestWorker):
    """Diagnostic ethernet worker, implement diagnostic ethernet test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_ethernet"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic ethernet test steps
        
        Returns:
            diagnostic ethernet test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if expected_responses else None, 
                timeout=5, 
                description="Ensure wifi not connected",
            ),
            TestStep(
                command=commands[1], 
                expected_response=expected_responses[1] if expected_responses else None, 
                description="Test ethernet connection by downloading google homepage",
                criteria="Can download google homepage normally", 
            ),
            TestStep(
                command=commands[2], 
                expected_response=expected_responses[2] if expected_responses else None,
                description="Ensure ethernet connected",
                
            )
        ]