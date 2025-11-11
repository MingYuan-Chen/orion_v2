"""
Diagnostic memory size test worker module
Implement diagnostic memory size test for device
"""
import re
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
        self.expected_response = expected_responses[0]

        return [
            TestStep(
                command=commands[0], 
                validation_func=self._validate_memory_size,
                timeout=5, 
                description="Check Memory Size by proc/meminfo",
                criteria="The memory size can be found in the response",
                max_retries=1,
                retry_delay=500
            )
        ]

    def _validate_memory_size(self, response: str) -> Tuple[bool, str]:
        match = re.search(r'\d+', response)
        if not match:
            return False, f"No numeric memory size found in response: {response}"
        mem_size = int(match.group())

        if self.platform_name.lower() == "odin":
            if mem_size in [3074220, 3074232]:
                return True, f"Memory size {mem_size} is valid for odin"
            else:
                return False, f"Memory size {mem_size} is invalid for odin"
        if self.platform_name.lower() == "argo":
            if mem_size in [3074232, 3886520]:
                return True, f"Memory size {mem_size} is valid for argo"
            else:
                return False, f"Memory size {mem_size} is invalid for argo"
        else:
            if self.expected_response in response:
                return True, f"No specific validation for platform {self.platform_name}, received {mem_size}"
            else:
                return False, f"Memory size {mem_size} is invalid"