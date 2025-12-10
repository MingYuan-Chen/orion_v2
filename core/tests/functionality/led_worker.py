"""
LED worker module
Implement led function test for device
"""
from typing import List, Tuple, Any
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class LedWorker(BaseTestWorker):
    """Led worker, implement led function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_led"
        self.LED_STATUS_MAP = {
            0: "Off",       8: "Off",               16: "Off",      24: "Off",              32: "Off",
            1: "Blue",      9: "Blue Blinking",     17: "Blue",     25: "Blue Blinking",    33: "Blue",     49: "Blue Blinking",
            2: "Green",     10: "Green Blinking",   18: "Green",    26: "Green Blinking",   34: "Green",    50: "Green Blinking",
            3: "Cyan",      11: "Cyan Blinking",    19: "Cyan",     27: "Cyan Blinking",
            4: "Red",       12: "Red Blinking",     20: "Red",      28: "Red Blinking",     36: "Red",      52: "Red Blinking",
            5: "Fuchsia",   13: "Fuchsia Blinking", 21: "Fuchsia",  29: "Fuchsia Blinking",
            6: "Orange",    14: "Orange Blinking",  22: "Orange",   30: "Orange Blinking",  38: "Orange",   54: "Orange Blinking",
            7: "White",     15: "White Blinking",   23: "White",    31: "White Blinking",   40: "Yellow",   56: "Yellow Blinking",
        }
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare led test steps
        
        Returns:
            led test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
            TestStep(
                command=commands[0],  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[1]}",
            ),
            TestStep(
                command=commands[1],  
                # validation_func=self._validate_led_status_blue,
                timeout=5, 
                description="Check led status blue",
                post_check="Is the led status blue?",
                criteria="Led status is blue",
                manual_only=True
            ),
            TestStep(
                command=commands[2],  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[2]}",
            ),
            TestStep(
                command=commands[3],  
                # validation_func=self._validate_led_status_green,
                timeout=5, 
                description="Check led status green",
                post_check="Is the led status green?",
                criteria="Led status is green",
                manual_only=True
            ),
            TestStep(
                command=commands[4],  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[4]}",
            ),
            TestStep(
                command=commands[5],  
                # validation_func=self._validate_led_status_red,
                timeout=5, 
                description="Check led status red",
                post_check="Is the led status red?",
                criteria="Led status is red",
                manual_only=True
            ),
            TestStep(
                command=commands[6],  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[9]}",
            ),
            TestStep(
                command=commands[7],  
                # validation_func=self._validate_led_status_blinking_blue,
                timeout=5, 
                description="Check led status blinking blue",
                post_check="Is the led status blinking blue?",
                criteria="Led status is blinking blue",
                manual_only=True
            ),
            TestStep(
                command=commands[8],  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[10]}",
            ),
            TestStep(
                command=commands[9],  
                # validation_func=self._validate_led_status_blinking_green,
                timeout=5, 
                description="Check led status blinking green",
                post_check="Is the led status blinking green?",
                criteria="Led status is blinking green",
                manual_only=True
            ),
            TestStep(
                command=commands[10],  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[12]}",
            ),
            TestStep(
                command=commands[11],  
                # validation_func=self._validate_led_status_blinking_red,
                timeout=5, 
                description="Check led status blinking red",
                post_check="Is the led status blinking red?",
                criteria="Led status is blinking red",
                manual_only=True
            ),
            TestStep(
                command=commands[12],  
                timeout=5, 
                description=f"Set led status to PIC control",
            )
        ]
    
    def _parse_led_info(self, response: str) -> Any:
        """
        Parse led information from i2ctransfer commands
        
        Args:
            response: Command response
            
        Returns:
            Parsed LED status value
        """
            
        try:
            # LED command response format:
            # Line 1: 0x02 (status)
            # Line 2: 0x00 0x0a (actual LED status data)
            
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            
            # Look for hex values in the response
            hex_values = []
            for line in lines:
                if '0x' in line:
                    # Extract all hex values from this line
                    line_hex = [x.strip() for x in line.split() if x.startswith('0x')]
                    hex_values.extend(line_hex)
            
            # For LED status, we need the last hex value (the actual status)
            if len(hex_values) >= 2:
                # Take the last hex value as the LED status
                led_status_hex = hex_values[-1]
                return int(led_status_hex, 16)
            elif len(hex_values) == 1:
                # If only one hex value, use it
                return int(hex_values[0], 16)
            else:
                logger.error(f"No hex values found in LED response: {response}")
                return None
                
        except Exception as e:  
            logger.error(f"Failed to parse led status: {e}")
            return None
        
    def _validate_led_status_blue(self, response: str) -> Tuple[bool, str]:
        """
        Validate led status
        
        Args:
            response: Command response
            
        Returns:
            Tuple of (bool, str): (True if valid, error message if invalid)
        """
        try:
            led_status = self._parse_led_info(response)
            if led_status in [1, 17]:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
        
    def _validate_led_status_green(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status in [2, 18]:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
    
    def _validate_led_status_red(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status in [4, 20]:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
    
    def _validate_led_status_blinking_blue(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status in [9, 25]:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
    
    def _validate_led_status_blinking_green(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status in [10, 26]:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
    
    def _validate_led_status_blinking_red(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status in [12, 28]:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"