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
        self.platform_name = platform_name
        self.battery_model = None
        self.charge_current_setting = None
        self.charge_voltage_setting = None

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
            2176: "Terminate Discharge",
            2432: "Remaining Time Alarm, Terminate Discharge",
            2688: "Remaining Capacity Alarm, Terminate Discharge",
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
                validation_func=self._validate_battery_status if self.platform_name != "athena" else self._validate_battery_model,
                timeout=5, 
                description="Validate battery status" if self.platform_name != "athena" else "Validate battery model",
                criteria="Can read the battery status" if self.platform_name != "athena" else "Can read the battery model",
                max_retries=1,
                retry_delay=500
                
            ),
            TestStep(
                command=commands[1], 
                validation_func=self._validate_battery_state if self.platform_name != "athena" else self._validate_charge_current_setting,
                timeout=5, 
                description="Validate battery state is in 0 ~ 100%" if self.platform_name != "athena" else "Validate charge current setting",
                criteria="Battery state is in 0 ~ 100%" if self.platform_name != "athena" else "Charge current setting is 0x00 0xc0 = 192ma(low battery charge) or 0x03 0x00 = 768ma(normal charge)",
                max_retries=3,
                retry_delay=500
            ),
            TestStep(
                command=commands[2],
                validation_func=self._validate_current if self.platform_name != "athena" else self._validate_charge_voltage_setting,
                timeout=5,
                description="Validate current is in -4 ~ 1.2A" if self.platform_name != "athena" else "Validate charge voltage setting",
                criteria="Current is in -4 ~ 1.2A" if self.platform_name != "athena" else "Charge voltage setting is 0x23 0x20 = 8992mv(low battery charge) or 0x31 0x30 = 12592mv(normal charge)",
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
            if len(hex_values) >= 10:
                # Skip first two bytes (status/length bytes), use next 8 bytes for data
                data_hex_values = hex_values[2:10]  # Take bytes 3-10
                # Convert hex values to ASCII characters
                ascii_chars = []
                for hex_val in data_hex_values:
                    try:
                        char_code = int(hex_val, 16)
                        if 32 <= char_code <= 126:  # Printable ASCII range
                            ascii_chars.append(chr(char_code))
                        else:
                            ascii_chars.append('?')  # Replace non-printable chars
                    except (ValueError, OverflowError):
                        ascii_chars.append('?')  # Replace invalid chars
                
                # Join characters and remove trailing nulls/spaces
                model_string = ''.join(ascii_chars).rstrip('\x00').rstrip()
                return model_string
            elif len(hex_values) >= 3:
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
            if value > 32767:
                signed_value = value - 65536  # Convert to signed
            else:
                signed_value = value
            if signed_value > -4000 and signed_value < 1200:
                return True, f"Current is {signed_value}mA"
            else:
                return False, f"Current is {signed_value}mA"
        
        except Exception as e:
            logger.error(f"exception in current: {e}")
            return False, f"exception in current: {e}"
    
    def _validate_battery_model(self, response: str) -> Tuple[bool, str]:
        """
        Validate battery model
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            model_string = self._parse_battery_info(response)
            logger.info(f"Battery model is {model_string}")
            if model_string == "MD-BAT03":
                self.battery_model = model_string
                return True, f"Battery model is {model_string}"
            elif model_string == "????????":
                return True, f"No battery connected"
            else:
                return False, f"Battery model is {model_string}"
        except Exception as e:
            logger.error(f"exception in battery model: {e}")
            return False, f"exception in battery model: {e}"
    
    def _validate_charge_current_setting(self, response: str) -> Tuple[bool, str]:
        """
        Validate battery status
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        value = self._parse_battery_info(response)
        if self.battery_model == "MD-BAT03" and value == 768:
            return True, f"Charge current setting is 768ma"
        elif self.battery_model is None and value == 192:
            return True, f"Charge current setting is 192ma"
        else:
            return False, f"Charge current setting is {value}ma"
    
    def _validate_charge_voltage_setting(self, response: str) -> Tuple[bool, str]:
        """
        Validate battery status
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        value = self._parse_battery_info(response)
        if self.battery_model == "MD-BAT03" and value == 12592:
            return True, f"Charge voltage setting is 12592mv"
        elif self.battery_model is None and value == 8992:
            return True, f"Charge voltage setting is 8992mv"
        else:
            return False, f"Charge voltage setting is {value}mv"