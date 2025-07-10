"""
Camera worker module
Implement camera function test for device
"""
from typing import List, Tuple
from util.logger import logger
from core.tests.base_test_worker import BaseTestWorker, TestStep
from core.tests.base_test_worker import CommandType

class CameraWorker(BaseTestWorker):
    """Camera worker, implement camera function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_camera"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare camera test steps
        
        Returns:
            camera test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
            # LVDS Camera ======================================================
            # port A(J1)
            TestStep(
                command=commands[0],
                pre_condition="Please ensure LVDS camera is connected to port A(J1)",
                timeout=5,
                description="Get GPIO value from Port A(J1)"
            ),
            TestStep(
                command=commands[1],
                validation_func=self._validate_gpio_value_lvds,
                timeout=5,
                description="Validate GPIO value of LVDS camera",
                criteria="The camera type is LVDS"
            ),
            TestStep(
                command=commands[2],
                timeout=5,
                description="Clear process",
            ),
            TestStep(
                command=commands[3],
                timeout=5,
                description="Reset port A(J1)",
            ),
            TestStep(
                command=commands[4],
                timeout=5,
                description="Detect port A(J1)",
            ),
            TestStep(
                command=commands[5],
                post_check="Is the preview video of LVDS camera displayed on the screen?",
                timeout=5, 
                description="Preview video of LVDS camera on port A(J1)",
                criteria="The preview video of LVDS camera is displayed on the screen"
            ),
            # port B(J4)
            TestStep(
                command=commands[6],
                pre_condition="Please ensure LVDS camera is connected to port B(J4)",
                timeout=5,
                description="Get GPIO value from Port B(J4)",  
            ),
            TestStep(
                command=commands[7],
                validation_func=self._validate_gpio_value_lvds,
                timeout=5,
                description="Validate GPIO value of LVDS camera",
                criteria="The camera type is LVDS"
            ),
            TestStep(
                command=commands[8],
                timeout=5,
                description="Clear process",
            ),
            TestStep(
                command=commands[9],
                timeout=5,
                description="Reset port B(J4)",
            ),
            TestStep(
                command=commands[10],
                timeout=5,
                description="Detect port B(J4)",
            ),
            TestStep(
                command=commands[11],
                post_check="Is the preview video of LVDS camera displayed on the screen?",
                timeout=5, 
                description="Preview video of LVDS camera on port B(J4)",
                criteria="The preview video of LVDS camera is displayed on the screen"
            ),
            # Scorpius Camera ======================================================
            # port A(J1)
            TestStep(
                command=commands[12],
                pre_condition="Please ensure Scorpius camera is connected to port A(J1)",
                timeout=5,
                description="Get GPIO value from Port A(J1)"
            ),
            TestStep(
                command=commands[13],
                validation_func=self._validate_gpio_value_Scorpius,
                timeout=5,
                description="Validate GPIO value of Scorpius camera",
                criteria="The camera type is Scorpius"
            ),
            TestStep(
                command=commands[14],
                timeout=5,
                description="Clear process",
            ),
            TestStep(
                command=commands[15],
                timeout=5,
                description="Reset port A(J1)",
            ),
            TestStep(
                command=commands[16],
                timeout=5,
                description="Detect port A(J1)",
            ),
            TestStep(
                command=commands[17],
                post_check="Is the preview video of Scorpius camera displayed on the screen?",
                timeout=5, 
                description="Preview video of Scorpius camera on port A(J1)",
                criteria="The preview video of Scorpius camera is displayed on the screen"
            ),
            # port B(J4)
            TestStep(
                command=commands[18],
                pre_condition="Please ensure Scorpius camera is connected to port B(J4)",
                timeout=5,
                description="Get GPIO value from Port B(J4)",  
            ),
            TestStep(
                command=commands[19],
                validation_func=self._validate_gpio_value_Scorpius,
                timeout=5,
                description="Validate GPIO value of Scorpius camera",
                criteria="The camera type is Scorpius"
            ),
            TestStep(
                command=commands[20],
                timeout=5,
                description="Clear process",
            ),
            TestStep(
                command=commands[21],
                timeout=5,
                description="Reset port B(J4)",
            ),
            TestStep(
                command=commands[22],
                timeout=5,
                description="Detect port B(J4)",
            ),
            TestStep(
                command=commands[23],
                post_check="Is the preview video of Scorpius camera displayed on the screen?",
                timeout=5, 
                description="Preview video of Scorpius camera on port B(J4)",
                criteria="The preview video of Scorpius camera is displayed on the screen"
            ),
            # MIPI VGA Camera ======================================================
            # port A(J1)
            TestStep(
                command=commands[24],
                pre_condition="Please ensure MIPI VGA camera is connected to port A(J1)",
                timeout=5,
                description="Get GPIO value from Port A(J1)"
            ),
            TestStep(
                command=commands[25],
                validation_func=self._validate_gpio_value_MIPI_VGA,
                timeout=5,
                description="Validate GPIO value of MIPI VGA camera",
                criteria="The camera type is MIPI VGA"
            ),
            TestStep(
                command=commands[26],
                timeout=5,
                description="Clear process",
            ),
            TestStep(
                command=commands[27],
                timeout=5,
                description="Reset port A(J1)",
            ),
            TestStep(
                command=commands[28],
                timeout=5,
                description="Detect port A(J1)",
            ),
            TestStep(
                command=commands[29],
                post_check="Is the preview video of MIPI VGA camera displayed on the screen?",
                timeout=5, 
                description="Preview video of MIPI VGA camera on port A(J1)",
                criteria="The preview video of MIPI VGA camera is displayed on the screen"
            ),
            # port B(J4)
            TestStep(
                command=commands[30],
                pre_condition="Please ensure MIPI VGA camera is connected to port B(J4)",
                timeout=5,
                description="Get GPIO value from Port B(J4)",  
            ),
            TestStep(
                command=commands[31],
                validation_func=self._validate_gpio_value_MIPI_VGA,
                timeout=5,
                description="Validate GPIO value of MIPI VGA camera",
                criteria="The camera type is MIPI VGA"
            ),
            TestStep(
                command=commands[32],
                timeout=5,
                description="Clear process",
            ),
            TestStep(
                command=commands[33],
                timeout=5,
                description="Reset port B(J4)",
            ),
            TestStep(
                command=commands[34],
                timeout=5,
                description="Detect port B(J4)",
            ),
            TestStep(
                command=commands[35],
                post_check="Is the preview video of MIPI VGA camera displayed on the screen?",
                timeout=5, 
                description="Preview video of MIPI VGA camera on port B(J4)",
                criteria="The preview video of MIPI VGA camera is displayed on the screen"
            ),
            # LVDS Smart Cable Camera ======================================================
            # port A(J1)
            TestStep(
                command=commands[36],
                pre_condition="Please ensure LVDSSmart Cable camera is connected to port A(J1)",
                timeout=5,
                description="Get GPIO value from Port A(J1)"
            ),
            TestStep(
                command=commands[37],
                validation_func=self._validate_gpio_value_smart_cable,
                timeout=5,
                description="Validate GPIO value of LVDS Smart Cable camera",
                criteria="The camera type is LVDS Smart Cable"
            ),
            TestStep(
                command=commands[38],
                timeout=5,
                description="Clear process",
            ),
            TestStep(
                command=commands[39],
                timeout=5,
                description="Reset port A(J1)",
            ),
            TestStep(
                command=commands[40],
                timeout=5,
                description="Detect port A(J1)",
            ),
            TestStep(
                command=commands[41],
                post_check="Is the preview video of LVDS Smart Cable camera displayed on the screen?",
                timeout=5, 
                description="Preview video of LVDS Smart Cable camera on port A(J1)",
                criteria="The preview video of LVDS Smart Cable camera is displayed on the screen"
            ),
            # port B(J4)
            TestStep(
                command=commands[42],
                pre_condition="Please ensure LVDS Smart Cable camera is connected to port B(J4)",
                timeout=5,
                description="Get GPIO value from Port B(J4)",  
            ),
            TestStep(
                command=commands[43],
                validation_func=self._validate_gpio_value_smart_cable,
                timeout=5,
                description="Validate GPIO value of LVDS Smart Cable camera",
                criteria="The camera type is LVDS Smart Cable"
            ),
            TestStep(
                command=commands[44],
                timeout=5,
                description="Clear process",
            ),
            TestStep(
                command=commands[45],
                timeout=5,
                description="Reset port B(J4)",
            ),
            TestStep(
                command=commands[46],
                timeout=5,
                description="Detect port B(J4)",
            ),
            TestStep(
                command=commands[47],
                post_check="Is the preview video of LVDS Smart Cable camera displayed on the screen?",
                timeout=5, 
                description="Preview video of LVDS Smart Cable camera on port B(J4)",
                criteria="The preview video of LVDS Smart Cable camera is displayed on the screen"
            ),
            # Jig A and B ======================================================
            # port A(J1)
            TestStep(
                command=commands[48],
                pre_condition="Please ensure Jig A is connected to port A(J1)",
                timeout=5,
                description="Get GPIO value from Jig A"
            ),
            TestStep(
                command=commands[49],
                validation_func=self._validate_gpio_value_jig_A,
                timeout=5,
                description="Validate GPIO value of Jig A",
                criteria="The camera type is Jig A"
            ),
            # port B(J4)
            TestStep(
                command=commands[50],
                pre_condition="Please ensure Jig B is connected to port B(J4)",
                timeout=5,
                description="Get GPIO value from Jig B"
            ),
            TestStep(
                command=commands[51],
                validation_func=self._validate_gpio_value_jig_B,
                timeout=5,
                description="Validate GPIO value of Jig B",
                criteria="The camera type is Jig B"
            ),
            TestStep(
                command=commands[52],
                timeout=5,
                description="Clear process",
            )
        ]
    
    def _parse_gpio_value(self, response: str) -> Tuple[bool, str]:
        """
        Parse GPIO value
        
        Args:
            response: Device response string
        """
        try:
            lines = response.strip().split("\n")
            values = [line.strip() for line in lines if line.strip()]
            value_str = "".join(values)
            return value_str
        except Exception as e:
            logger.error(f"exception in parsing GPIO value: {e}")
            return response
    
    def _validate_gpio_value_lvds(self, response: str) -> Tuple[bool, str]:
        """
        Validate GPIO value
        
        Args:
            response: Device response string
        """
        try:
            value_str = self._parse_gpio_value(response)

            if "1001" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}, expected to contain '1001'"
            
        except Exception as e:
            logger.error(f"exception in validating GPIO value: {e}")
            return False, f"exception in validating GPIO value: {e}"
    
    def _validate_gpio_value_Scorpius(self, response: str) -> Tuple[bool, str]:
        """
        Validate GPIO value
        
        Args:
            response: Device response string
        """
        try:
            value_str = self._parse_gpio_value(response)
            
            if "0111" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}, expected to contain '0111'"
            
        except Exception as e:
            logger.error(f"exception in validating GPIO value: {e}")
            return False, f"exception in validating GPIO value: {e}"

    def _validate_gpio_value_MIPI_VGA(self, response: str) -> Tuple[bool, str]:
        """
        Validate GPIO value
        
        Args:
            response: Device response string
        """
        try:
            value_str = self._parse_gpio_value(response)
            
            if "1011" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}, expected to contain '1011'"
            
        except Exception as e:
            logger.error(f"exception in validating GPIO value: {e}")
            return False, f"exception in validating GPIO value: {e}"
    
    def _validate_gpio_value_MIPI_720(self, response: str) -> Tuple[bool, str]:
        """
        Validate GPIO value
        
        Args:
            response: Device response string
        """
        try:
            value_str = self._parse_gpio_value(response)
            
            if "1101" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}, expected to contain '1101'"
            
        except Exception as e:
            logger.error(f"exception in validating GPIO value: {e}")
            return False, f"exception in validating GPIO value: {e}"

    def _validate_gpio_value_smart_cable(self, response: str) -> Tuple[bool, str]:
        """
        Validate GPIO value
        
        Args:
            response: Device response string
        """
        try:
            value_str = self._parse_gpio_value(response)
            
            if "0101" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}, expected to contain '0101'"
            
        except Exception as e:
            logger.error(f"exception in validating GPIO value: {e}")
            return False, f"exception in validating GPIO value: {e}"
    
    def _validate_gpio_value_jig_A(self, response: str) -> Tuple[bool, str]:
        """
        Validate GPIO value
        
        Args:
            response: Device response string
        """
        try:
            value_str = self._parse_gpio_value(response)
            
            if "1000" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}, expected to contain '1000'"
            
        except Exception as e:
            logger.error(f"exception in validating GPIO value: {e}")
            return False, f"exception in validating GPIO value: {e}"
        
    def _validate_gpio_value_jig_B(self, response: str) -> Tuple[bool, str]:
        """
        Validate GPIO value
        
        Args:
            response: Device response string
        """
        try:
            value_str = self._parse_gpio_value(response)
            
            if "0100" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}, expected to contain '0100'"
            
        except Exception as e:
            logger.error(f"exception in validating GPIO value: {e}")
            return False, f"exception in validating GPIO value: {e}"
