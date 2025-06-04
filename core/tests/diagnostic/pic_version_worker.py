"""
Diagnostic pic version test worker module
Implement diagnostic pic version test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class PicVersionWorker(BaseTestWorker):
    """Diagnostic pic version worker, implement diagnostic pic version test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_pic_version"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic pic version test steps
        
        Returns:
            diagnostic pic version test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response="0x6e",           # convert to decimal: 110
                # Hydra: 0x6e = 110
                # Argo: 0x72 = 114
                timeout=5, 
                description="Check PIC Version by i2c",
                criteria="The PIC version is 110",
                max_retries=3,
                retry_delay=500
            ),
            TestStep(
                command=commands[1], 
                expected_response="100",           # convert to decimal: 100
                timeout=5, 
                description="Check HW revision by proc",
                criteria="The HW revision is 100",
                max_retries=1,
                retry_delay=500
            )
        ]

