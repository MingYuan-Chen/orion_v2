"""
Diagnostic mac address test worker module
Implement diagnostic mac address test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class MacAddressWorker(BaseTestWorker):
    """Diagnostic mac address worker, implement diagnostic mac address test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_mac_address"
        self.expected_mac_address_mapping = {
            "hydra_fhd": "5a:31:e7:6b:68:2a",
            "hydra": "8e:65:70:f4:f2:ba",
            "gemini": "8e:65:70:f4:f2:ba",
            "argo": "3a:32:a0:22:a3:d9"
        }
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic mac address test steps
        
        Returns:
            diagnostic mac address test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if expected_responses else None,
                # FHD Hydra: 5a:31:e7:6b:68:2a
                # Hydra: 8e:65:70:f4:f2:ba
                # Gemini: 8e:65:70:f4:f2:ba
                # Argo: 3a:32:a0:22:a3:d9
                timeout=5, 
                description="Check the Mac address label match the system reading",
                criteria=f"The mac address is {self.expected_mac_address_mapping[self.platform_name]}",
                max_retries=1,
                retry_delay=500
            )
        ]

