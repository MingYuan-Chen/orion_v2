"""
Diagnostic mac address test worker module
Implement diagnostic mac address test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType
import re

class MacAddressWorker(BaseTestWorker):
    """Diagnostic mac address worker, implement diagnostic mac address test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_mac_address"
    
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
                validation_func=self._validate_mac_address_pattern,
                timeout=5, 
                description="Check the Mac address label match the system reading",
                criteria=f"The mac address is valid",
                max_retries=1,
                retry_delay=500
            )
        ]
    
    def _validate_mac_address_pattern(self, response: str) -> Tuple[bool, str]:
        """
        Validate the mac address pattern
        
        Args:
            mac_address: The mac address to validate
        """
        if re.match(r'^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$', response) is not None:
            return True, f"The mac address is valid"
        
        return False, f"The mac address is invalid"

