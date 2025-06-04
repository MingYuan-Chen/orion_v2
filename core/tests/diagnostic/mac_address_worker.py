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
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic mac address test steps
        
        Returns:
            diagnostic mac address test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response="5a:31:e7:6b:68:2a",
                # FHD Hydra: 5a:31:e7:6b:68:2a
                # FHD Hydra: sometimes it changes to 1a:33:65:6d:72:09
                # FHD Argo: 7a:30:22:24:b9:fa
                timeout=5, 
                description="Check the Mac address label match the system reading",
                criteria="The mac address is 7a:30:22:24:b9:fa",
                max_retries=1,
                retry_delay=500
            )
        ]

