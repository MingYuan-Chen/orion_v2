"""
Diagnostic emmc size test worker module
Implement diagnostic emmc size test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class EmmcSizeWorker(BaseTestWorker):
    """Diagnostic emmc size worker, implement diagnostic emmc size test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_emmc_size"
        self.expected_emmc_size_mapping = {
            "hydra_fhd": [125250306048, 116.64],
            "hydra": [125069950976, 116.48],
            "gemini": [125069950976, 116.48],
            "argo": [125069950976, 116.48]
        }
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic emmc size test steps
        
        Returns:
            diagnostic emmc size test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if expected_responses else None, # get sector size * 512 = expected bytes: 125250306048 = 116.65GB
                timeout=5, 
                description="Check emmc size",
                criteria=f"The emmc size is {self.expected_emmc_size_mapping[self.platform_name][0]} bytes({self.expected_emmc_size_mapping[self.platform_name][1]}GB)",
                # fhd hydra: 244629504 = 125250306048 bytes= 116.64GB
                # hydra:     244277248 = 125069950976 bytes= 116.48GB
                # gemini:    244277248 = 125069950976 bytes= 116.48GB
                max_retries=1,
                retry_delay=500
            )
        ]

