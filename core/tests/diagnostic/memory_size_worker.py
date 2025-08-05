"""
Diagnostic memory size test worker module
Implement diagnostic memory size test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class MemorySizeWorker(BaseTestWorker):
    """Diagnostic memory size worker, implement diagnostic memory size test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_memory_size"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic memory size test steps
        
        Returns:
            diagnostic memory size test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if expected_responses else None, 
                timeout=5, 
                description="Check Memory Size by proc/meminfo",
                criteria="The memory size can be found in the response",
                max_retries=1,
                retry_delay=500
            )
        ]

