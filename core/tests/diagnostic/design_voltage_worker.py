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
        self.design_capacity = None
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
        if self.platform_name == "odin":
            TestStep(
                command=commands[0],           # concatenate the two bytes as 0x1c20 then convert to decimal: 7200
                validation_func=self._save_design_capacity,
                timeout=5, 
                description="Check battery design capacity by i2c"
            ),
            TestStep(
                command=commands[1], 
                validation_func=self._validate_design_voltage,
                expected_response=expected_responses[0] if expected_responses else None,           # concatenate the two bytes as 0x1c20 then convert to decimal: 7200
                timeout=5, 
                description="Check Design Voltage by i2c",
                criteria=f"The design voltage is {self.expected_design_voltage_mapping[self.platform_name]} mV"
            )
        else:
            return [
                TestStep(
                    command=commands[0], 
                    expected_response=expected_responses[0] if expected_responses else None,           # concatenate the two bytes as 0x1c20 then convert to decimal: 7200
                    timeout=5, 
                    description="Check Design Voltage by i2c",
                    criteria=f"The design voltage is {self.expected_design_voltage_mapping[self.platform_name]} mV"
                )
            ]
    def _save_design_capacity(self, response: str) -> Tuple[bool, str]:
        lines = response.strip().splitlines()
        if len(lines) < 2:
            return False, "Invalid response"
        self.design_capacity = lines[-1].strip()
        return True, f"Design capacity saved: {self.design_capacity}"
    
    def _validate_design_voltage(self, response: str) -> Tuple[bool, str]:
        if not self.design_capacity:
            return False, "Design capacity not available, cannot validate design voltage"

        voltage_map = {
            "odin": {
                "0x19 0x00": "0x2a 0x30",
                "0x1a 0x90": "0x2a 0xc6",
            },
            # 其他 platform 可補
        }

        expected_voltage = voltage_map.get(self.platform_name.lower(), {}).get(self.design_capacity)
        if not expected_voltage:
            return False, f"No voltage mapping for platform {self.platform_name} and capacity {self.design_capacity}"

        if expected_voltage in response:
            return True, f"Design voltage {expected_voltage} matches for capacity {self.design_capacity}"
        else:
            return False, f"Design voltage mismatch: expected {expected_voltage}, got {response}"
     

        