"""
Charge worker module
Implement charge test for device
"""
from typing import List, Tuple, Any
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class ChargeWorker(BaseTestWorker):
    """Charge worker, implement charge test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_charge"

    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare charge test steps
        
        Returns:
            charge test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)  
        return [
            TestStep(
                command=commands[0], 
                expected_response="1",
                timeout=5, 
                description="Validate DUT is charging",
                criteria="The DUT is charging",
                pre_condition="Ensure battery state is lower than 23% and Connect the DUT to the power source",
                max_retries=1,
                retry_delay=500
                
            ),
            TestStep(
                command=commands[1], 
                validation_func=self._validate_battery_state,
                timeout=5, 
                description="For charge current test, validate battery state is lower than 23% (Upper limited 25% by BLT tool)",
                criteria="Battery state is in 0 ~ 23%",
                max_retries=3,
                retry_delay=500
            ),
            TestStep(
                command=commands[2],
                validation_func=self._validate_current,
                timeout=5,
                description="Validate current is positive",
                criteria="Current is in 0 ~ 1200mA",
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
            lines = response.strip().split('\n')
            hex_values = []
            for line in lines:
                # Skip command echo lines
                if 'i2ctransfer' in line or 'sleep' in line or 'root@' in line:
                    continue
                    
                logger.debug(f"filter line: {line}")
                # Look for hex values in the line
                if '0x' in line:
                    line_hex = [x.strip() for x in line.split() if x.startswith('0x')]
                    if line_hex:
                        hex_values.extend(line_hex)
            
            if len(hex_values) >= 3:
                # Use the last two hex values to form the result
                # For example: ['0x02', '0x00', '0x3a'] -> use '0x00' and '0x3a' to form '0x003a'
                hex1 = hex_values[-2].replace('0x', '')  # Remove '0x' prefix
                hex2 = hex_values[-1].replace('0x', '')  # Remove '0x' prefix
                combined_hex = f"0x{hex1}{hex2}"  # Combine as "0x003a"
                return int(combined_hex, 16)
            else:
                logger.error(f"Get unexpected hex values: {hex_values}")
                return None
        
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
            if value < 24 and value > 0:
                return True, f"Battery state is {value}%"
            else:
                return False, f"Battery state is {value}%"
            
        except Exception as e:
            logger.error(f"exception in charging state: {e}")
            return False, f"exception in charging state: {e}"
        
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
            if value > 0 and value < 1200:
                return True, f"Current is {value}mA"
            else:
                return False, f"Current is {value}mA"
        
        except Exception as e:
            logger.error(f"exception in current: {e}")
            return False, f"exception in current: {e}"
