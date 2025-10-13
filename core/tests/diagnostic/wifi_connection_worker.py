"""
Diagnostic wifi connection test worker module
Implement diagnostic wifi connection test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType


class WifiConnectionWorker(BaseTestWorker):
    """Diagnostic wifi connection worker, implement diagnostic wifi connection test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_wifi_connection"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic wifi connection test steps
        
        Returns:
            diagnostic wifi connection test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if expected_responses else None, 
                timeout=5, 
                description="scan available wifi networks",
            ),
            TestStep(
                command=commands[1], 
                expected_response=expected_responses[1] if expected_responses else None, 
                timeout=5, 
                description="connect to wifi network",
            ),
            TestStep(
                command=commands[2], 
                expected_response=expected_responses[2] if expected_responses else None, 
                timeout=5, 
                description="set wifi as default network",
            ),
            TestStep(
                command=commands[3], 
                expected_response=expected_responses[3] if expected_responses else None, 
                timeout=5, 
                description="apply default network setting",
            ),
            TestStep(
                command=commands[4], 
                expected_response=expected_responses[4] if expected_responses else None, 
                timeout=5, 
                description="Test wifi connection by downloading google homepage",
                criteria="Can download google homepage normally",
            ),
            TestStep(
                command=commands[5], 
                expected_response=expected_responses[5] if expected_responses else None, 
                timeout=5, 
                description="reset ethernet as default network",
            ),
            TestStep(
                command=commands[6], 
                expected_response=expected_responses[6] if expected_responses else None, 
                timeout=5, 
                description="apply default network setting",
            )
        ]