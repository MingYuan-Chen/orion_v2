"""
Diagnostic cpu name test worker module
Implement diagnostic cpu name test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType


class CpuNameWorker(BaseTestWorker):
    """Diagnostic cpu name worker, implement diagnostic cpu name test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_cpu_name"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic cpu name test steps
        
        Returns:
            diagnostic cpu name test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if expected_responses else None, 
                timeout=5, 
                description="Check CPU Name",
                criteria="CPU name with 'i.MX6'",
                max_retries=1,
                retry_delay=500
            )
        ]

