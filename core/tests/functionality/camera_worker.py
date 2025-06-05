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
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command=commands[1],
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=commands[2],
                # validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port A(J1)",
                criteria="The camera preview video is displayed on the screen",
                post_check="Is the camera preview video displayed on the screen?",
            ),
            TestStep(
                command=commands[3],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[4],
                validation_func=self._validate_gpio_value_lvds,
                timeout=5,
                description="Validate GPIO value of LVDS camera",
                criteria="The camera type is LVDS",
            ),
            TestStep(
                command=commands[5],
                timeout=5,
                description="Reset camera port A(J1)",
            ),
            # port B(J4)
            TestStep(
                command=commands[6],
                # validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port B(J4)",
                pre_condition="Please ensure LVDS camera is connected to port B(J4)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[7],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[8],
                validation_func=self._validate_gpio_value_lvds,
                timeout=5,
                description="Validate GPIO value of LVDS camera",
                criteria="The camera type is LVDS",
            ),
            TestStep(
                command=commands[9],
                timeout=5,
                description="Reset camera port B(J4)",
            ),
            # Scorpius camera ======================================================
            # port A(J1)
            TestStep(
                command=commands[10],
                pre_condition="Please ensure Scorpius camera is connected to port A(J1",
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command=commands[11],
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=commands[12],
                # validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port A(J1)",
                criteria="The camera preview video is displayed on the screen",
                post_check="Is the camera preview video displayed on the screen?",
            ),
            TestStep(
                command=commands[13],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[14],
                validation_func=self._validate_gpio_value_Scorpius,
                timeout=5,
                description="Validate GPIO value of Scorpius camera",
                criteria="The camera type is Scorpius",
            ),
            TestStep(
                command=commands[15],
                timeout=5,
                description="Reset camera port A(J1)",
            ),
            # port B(J4)
            TestStep(
                command=commands[16],
                # validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port B(J4)",
                pre_condition="Please ensure Scorpius camera is connected to port B(J4)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[17],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[18],
                validation_func=self._validate_gpio_value_Scorpius,
                timeout=5,
                description="Validate GPIO value of Scorpius camera",
                criteria="The camera type is Scorpius",
            ),
            TestStep(
                command=commands[19],
                timeout=5,
                description="Reset camera port B(J4)",
            ),

            # MIPI VGA camera ======================================================
            # port A(J1)
            TestStep(
                command=commands[20],
                pre_condition="Please ensure MIPI VGA camera is connected to port A(J1)",
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command=commands[21],
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=commands[22],
                # validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port A(J1)",
                criteria="The camera preview video is displayed on the screen",
                post_check="Is the camera preview video displayed on the screen?",
            ),
            TestStep(
                command=commands[23],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[24],
                validation_func=self._validate_gpio_value_MIPI_VGA,
                timeout=5,
                description="Validate GPIO value of MIPI VGA camera",
                criteria="The camera type is MIPI VGA",
            ),
            TestStep(
                command=commands[25],
                timeout=5,
                description="Reset camera port A(J1)",
            ),
            # port B(J4)
            TestStep(
                command=commands[26],
                # validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port B(J4)",
                pre_condition="Please ensure MIPI VGA camera is connected to port B(J4)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[27],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[28],
                validation_func=self._validate_gpio_value_MIPI_VGA,
                timeout=5,
                description="Validate GPIO value of MIPI VGA camera",
                criteria="The camera type is MIPI VGA",
            ),
            TestStep(
                command=commands[29],
                timeout=5,
                description="Reset camera port B(J4)",
            ),

            # LVDS smart cable ======================================================
            # port A(J1)
            TestStep(
                command=commands[30],
                pre_condition="Please ensure smart cable is connected to port A(J1)",
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command=commands[31],
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=commands[32],
                # validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port A(J1)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
            ),
            TestStep(
                command=commands[33],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[34],
                validation_func=self._validate_gpio_value_smart_cable,
                timeout=5,
                description="Validate GPIO value of smart cable",
                criteria="The camera type is LVDS smart cable",
            ),
            TestStep(
                command=commands[35],
                timeout=5,
                description="Reset camera port A(J1)",
            ),
            # port B(J4)
            TestStep(
                command=commands[36],
                # validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port B(J4)",
                pre_condition="Please ensure smart cable is connected to port B(J4)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[37],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[38],
                validation_func=self._validate_gpio_value_smart_cable,
                timeout=5,
                description="Validate GPIO value of smart cable",
                criteria="The camera type is LVDS smart cable",
            ),
            TestStep(
                command=commands[39],
                timeout=5,
                description="Reset camera port B(J4)",
            ),

            # Jig A and B ======================================================
            # port A(J1)
            TestStep(
                command=commands[40],
                pre_condition="Please ensure Jig A is connected to port A(J1), Jig B is connected to port B(J4)",
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command=commands[41],
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=commands[42],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[43],
                validation_func=self._validate_gpio_value_jig_A,
                timeout=5,
                description="Validate GPIO value of Jig A",
                criteria="The camera type is Jig A",
            ),
            # port B(J4)
            TestStep(
                command=commands[44],
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command=commands[45],
                validation_func=self._validate_gpio_value_jig_B,
                timeout=5,
                description="Validate GPIO value of Jig B",
                criteria="The camera type is Jig B",
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

    def _validate_camera_connection(self, response: str) -> Tuple[bool, str]:
        """
        Validate camera connection
        
        Args:
            response: Device response string
        """
        try:
            if "Error" in response:
                return False, "Error in camera connection"
            # Check if the camera is connected
            if "lcmx02p1_camera" in response or "lcmx02p2_camera" in response:
                return True, "Camera is connected"
            else:
                return False, "Can't find camera"
        
        except Exception as e:
            logger.error(f"exception in validating camera connection: {e}")
            return False, f"exception in validating camera connection: {e}"
    
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
