"""
Camera worker module
Implement camera function test for device
"""
from typing import List, Tuple
from util.logger import logger
from core.tests.base_test_worker import BaseTestWorker, TestStep


class CameraWorker(BaseTestWorker):
    """Camera worker, implement camera function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.preview_vieo_port = lambda port: f"/unit_tests/mxc_v4l2_overlay.out \\n -iw 1280 -ih 720 -it 0 -il 0 \\n -ow 1280 -oh 800 -ot 0 -ol 0 \\n -di /dev/video{port} -bg -r 1 &"
        self.get_gpio_value = lambda port:f"for i in 0 1 2 3; do cat /sys/class/gpio/vfe{port+1}_blade_det$i/value"
        self.reset_camera = lambda port: f"fuser -k /dev/video{port}"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare camera test steps
        
        Returns:
            camera test steps list
        """
        return [
            # LVDS Camera ======================================================
            # port A(J1)
            TestStep(
                command="reboot",
                pre_condition="Please ensure LVDS camera is connected to port A(J1)",
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command="root",
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=self.preview_vieo_port(0), 
                validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port A(J1)",
                criteria="The camera preview video is displayed on the screen",
                post_check="Is the camera preview video displayed on the screen?",
            ),
            TestStep(
                command=self.get_gpio_value(0),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_lvds,
                timeout=5,
                description="Validate GPIO value of LVDS camera",
                criteria="The GPIO value is 1001",
            ),
            TestStep(
                command=self.reset_camera(0),
                timeout=5,
                description="Reset camera port A(J1)",
            ),
            # port B(J4)
            TestStep(
                command=self.preview_vieo_port(1), 
                validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port B(J4)",
                pre_condition="Please ensure LVDS camera is connected to port B(J4)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.get_gpio_value(1),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_lvds,
                timeout=5,
                description="Validate GPIO value of LVDS camera",
                criteria="The GPIO value is 1001",
            ),
            TestStep(
                command=self.reset_camera(1),
                timeout=5,
                description="Reset camera port B(J4)",
            ),
            # Scorpius camera ======================================================
            # port A(J1)
            TestStep(
                command="reboot",
                pre_condition="Please ensure Scorpius camera is connected to port A(J1",
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command="root",
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=self.preview_vieo_port(0), 
                validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port A(J1)",
                criteria="The camera preview video is displayed on the screen",
                post_check="Is the camera preview video displayed on the screen?",
            ),
            TestStep(
                command=self.get_gpio_value(0),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_Scorpius,
                timeout=5,
                description="Validate GPIO value of Scorpius camera",
                criteria="The GPIO value is 0111",
            ),
            TestStep(
                command=self.reset_camera(0),
                timeout=5,
                description="Reset camera port A(J1)",
            ),
            # port B(J4)
            TestStep(
                command=self.preview_vieo_port(1), 
                validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port B(J4)",
                pre_condition="Please ensure Scorpius camera is connected to port B(J4)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.get_gpio_value(1),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_Scorpius,
                timeout=5,
                description="Validate GPIO value of Scorpius camera",
                criteria="The GPIO value is 0111",
            ),
            TestStep(
                command=self.reset_camera(1),
                timeout=5,
                description="Reset camera port B(J4)",
            ),

            # MIPI VGA camera ======================================================
            # port A(J1)
            TestStep(
                command="reboot",
                pre_condition="Please ensure MIPI VGA camera is connected to port A(J1)",
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command="root",
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=self.preview_vieo_port(0), 
                validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port A(J1)",
                criteria="The camera preview video is displayed on the screen",
                post_check="Is the camera preview video displayed on the screen?",
            ),
            TestStep(
                command=self.get_gpio_value(0),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_MIPI_VGA,
                timeout=5,
                description="Validate GPIO value of MIPI VGA camera",
                criteria="The GPIO value is 1011",
            ),
            TestStep(
                command=self.reset_camera(0),
                timeout=5,
                description="Reset camera port A(J1)",
            ),
            # port B(J4)
            TestStep(
                command=self.preview_vieo_port(1), 
                validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port B(J4)",
                pre_condition="Please ensure MIPI VGA camera is connected to port B(J4)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.get_gpio_value(1),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_MIPI_VGA,
                timeout=5,
                description="Validate GPIO value of MIPI VGA camera",
                criteria="The GPIO value is 1011",
            ),
            TestStep(
                command=self.reset_camera(1),
                timeout=5,
                description="Reset camera port B(J4)",
            ),

            # LVDS smart cable ======================================================
            # port A(J1)
            TestStep(
                command="reboot",
                pre_condition="Please ensure smart cable is connected to port A(J1)",
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command="root",
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=self.preview_vieo_port(0), 
                validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port A(J1)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
            ),
            TestStep(
                command=self.get_gpio_value(0),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_smart_cable,
                timeout=5,
                description="Validate GPIO value of smart cable",
                criteria="The GPIO value is 1111",
            ),
            TestStep(
                command=self.reset_camera(0),
                timeout=5,
                description="Reset camera port A(J1)",
            ),
            # port B(J4)
            TestStep(
                command=self.preview_vieo_port(1), 
                validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port B(J4)",
                pre_condition="Please ensure smart cable is connected to port B(J4)",
                post_check="Is the camera preview video displayed on the screen?",
                criteria="The camera preview video is displayed on the screen",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.get_gpio_value(1),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_smart_cable,
                timeout=5,
                description="Validate GPIO value of smart cable",
                criteria="The GPIO value is 1111",
            ),
            TestStep(
                command=self.reset_camera(1),
                timeout=5,
                description="Reset camera port B(J4)",
            ),

            # Jig A and B ======================================================
            # port A(J1)
            TestStep(
                command="reboot",
                pre_condition="Please ensure Jig A is connected to port A(J1), Jig B is connected to port B(J4)",
                post_check="Is the device rebooted to the login screen?",
                timeout=5,
                description="reboot the device",
            ),
            TestStep(
                command="root",
                timeout=5,
                description="enter user name",
            ),
            TestStep(
                command=self.get_gpio_value(0),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_jig_A,
                timeout=5,
                description="Validate GPIO value of Jig A",
                criteria="The GPIO value is 1000",
            ),
            # port B(J4)
            TestStep(
                command=self.get_gpio_value(1),
                timeout=5,
                description="Get GPIO value",
            ),
            TestStep(
                command="done",
                validation_func=self._validate_gpio_value_jig_B,
                timeout=5,
                description="Validate GPIO value of Jig B",
                criteria="The GPIO value is 0100",
            )
        ]
    
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
            values = response.split("\n")
            values = values[:-1]
            value_str = "".join(values)
            if "1001" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}"
            
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
            values = response.split("\n")
            values = values[:-1]
            value_str = "".join(values)
            if "0111" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}"
            
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
            values = response.split("\n")
            values = values[:-1]
            value_str = "".join(values)
            if "1011" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}"
            
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
            values = response.split("\n")
            values = values[:-1]
            value_str = "".join(values)
            if "1101" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}"
            
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
            values = response.split("\n")
            values = values[:-1]
            value_str = "".join(values)
            if "1111" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}"
            
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
            values = response.split("\n")
            values = values[:-1]
            value_str = "".join(values)
            if "1000" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}"
            
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
            values = response.split("\n")
            values = values[:-1]
            value_str = "".join(values)
            if "0100" in value_str:
                return True, f"GPIO value is {value_str}"
            else:
                return False, f"GPIO value unexpected: {value_str}"
            
        except Exception as e:
            logger.error(f"exception in validating GPIO value: {e}")
            return False, f"exception in validating GPIO value: {e}"
