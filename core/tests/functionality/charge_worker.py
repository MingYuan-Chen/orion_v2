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

        self.BATTERY_STATUS_MAP = {
            128: "Charging",
            192: "Discharging",
            160: "Full Charged",
            224: "Full Charged",
            144: "Full Discharged",
            32770: "Initializing",
            32896: "Over Charged",
            16512: "Terminate Charge",
            16544: "Full Charged, Terminate Charge",
            20608: "Over Temperature, Terminate Charge",
            20672: "Over Temperature, Terminate Charge",
            4224: "Over Temperature - Charge",
            4288: "Over Temperature - Discharge",
            3008: "Remaining Capacity and Time Alarm, Terminate Charge",
            960: "Remaining Capacity and Time Alarm",
            704: "Remaining Capacity Alarm",
            448: "Remaining Time Alarm",
        }

    
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
                validation_func=self._validate_battery_status,
                timeout=5, 
                description="Validate battery status",
                criteria="Can read the battery status",
                max_retries=1,
                retry_delay=500
                
            ),
            TestStep(
                command=commands[1], 
                validation_func=self._validate_battery_state,
                timeout=5, 
                description="Validate battery state is in 0 ~ 100%",
                criteria="Battery state is in 0 ~ 100%",
                max_retries=3,
                retry_delay=500
            ),
            TestStep(
                command=commands[2],
                validation_func=self._validate_current,
                timeout=5,
                description="Validate current is in -4 ~ 1.2A",
                criteria="Current is in -4 ~ 1.2A",
                max_retries=3,
                retry_delay=500
            )
        ]
    
    def _parse_battery_info(self, response: str) -> Any:
        """
        Parse battery information from i2ctransfer commands
        
        Args:
            command_name: Name of the command (capacity, full_capacity, etc.)
            response: Command response
            
        Returns:
            Parsed battery information value
        """
        try:
            lines = response.strip().split('\n')
            hex_values = []
            
            for line in lines:
                # Skip command echo lines
                if 'i2ctransfer' in line or 'sleep' in line or 'root@' in line:
                    continue
                    
                # Look for hex values in the line
                if '0x' in line:
                    line_hex = [x.strip() for x in line.split() if x.startswith('0x')]
                    if line_hex:
                        hex_values.extend(line_hex)
            
            # Extract the correct hex values for battery commands
            # Typical i2c response format: 0x02 0xHH 0xLL (status + high byte + low byte)
            if len(hex_values) >= 3:
                # Skip the first byte (status byte 0x02) and use the next 2 bytes as data
                high_byte = int(hex_values[1], 16)  # Second hex value
                low_byte = int(hex_values[2], 16)   # Third hex value
                value = (high_byte << 8) + low_byte
                return value
            elif len(hex_values) == 2:
                # Two values: use both as data (high byte + low byte)
                high_byte = int(hex_values[0], 16)
                low_byte = int(hex_values[1], 16)
                value = (high_byte << 8) + low_byte
                return value
            elif len(hex_values) == 1:
                # Single value
                value = int(hex_values[0], 16)
                return value
            else:
                logger.warning(f"No valid hex values found in response: {response}")
                return None
        
        except Exception as e:
            logger.error(f"Error in battery info parsing: {str(e)}")
            return None

    def _validate_battery_status(self, response: str) -> Tuple[bool, str]:
        """
        Validate battery status
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            value = self._parse_battery_info(response)
            if type(value) != int:
                return False, f"Unexpected battery status: {value}"
            
            return True, f"Battery status: {self.BATTERY_STATUS_MAP[value]}"
        except Exception as e:
            logger.error(f"exception in battery status: {e}")
            return False, f"exception in battery status: {e}"
    
    def _validate_battery_state(self, response: str) -> Tuple[bool, str]:
        """
        Validate battery state
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            value = self._parse_battery_info(response)
            if value <= 100 and value >= 0:
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
            value = self._parse_battery_info(response)
            if value > -4000 and value < 1200:
                return True, f"Current is {value}mA"
            else:
                return False, f"Current is {value}mA"
        
        except Exception as e:
            logger.error(f"exception in current: {e}")
            return False, f"exception in current: {e}"
