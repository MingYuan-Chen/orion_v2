"""
Diagnostic HW version test worker module
Implement diagnostic HW version test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class HWVersionWorker(BaseTestWorker):
    """Diagnostic HW version worker, implement diagnostic HW version test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_HW_version"
        # self.expected_HW_version_mapping = {
        #     "hydra": 100,
        #     "hydra_fhd": 100,
        #     "gemini": 100,
        #     "gemini_fhd": 100,
        #     "argo": 100,
        #     "athena": "Athena-030",
        #     "odin": "PSC Odin",
        # }
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic HW version test steps
        
        Returns:
            diagnostic HW version test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if expected_responses else None, 
                timeout=5, 
                description="Check HW version by proc",
                criteria="The HW version can be read",
                max_retries=1,
                retry_delay=500
            )
        ]
