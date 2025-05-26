"""
Backlight worker module
Implement backlight function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class BacklightWorker(BaseTestWorker):
    """Backlight worker, implement backlight function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        # brightness level: 0-7
        self.set_backlight_brightness = lambda level: f"echo {level} > /sys/class/backlight/backlight/brightness"
        self.get_backlight_brightness = "cat /sys/class/backlight/backlight/brightness"
        # screen power:= 0-1
        self.set_screen_power = lambda power: f"echo {power} > /sys/class/backlight/backlight/bl_power"
        self.get_screen_power = "cat /sys/class/backlight/backlight/bl_power"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare backlight test steps
        
        Returns:
            backlight test steps list
        """
        return [
            TestStep(
                command=self.set_backlight_brightness(0), 
                timeout=3, 
                description="Set backlight brightness to 0",
            ),
            TestStep(
                command=self.get_backlight_brightness, 
                expected_response="0", 
                timeout=3, 
                description="Check backlight brightness",
                post_check="Is the backlight brightness become to dark?",
                criteria="The backlight brightness is 0%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=self.set_backlight_brightness(1), 
                timeout=3, 
                description="Set backlight brightness to 1",
            ),
            TestStep(
                command=self.get_backlight_brightness, 
                expected_response="1", 
                timeout=3, 
                description="Check backlight brightness 20%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 20%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=self.set_backlight_brightness(2), 
                timeout=3, 
                description="Set backlight brightness to 2",
            ),
            TestStep(
                command=self.get_backlight_brightness, 
                expected_response="2", 
                timeout=3, 
                description="Check backlight brightness 30%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 30%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=self.set_backlight_brightness(3), 
                timeout=3, 
                description="Set backlight brightness to 3",
            ),
            TestStep(
                command=self.get_backlight_brightness, 
                expected_response="3", 
                timeout=3, 
                description="Check backlight brightness 40%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 40%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=self.set_backlight_brightness(4), 
                timeout=3, 
                description="Set backlight brightness to 4",
            ),
            TestStep(
                command=self.get_backlight_brightness, 
                expected_response="4", 
                timeout=3, 
                description="Check backlight brightness 50%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 50%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=self.set_backlight_brightness(5), 
                timeout=3, 
                description="Set backlight brightness to 5",
            ),
            TestStep(
                command=self.get_backlight_brightness, 
                expected_response="5", 
                timeout=3, 
                description="Check backlight brightness 60%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 60%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=self.set_backlight_brightness(6), 
                timeout=3, 
                description="Set backlight brightness to 6",
            ),
            TestStep(
                command=self.get_backlight_brightness, 
                expected_response="6",
                timeout=3, 
                description="Check backlight brightness 80%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 80%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=self.set_backlight_brightness(7), 
                timeout=3, 
                description="Set backlight brightness to 7",
            ),
            TestStep(
                command=self.get_backlight_brightness, 
                expected_response="7",
                timeout=3, 
                description="Check backlight brightness 100%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 100%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=self.set_screen_power(1), 
                timeout=3, 
                description="Set screen power off",
            ),
            TestStep(
                command=self.get_screen_power, 
                expected_response="1", 
                timeout=3, 
                description="Check screen power",
                post_check="Is the screen power off?",
                criteria="The screen power is off",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=self.set_screen_power(0), 
                timeout=3, 
                description="Set screen power on",
            ),
            TestStep(
                command=self.get_screen_power, 
                expected_response="0",
                timeout=3, 
                description="Check screen power",
                post_check="Is the screen power on?",
                criteria="The screen power is on",
                max_retries=1,
                retry_delay=1000
            )
        ]