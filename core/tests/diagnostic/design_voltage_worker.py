"""
Diagnostic design voltage test worker module
Implement diagnostic design voltage test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class DesignVoltageWorker(BaseTestWorker):
    """Diagnostic design voltage worker, implement diagnostic design voltage test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_design_voltage"
        self.expected_design_voltage_mapping = {
            "hydra_fhd": 7200,
            "hydra": 7200,
            "gemini_fhd": 7200,  # Same as gemini
            "gemini": 7200,
            "argo": 7200,
            "athena": 10800,
            "odin" : 10800
        }
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic design voltage test steps
        
        Returns:
            diagnostic design voltage test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if expected_responses else None,           # concatenate the two bytes as 0x1c20 then convert to decimal: 7200
                timeout=5, 
                description="Check Design Voltage by i2c",
                criteria=f"The design voltage is {self.expected_design_voltage_mapping[self.platform_name]} mV"
            )
        ]

