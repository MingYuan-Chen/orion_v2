"""
Charge worker module
Implement charge test for device
"""
from typing import List, Tuple, Any
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger

class ChargeWorker(BaseTestWorker):
    """Charge worker, implement charge test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.get_battery_state = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x0d r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x0d r2"
        self.get_current = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x0a r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x0a r2"

    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare charge test steps
        
        Returns:
            charge test steps list
        """
        return [
            TestStep(
                command="cat /sys/class/gpio/gpio133/value", 
                expected_response="0",
                timeout=5, 
                description="Validate DUT is unplugged from the power source",
                pre_condition="Ensure the DUT is unplugged from the power source.",
                max_retries=1,
                retry_delay=500
                
            ),
            TestStep(
                command=self.get_battery_state, 
                validation_func=self._validate_battery_state,
                timeout=5, 
                description="Validate battery state is lower than 25%",
                pre_condition="Ensure the battery state is lower than 25%",
                max_retries=3,
                retry_delay=500
            ),
            TestStep(
                command=self.get_current,
                validation_func=self._validate_current,
                timeout=5,
                description="Validate current is negative",
                max_retries=3,
                retry_delay=500
            )
        ]
    
    def _parse_response(self, response: str) -> Any:
        """
        Parse i2ctransfer command response
        
        Args:
            response: Command response
            
        Returns:
            Parsed value
        """
        try:
            value = response.split("\n")[3]
            from util.numeric_converter import numeric_converter
            return numeric_converter.hex_to_signed_decimal(value)
        
        except Exception as e:
            logger.error(f"Error in i2ctransfer command response parsing: {str(e)}")
            return None

    def _validate_battery_state(self, response: str) -> Tuple[bool, str]:
        """
        Validate battery state
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            value = self._parse_response(response)
            if value < 25 and value > 0:
                return True, f"Battery state is {value}%"
            else:
                return False, f"Battery state is {value}%"
            
        except Exception as e:
            logger.error(f"exception in discharging state: {e}")
            return False, f"exception in discharging state: {e}"
        
    def _validate_current(self, response: str) -> Tuple[bool, str]:
        """
        Validate current
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            value = self._parse_response(response)
            if value < 0 and value > -4100:
                return True, f"Current is {value}mA"
            else:
                return False, f"Current is {value}mA"
        
        except Exception as e:
            logger.error(f"exception in current: {e}")
            return False, f"exception in current: {e}"
