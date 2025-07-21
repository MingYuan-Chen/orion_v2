"""
Battery worker module
Implement battery test for device
"""
from typing import List, Tuple, Any
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class BatteryWorker(BaseTestWorker):
    """Battery worker, implement battery test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_battery"
        
        self.LED_STATUS_MAP = {
            0: "Off", 8: "Off", 16: "Off", 24: "Off", 32: "Off",
            1: "Blue", 9: "Blue Blinking", 17: "Blue", 25: "Blue Blinking", 33: "Blue", 41: "Blue Blinking",
            2: "Green", 10: "Green Blinking", 18: "Green", 26: "Green Blinking", 34: "Green", 42: "Green Blinking",
            3: "Cyan", 11: "Cyan Blinking", 19: "Cyan", 27: "Cyan Blinking", 35: "Cyan", 43: "Cyan Blinking",
            4: "Red", 12: "Red Blinking", 20: "Red", 28: "Red Blinking", 36: "Red", 44: "Red Blinking",
            5: "Fuchsia", 13: "Fuchsia Blinking", 21: "Fuchsia", 29: "Fuchsia Blinking", 37: "Fuchsia", 45: "Fuchsia Blinking",
            6: "Orange", 14: "Orange Blinking", 22: "Orange", 30: "Orange Blinking", 38: "Orange", 46: "Orange Blinking",
            7: "White", 15: "White Blinking", 23: "White", 31: "White Blinking", 39: "White", 47: "White Blinking"
        }

        self.INTERRUPT_STATUS_MAP = {
            0: "Normal",
            1: "No Battery",
            2: "Timeout",
            8: "Over Temperature - Charge",
            16: "Over Current - Charge",
            24: "Over Current & Temperature - Charge",
            32: "Over Temperature - Discharge",
            64: "Over Current - Discharge",
            96: "Over Current & Temperature - Discharge",
        }

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

        self.current_dc = None
        self.current_led = None
        self.current_temperature = None
        self.current_battery_state = None

    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare battery test steps
        
        Returns:
            battery test steps list
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
                description="Validate battery state",
                criteria="Can read the battery state",
                max_retries=3,
                retry_delay=500
            ),
            TestStep(
                command=commands[2], 
                validation_func=self._validate_temperature,
                timeout=10, 
                description="Validate battery temperature",
                criteria="Can read the battery temperature",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command=commands[3], 
                validation_func=self._validate_current,
                timeout=10, 
                description="Validate battery current",
                criteria="Can read the battery current",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command=commands[4], 
                validation_func=self._validate_led_status,
                timeout=10, 
                description="Validate led status",
                criteria="Can read the led status",
                max_retries=2,
                retry_delay=1500
            )
        ]
    
    def _parse_battery_info(self, command_name: str, response: str) -> Any:
        """
        Parse battery information from i2ctransfer commands
        
        Args:
            command_name: Name of the command (capacity, full_capacity, etc.)
            response: Command response
            
        Returns:
            Parsed battery information value
        """
        try:
            value = None

            # Process i2ctransfer command results
            if command_name in ["capacity", "battery_status", "relative_state", "charging_voltage", 
                               "charging_current", "temperature", "cycle_count", "led_status"]:
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
                    elif len(hex_values) == 2:
                        # Two values: use both as data (high byte + low byte)
                        high_byte = int(hex_values[0], 16)
                        low_byte = int(hex_values[1], 16)
                        value = (high_byte << 8) + low_byte
                    elif len(hex_values) == 1:
                        # Single value
                        value = int(hex_values[0], 16)
                    else:
                        logger.warning(f"No valid hex values found in response for {command_name}: {response}")
                        return None
                    
                    # Convert format according to different types
                    if command_name == "capacity":
                        # Return capacity value directly
                        parsed_value = value
                    elif command_name == "full_capacity":
                        # Return full capacity value directly
                        parsed_value = value
                    elif command_name == "relative_state":
                        # Return relative state value directly
                        parsed_value = value
                    elif command_name == "charging_voltage":
                        # Convert voltage to volts (V)
                        parsed_value = round(float(value/1000), 2)
                    elif command_name == "charging_current":
                        # Convert current to amperes (A)
                        parsed_value = round(float(value/1000), 2)
                    elif command_name == "temperature":
                        # Convert temperature to Celsius (°C)
                        parsed_value = round(float(value/10)-273.2, 1)
                    elif command_name == "cycle_count":
                        # Return cycle count value directly
                        parsed_value = value
                    elif command_name == "led_status":
                        # Return LED status value directly
                        parsed_value = value
                    else:
                        parsed_value = value
                    
                    logger.debug(f"Parsed {command_name}: {parsed_value}")
                    return parsed_value
                    
                except Exception as e:
                    logger.error(f"Failed to parse {command_name}: {e}")
                    return None
            
            # If it's not a known battery command, return the original response
            return response
            
        except Exception as e:
            logger.error(f"Error in battery info parsing for {command_name}: {str(e)}")
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
            value = self._parse_battery_info("battery_status", response)
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
            value = self._parse_battery_info("relative_state", response)
            if type(value) != int:
                return False, f"Unexpected battery state: {value}"
            
            # if value < 0 or value > 100:
            #     return False, f"Unreasonable battery state: {value}"
            
            self.current_battery_state = value
            return True, f"Battery state: {value}%"
        except Exception as e:
            logger.error(f"exception in discharging state: {e}")
            return False, f"exception in discharging state: {e}"
        
    def _validate_temperature(self, response: str) -> Tuple[bool, str]:
        """
        Validate battery temperature
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            value = self._parse_battery_info("temperature", response)
            if type(value) != float:
                return False, f"Unexpected battery temperature: {value}"
            
            # if value < 0 or value > 100:
            #     return False, f"Unreasonable battery temperature: {value}"
            
            self.current_temperature = value
            return True, f"Battery temperature: {value}°C"
        except Exception as e:
            logger.error(f"exception in discharging temperature: {e}")
            return False, f"exception in discharging temperature: {e}"
    
    def _validate_led_status(self, response: str) -> Tuple[bool, str]:
        """
        Validate LED status
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            value = self._parse_battery_info("led_status", response)
            if type(value) != int:
                return False, f"Unexpected led status: {value}"
            
            if value not in self.LED_STATUS_MAP:
                return False, f"Unexpected led status: {value}"

            self.current_led = value
            return True, f"LED status: {self.LED_STATUS_MAP[value]}"
        except Exception as e:
            logger.error(f"exception in discharging led status: {e}")
            return False, f"exception in discharging led status: {e}"
        
    def _validate_current(self, response: str) -> Tuple[bool, str]:
        """
        Validate current
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            value = self._parse_battery_info("charging_current", response)
            if type(value) != float:
                return False, f"Unexpected current: {value}"
            
            return True, f"Current: {value}"
        except Exception as e:
            logger.error(f"exception in discharging current: {e}")
            return False, f"exception in discharging current: {e}"

