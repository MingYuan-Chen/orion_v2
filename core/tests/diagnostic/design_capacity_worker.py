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
        self.expected_design_capacity_mapping = {
            "hydra_fhd": 3350,
            "hydra": 3350,
            "gemini_fhd": 3350,  # Same as gemini
            "gemini": 3350,
            "argo": 3250,
            "athena": 3250,
            "odin": '6400 or 6800',
        }

    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic design capacity test steps
        
        Returns:
            diagnostic design capacity test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        self.expected_response = expected_responses[0]
        
        # Get expected design capacity for the platform, with fallback
        expected_design_capacity = self.expected_design_capacity_mapping.get(self.platform_name, 3350)
        if self.platform_name not in self.expected_design_capacity_mapping:
            logger.warning(f"Unknown platform '{self.platform_name}' for design capacity test, using default value 3350")
        
        return [
            TestStep(
                command=commands[0], 
                validation_func=self._validate_design_capacity,
                # FHD Hydra: 0x0d 0x16 = 3350
                # Hydra: 0x0d 0x16 = 3350
                # Argo: 0x0c 0xb2 = 3250
                # Gemini: 0x0d 0x16 = 3350
                timeout=5, 
                description="Check Design Capacity",
                criteria=f"The design capacity is {expected_design_capacity} mAh",
                max_retries=3,
                retry_delay=500
            )
        ]
    def _validate_design_capacity(self, response: str) -> Tuple[bool, str]:
        lines = response.strip().splitlines()
        design_capacity = lines[-1].strip()
        self.design_capacity = design_capacity
        if self.platform_name.lower() == "odin":
            if design_capacity in ["0x1a 0x90", "0x19 0x00"]:
                return True, f"Design capacity {design_capacity} is valid for odin"
            else:
                return False, f"Design capacity {design_capacity} is invalid for odin"
        else:
            if self.expected_response in response:
                return True, f"No specific validation for platform {self.platform_name}, received {design_capacity}"
            else:
                return False, f"Memory size {design_capacity} is invalid"
