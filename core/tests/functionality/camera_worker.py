"""
Camera worker module
Implement camera function test for device
"""
from typing import List, Tuple
import logging
from core.tests.base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class CameraWorker(BaseTestWorker):
    """Camera worker, implement camera function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
        self.preview_vieo_port = lambda port: f"/unit_tests/mxc_v4l2_overlay.out \\n -iw 1280 -ih 720 -it 0 -il 0 \\n -ow 1280 -oh 800 -ot 0 -ol 0 \\n -di /dev/video{port} -bg -r 1 &"
        self.get_gpio_value = f"for i in 0 1 2 3; do cat vfe1_blade_det$i/value; done"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare camera test steps
        
        Returns:
            camera test steps list
        """
        return [
            TestStep(
                command=self.preview_vieo_port(1), 
                validation_func=self._validate_camera_connection,
                timeout=5, 
                description="Preview video on port 1",
                pre_condition="Please ensure LVDS camera is connected to port 1",
                post_check="Is the camera preview video displayed on the screen?",
                max_retries=1,
                retry_delay=500
            )
        ]
    
    def _validate_camera_connection(self, response: str) -> Tuple[bool, str]:
        """
        Validate camera connection
        
        Args:
            response: Device response string
        """
        try:
            # Check if the camera is connected
            if "width = 1280" in response and "height = 800" in response:
                return True, "Camera is connected"
            else:
                return False, "Camera is not connected"
        
        except Exception as e:
            logger.error(f"exception in validating camera connection: {e}")
            return False, f"exception in validating camera connection: {e}"
