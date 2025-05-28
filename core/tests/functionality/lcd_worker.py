"""
LCD worker module
Implement LCD function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class LcdWorker(BaseTestWorker):
    """Lcd worker, implement lcd function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.set_color = lambda color: f"/unit_tests/drawfb.out {color}"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare lcd test steps
        
        Returns:
            lcd test steps list
        """
        return [
            TestStep(
                command=self.set_color("red"), 
                # validation_func=self._validate_red_color, 
                timeout=5, 
                description="Validate red color",
                post_check="Is the LCD display red?",
                criteria="Screen display a red color",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("green"), 
                # validation_func=self._validate_green_color, 
                timeout=5, 
                description="Validate green color",
                post_check="Is the LCD display green?",
                criteria="Screen display a green color",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("blue"), 
                # validation_func=self._validate_blue_color, 
                timeout=5, 
                description="Validate blue color",
                post_check="Is the LCD display blue?",
                criteria="Screen display a blue color",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("black"), 
                # validation_func=self._validate_black_color, 
                timeout=5, 
                description="Validate black color",
                post_check="Is the LCD display black?",
                criteria="Screen display a black color",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("white"), 
                # validation_func=self._validate_white_color, 
                timeout=5, 
                description="Validate white color",
                post_check="Is the LCD display white?",
                criteria="Screen display a white color",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("colorbar"), 
                # validation_func=self._validate_colorbar, 
                timeout=5, 
                description="Validate colorbar",
                post_check="Is the LCD display colorbar?",
                criteria="Screen display a colorbar",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("gradient"), 
                # validation_func=self._validate_gradient, 
                timeout=5, 
                description="Validate gradient",
                post_check="Is the LCD display gradient?",
                criteria="Screen display a gradient",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("frame"), 
                # validation_func=self._validate_frame, 
                timeout=5, 
                description="Validate frame",
                post_check="Is the LCD display frame?",
                criteria="Screen display a frame",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("gray16"), 
                # validation_func=self._validate_gray16, 
                timeout=5, 
                description="Validate gray16",
                post_check="Is the LCD display gray16?",
                criteria="Screen display a gray16 color",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("gray64"), 
                # validation_func=self._validate_gray64, 
                timeout=5, 
                description="Validate gray64",
                post_check="Is the LCD display gray64?",
                criteria="Screen display a gray64 color",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=self.set_color("gray256"), 
                # validation_func=self._validate_gray256, 
                timeout=5, 
                description="Validate gray256",
                post_check="Is the LCD display gray256?",
                criteria="Screen display a gray256 color",
                max_retries=1,
                retry_delay=500
            )
        ]
    
    def _validate_red_color(self, response: str) -> Tuple[bool, str]:
        """Validate red color"""

        if "successfully" not in response and "color : red" not in response:
            return False, "Failed to validate red color"
        return True, "Red color validated successfully"
    
    def _validate_green_color(self, response: str) -> Tuple[bool, str]:
        """Validate green color"""
        if "successfully" not in response and "color : green" not in response:
            return False, "Failed to validate green color"
        return True, "Green color validated successfully"
    
    def _validate_blue_color(self, response: str) -> Tuple[bool, str]:
        """Validate blue color"""
        if "successfully" not in response and "color : blue" not in response:
            return False, "Failed to validate blue color"
        return True, "Blue color validated successfully"
    
    def _validate_black_color(self, response: str) -> Tuple[bool, str]:
        """Validate black color"""
        if "successfully" not in response and "color : black" not in response:
            return False, "Failed to validate black color"
        return True, "Black color validated successfully"
    
    def _validate_white_color(self, response: str) -> Tuple[bool, str]:
        """Validate white color"""
        if "successfully" not in response and "color : white" not in response:
            return False, "Failed to validate white color"
        return True, "White color validated successfully"

    def _validate_colorbar(self, response: str) -> Tuple[bool, str]:
        """Validate colorbar"""
        if "successfully" not in response and "colorbar" not in response:
            return False, "Failed to validate colorbar"
        return True, "Colorbar validated successfully"

    def _validate_gradient(self, response: str) -> Tuple[bool, str]:
        """Validate gradient"""
        if "successfully" not in response and "gradient" not in response:
            return False, "Failed to validate gradient"
        return True, "Gradient validated successfully"
    
    def _validate_frame(self, response: str) -> Tuple[bool, str]:
        """Validate frame"""
        # Frame command should produce screen info and draw output
        if ("Screen info" in response or "successfully" in response) and "Draw" in response:
            return True, "Frame validated successfully"
        return False, "Failed to validate frame"
    
    def _validate_gray16(self, response: str) -> Tuple[bool, str]:
        """Validate gray16"""
        if "successfully" not in response and "gray16" not in response:
            return False, "Failed to validate gray16"
        return True, "Gray16 validated successfully"
    
    def _validate_gray64(self, response: str) -> Tuple[bool, str]:
        """Validate gray64"""
        if "successfully" not in response and "gray64" not in response:
            return False, "Failed to validate gray64"
        return True, "Gray64 validated successfully"
    
    def _validate_gray256(self, response: str) -> Tuple[bool, str]:
        """Validate gray256"""
        if "successfully" not in response and "gray256" not in response:
            return False, "Failed to validate gray256"
        return True, "Gray256 validated successfully"
