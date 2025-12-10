"""
Diagnostic nor flash size test worker module
Implement diagnostic nor flash size test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class NorFlashSizeWorker(BaseTestWorker):
    """Diagnostic nor flash size worker, implement diagnostic nor flash size test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_nor_flash_size"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic nor flash size test steps
        
        Returns:
            diagnostic nor flash size test steps list
        """ 
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if expected_responses else None, # 64MB
                timeout=5, 
                description="Check NOR flash size",
                criteria="The NOR flash size is 64MB",
                max_retries=1,
                retry_delay=500
            )
        ]

