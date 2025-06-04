"""
Diagnostic cpu processor test worker module
Implement diagnostic cpu processor test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class CpuProcessorWorker(BaseTestWorker):
    """Diagnostic cpu processor worker, implement diagnostic cpu processor test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_cpu_processor"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic cpu processor test steps
        
        Returns:
            diagnostic cpu processor test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response="4", 
                timeout=5, 
                description="Check CPU Processor",
                criteria="4 processors",
                max_retries=1,
                retry_delay=500
            )
        ]

