"""
Diagnostic wifi and bluetooth test worker module
Implement diagnostic wifi and bluetooth test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class WifiBtWorker(BaseTestWorker):
    """Diagnostic wifi and bluetooth worker, implement diagnostic wifi and bluetooth test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_wifi_bt"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic wifi and bluetooth test steps
        
        Returns:
            diagnostic wifi and bluetooth test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if len(expected_responses) > 0 else None,            # Get the ID
                timeout=5, 
                description="Check bluetooth device ID",
                criteria="The bluetooth device ID can be read",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[1], 
                expected_response=expected_responses[1] if len(expected_responses) > 1 else None,            # Get the wifi device name
                timeout=5, 
                description="Check wifi device name",
                criteria="The wifi device name can be read",
                max_retries=1,
                retry_delay=500
            )
        ]

