"""
LED worker module
Implement led function test for device
"""
from typing import List, Tuple, Any
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class LedWorker(BaseTestWorker):
    """Led worker, implement led function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
        self.set_led_status = lambda status: f"i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 {status} r2"
        self.get_led_status = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x14 r2"
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
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare led test steps
        
        Returns:
            led test steps list
        """
        return [
            TestStep(
                command=self.set_led_status(f"{1:#04x}"),  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[1]}",
            ),
            TestStep(
                command=self.get_led_status, 
                validation_func=self._validate_led_status_blue,
                timeout=5, 
                description="Check led status blue",
                post_check="Is the led status blue?",
                max_retries=3,
                retry_delay=5000
            ),
            TestStep(
                command=self.set_led_status(f"{2:#04x}"),  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[2]}",
            ),
            TestStep(
                command=self.get_led_status, 
                validation_func=self._validate_led_status_green,
                timeout=5, 
                description="Check led status green",
                post_check="Is the led status green?",
                max_retries=3,
                retry_delay=5000
            ),
            TestStep(
                command=self.set_led_status(f"{4:#04x}"),  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[4]}",
            ),
            TestStep(
                command=self.get_led_status, 
                validation_func=self._validate_led_status_red,
                timeout=5, 
                description="Check led status red",
                post_check="Is the led status red?",
                max_retries=3,
                retry_delay=5000
            ),
            TestStep(
                command=self.set_led_status(f"{9:#04x}"),  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[9]}",
            ),
            TestStep(
                command=self.get_led_status, 
                validation_func=self._validate_led_status_blinking_blue,
                timeout=5, 
                description="Check led status blinking blue",
                post_check="Is the led status blinking blue?",
                max_retries=3,
                retry_delay=5000
            ),
            TestStep(
                command=self.set_led_status(f"{10:#04x}"),  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[10]}",
            ),
            TestStep(
                command=self.get_led_status, 
                validation_func=self._validate_led_status_blinking_green,
                timeout=5, 
                description="Check led status blinking green",
                post_check="Is the led status blinking green?",
                max_retries=3,
                retry_delay=5000
            ),
            TestStep(
                command=self.set_led_status(f"{12:#04x}"),  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[12]}",
            ),
            TestStep(
                command=self.get_led_status, 
                validation_func=self._validate_led_status_blinking_red,
                timeout=5, 
                description="Check led status blinking red",
                post_check="Is the led status blinking red?",
                max_retries=3,
                retry_delay=5000
            ),
            TestStep(
                command=self.set_led_status(f"{0:#04x}"),  
                timeout=5, 
                description=f"Set led status to {self.LED_STATUS_MAP[0]}",
            )
        ]
    
    def _parse_led_info(self, response: str) -> Any:
        """
        Parse led information from i2ctransfer commands
        
        Args:
            command_name: Name of the command (capacity, full_capacity, etc.)
            response: Command response
            
        Returns:
            Parsed battery information value
        """
            
        try:
            value = response.split("r2\n")[1].split("root")[0].split("\n")[1].replace(" 0x", "")
            return int(value, 16)
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
            if led_status == 1:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
        
    def _validate_led_status_green(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status == 2:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
    
    def _validate_led_status_red(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status == 4:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
    
    def _validate_led_status_blinking_blue(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status == 9:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
    
    def _validate_led_status_blinking_green(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status == 10:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"
    
    def _validate_led_status_blinking_red(self, response: str) -> Tuple[bool, str]:
        try:
            led_status = self._parse_led_info(response)
            if led_status == 12:
                return True, f"Led status is {self.LED_STATUS_MAP[led_status]}"
            return False, f"Unexpected led status: {self.LED_STATUS_MAP[led_status]}"
        except Exception as e:
            return False, f"Error validating led status: {e}"