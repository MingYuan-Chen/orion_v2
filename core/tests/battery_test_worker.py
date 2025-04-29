"""
USB ports test worker module
Implement USB port function test for device
"""
from typing import List, Tuple, Any
import logging
from .base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class BatteryTestWorker(BaseTestWorker):
    """Battery test worker, implement battery discharging test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
        self.get_battery_state = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x0d r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x0d r2"
        self.get_temperature = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x08 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x08 r2"
        self.get_led_status = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x14 r2"
        self.get_current = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x14 r2"
        self.LED_STATUS_MAP = {
            0: "Off", 8: "Off", 16: "Off", 24: "Off",
            1: "Blue", 9: "Blue Blinking", 17: "Blue", 25: "Blue Blinking",
            2: "Green", 10: "Green Blinking", 18: "Green", 26: "Green Blinking",
            3: "Cyan", 11: "Cyan Blinking", 19: "Cyan", 27: "Cyan Blinking",
            4: "Red", 12: "Red Blinking", 20: "Red", 28: "Red Blinking",
            5: "Fuchsia", 13: "Fuchsia Blinking", 21: "Fuchsia", 29: "Fuchsia Blinking",
            6: "Orange", 14: "Orange Blinking", 22: "Orange", 30: "Orange Blinking",
            7: "White", 15: "White Blinking", 23: "White", 31: "White Blinking"
        }
        self.current_dc = None
        self.current_led = None
        self.current_temperature = None
        self.current_battery_state = None

    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare battery discharging test steps
        
        Returns:
            discharging test steps list
        """
        return [
            TestStep(
                command="cat /sys/class/gpio/gpio133/value", 
                validation_func=self._validate_dc_status,
                timeout=5, 
                description="Validate dc status",
                max_retries=1,           # Maximum retries 1 time
                retry_delay=500          # 0.5 seconds later retry
            ),
            TestStep(
                command=self.get_battery_state, 
                validation_func=self._validate_battery_state,
                timeout=5, 
                description="Validate battery state",
                max_retries=3,           # Maximum retries 3 times
                retry_delay=500          # 0.5 seconds later retry
            ),
            TestStep(
                command=self.get_temperature, 
                validation_func=self._validate_temperature,
                timeout=10, 
                description="Validate battery temperature",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            ),
            TestStep(
                command=self.get_current, 
                validation_func=self._validate_current,
                timeout=10, 
                description="Validate batterycurrent",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            ),
            TestStep(
                command=self.get_led_status, 
                validation_func=self._validate_led_status,
                timeout=10, 
                description="Validate led status",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
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
            value = response
            
            # Special processing for dc_status
            if command_name == "dc_status":
                try:
                    value = int(response.strip().split("\n")[0])
                    logger.debug(f"Parsed {command_name}: {value}")
                    return value
                except Exception as e:
                    logger.error(f"Failed to parse {command_name}: {e}")
                    return None
            
            # Process i2ctransfer command results
            if command_name in ["capacity", "full_capacity", "relative_state", "charging_voltage", 
                               "charging_current", "temperature", "cycle_count", "led_status"]:
                try:
                    # Extract hexadecimal value part
                    value = response.split("r2\n")[1].split("root")[0].split("\n")[1].replace(" 0x", "")
                    value = int(value, 16)
                    
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
                        parsed_value = round(float(value/10)-273.15, 2)
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
    
    def _validate_dc_status(self, response: str) -> Tuple[bool, str]:
        """
        Validate dc status
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            value = self._parse_battery_info("dc_status", response)
            if type(value) != int:
                return False, f"Unexpected dc status: {value}"
            
            if value not in [0, 1]:
                return False, f"Unexpected dc status: {value}"
            
            self.current_dc = value
            return True, f"DC status: {value} {'discharging' if value == 0 else 'charging'}"
        except Exception as e:
            logger.error(f"exception in dc status: {e}")
            return False, f"exception in dc status: {e}"

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
            
            if value < 0 or value > 100:
                return False, f"Unreasonable battery state: {value}"
            
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
            
            if value < 0 or value > 100:
                return False, f"Unreasonable battery temperature: {value}"
            
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
            
            if self.current_dc == 0:
                if self.current_battery_state > 10 and self.current_battery_state <= 100:
                    if value not in [0, 16]:
                        return False, f"Unexpected led status: {self.LED_STATUS_MAP[value]}"
                else:
                    if value not in [12, 28]:
                        return False, f"Unexpected led status: {self.LED_STATUS_MAP[value]}"
            else:
                if self.current_battery_state == 100:
                    if value not in [2, 18]:
                        return False, f"Unexpected led status: {self.LED_STATUS_MAP[value]}"
                elif self.current_battery_state > 10 and self.current_battery_state <= 99:
                    if value not in [1, 17]:
                        return False, f"Unexpected led status: {self.LED_STATUS_MAP[value]}"
                else:
                    if value not in [12, 28]:
                        return False, f"Unexpected led status: {self.LED_STATUS_MAP[value]}"

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
            
            if value < 1.5 or value > 2.5:
                return False, f"Unreasonable current: {value}"
            
            return True, f"Current: {value}"
        except Exception as e:
            logger.error(f"exception in discharging current: {e}")
            return False, f"exception in discharging current: {e}"

