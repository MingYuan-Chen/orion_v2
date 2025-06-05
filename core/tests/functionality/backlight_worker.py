"""
Backlight worker module
Implement backlight function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class BacklightWorker(BaseTestWorker):
    """Backlight worker, implement backlight function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_backlight"

    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare backlight test steps
        
        Returns:
            backlight test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
            TestStep(
                command=commands[0], 
                timeout=3, 
                description="Set backlight brightness to 0",
            ),
            TestStep(
                command=commands[1], 
                # expected_response="0", 
                timeout=3, 
                description="Check backlight brightness",
                post_check="Is the backlight brightness become to dark?",
                criteria="The backlight brightness is 0%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[2], 
                timeout=3, 
                description="Set backlight brightness to 1",
            ),
            TestStep(
                command=commands[3], 
                # expected_response="1", 
                timeout=3, 
                description="Check backlight brightness 20%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 20%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[4], 
                timeout=3, 
                description="Set backlight brightness to 2",
            ),
            TestStep(
                command=commands[5], 
                # expected_response="2", 
                timeout=3, 
                description="Check backlight brightness 30%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 30%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[6], 
                timeout=3, 
                description="Set backlight brightness to 3",
            ),
            TestStep(
                command=commands[7], 
                # expected_response="3", 
                timeout=3, 
                description="Check backlight brightness 40%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 40%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[8], 
                timeout=3, 
                description="Set backlight brightness to 4",
            ),
            TestStep(
                command=commands[9], 
                # expected_response="4", 
                timeout=3, 
                description="Check backlight brightness 50%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 50%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[10], 
                timeout=3, 
                description="Set backlight brightness to 5",
            ),
            TestStep(
                command=commands[11], 
                # expected_response="5", 
                timeout=3, 
                description="Check backlight brightness 60%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 60%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[12], 
                timeout=3, 
                description="Set backlight brightness to 6",
            ),
            TestStep(
                command=commands[13], 
                # expected_response="6",
                timeout=3, 
                description="Check backlight brightness 80%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 80%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[14], 
                timeout=3, 
                description="Set backlight brightness to 7",
            ),
            TestStep(
                command=commands[15], 
                # expected_response="7",
                timeout=3, 
                description="Check backlight brightness 100%",
                post_check="Is the backlight brighter than before?",
                criteria="The backlight brightness is 100%",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[16], 
                timeout=3, 
                description="Set screen power off",
            ),
            TestStep(
                command=commands[17], 
                # expected_response="1", 
                timeout=3, 
                description="Check screen power",
                post_check="Is the screen power off?",
                criteria="The screen power is off",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[18], 
                timeout=3, 
                description="Set screen power on",
            ),
            TestStep(
                command=commands[19], 
                # expected_response="0",
                timeout=3, 
                description="Check screen power",
                post_check="Is the screen power on?",
                criteria="The screen power is on",
                max_retries=1,
                retry_delay=1000
            )
        ]