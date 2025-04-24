"""
USB ports test worker module
Implement USB port function test for device
"""
from typing import List, Tuple, Any
import logging
from .base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class BatteryTestDischargingWorker(BaseTestWorker):
    """Battery test worker, implement battery discharging test for device"""
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare battery discharging test steps
        
        Returns:
            discharging test steps list
        """
        return [
            TestStep(
                command="i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x0d r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x0d r2", 
                validation_func=self._validate_battery_state_in_step_1,
                timeout=5, 
                description="Validate battery state should be more than 90%",
                max_retries=3,           # Maximum retries 1 time
                retry_delay=500          # 0.5 seconds later retry
            ),
            self.create_wait_step(
                wait_time_ms=10000,  # 10 seconds
                description="Wait for battery discharging"
            ),
            TestStep(
                command="i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x0d r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x0d r2", 
                validation_func=self._validate_battery_state_in_step_2,
                timeout=10, 
                description="Validate battery discharging should be more than 30%",
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
    
    def _validate_battery_state_in_step_1(self, response: str) -> Tuple[bool, str]:
        """
        Validate battery state in step 1
        
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
            
            if value < 90:
                return False, f"Battery state is less than 90%: {value}"
            
            return True, f"Battery state: {value}"
        except Exception as e:
            logger.error(f"exception in discharging step 1: {e}")
            return False, f"exception in discharging step 1: {e}"
        
    def _validate_battery_state_in_step_2(self, response: str) -> Tuple[bool, str]:
        """
        Validate battery state in step 2
        
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
            
            if value < 30:
                return False, f"Battery discharging is less than 30%: {value}"
            
            return True, f"Battery state: {value}"
        except Exception as e:
            logger.error(f"exception in discharging step 2: {e}")
            return False, f"exception in discharging step 2: {e}"
