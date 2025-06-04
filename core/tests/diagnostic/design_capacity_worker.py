"""
Diagnostic design capacity test worker module
Implement diagnostic design capacity test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class DesignCapacityWorker(BaseTestWorker):
    """Diagnostic design capacity worker, implement diagnostic design capacity test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_design_capacity"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic design capacity test steps
        
        Returns:
            diagnostic design capacity test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response="0x0d 0x16",
                # Hydra: 0x0d 0x16 = 3350
                # Argo: 0x0c 0xb2 = 3250
                timeout=5, 
                description="Check Design Capacity",
                criteria="The design capacity is 3250 mAh",
                max_retries=3,
                retry_delay=500
            )
        ]

