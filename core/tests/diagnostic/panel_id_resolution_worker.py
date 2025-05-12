"""
Panel ID resolution test worker module
Implement panel ID resolution test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class PanelIdResolutionWorker(BaseTestWorker):
    """Panel ID resolution worker, implement panel ID resolution test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
        self.process_id = None
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare panel ID resolution test steps
        
        Returns:
            panel ID resolution test steps list
        """
        return [
            TestStep(
                command="evtest /dev/input/event1 > evtlog &", 
                validation_func=self._validate_evtest_process_is_running,
                timeout=5, 
                description="Check evtest process is running",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=f"kill {self.process_id}",
                timeout=5,
                description="Kill evtest process",
            ),
            TestStep(
                command="cat evtlog",
                validation_func=self._validate_evtlog,
                timeout=5,
                description="Check evtlog",
            ),
            TestStep(
                command="rm evtlog",
                timeout=5,
                description="Remove evtlog",
            )
        ]
    
    def _validate_evtest_process_is_running(self, response: str) -> Tuple[bool, str]:
        """
        Validate evtest process is running
        """
        value = response.split("\n")[1].split(" ")[1]
        if value:
            self.process_id = value
            return True, "evtest process is running"
        else:
            return False, "evtest process is not running"
    
    def _validate_evtlog(self, response: str) -> Tuple[bool, str]:
        """
        Validate evtlog
        """
        lines = response.split("\n")
        current_axis = None
        
        for i, line in enumerate(lines):
            if "Input device ID:" in line:
                parts = line.split(":")
                if len(parts) != 2:
                    return False, "Invalid input device ID format"
                    
                # get id parts
                id_parts = parts[1].strip().split()
                
                # use dict to store expected values
                expected_values = {
                    "bus": "0x3",
                    "vendor": "0x3eb",
                    "product": "0x214e",
                    "version": "0x111"
                }
                
                # validate each value
                for i, (key, expected) in enumerate(expected_values.items()):
                    if i * 2 + 1 >= len(id_parts) or id_parts[i * 2 + 1] != expected:
                        return False, f"{key} ID detected failed"
            
            # Record the current axis
            if "ABS_X" in line:
                current_axis = "X"
            elif "ABS_Y" in line:
                current_axis = "Y"
            
            # validate resolution
            if "Max" in line and current_axis:
                if current_axis == "X" and "1919" not in line:
                    return False, "x-axis resolution detected failed"
                elif current_axis == "Y" and "1079" not in line:
                    return False, "y-axis resolution detected failed"
        
        return True, "All validations passed"
