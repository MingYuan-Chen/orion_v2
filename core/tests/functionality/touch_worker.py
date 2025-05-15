"""
Touch worker module
Implement touch function test for device
"""
from typing import List, Tuple
from util.logger import logger
from core.tests.base_test_worker import BaseTestWorker, TestStep


class TouchWorker(BaseTestWorker):
    """Touch worker, implement touch function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare touch test steps
        
        Returns:
            touch test steps list
        """
        return [
            TestStep(
                command="ts_test_mt -j 2 -v",  
                timeout=5, 
                description="Launch touch test tool",
                post_check="Is test tool running with 'Drag/Draw/Quit' options?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Touch the 9 points",
                pre_condition="Please touch the 9 points on the screen",
                post_check="Is the 9 points touched with cross mark?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Single drag",
                pre_condition="Please Drag by single finger on the screen",
                post_check="Is the cross mark moving on the screen?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Double drag",
                pre_condition="Please Drag by two fingers on the screen",
                post_check="Is the two cross marks moving on the screen?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Drag the edge of the screen",
                pre_condition="Please Drag the edge of the screen",
                post_check="Is the cross mark moving along the edge of the screen?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Drag the screen with water",
                pre_condition="Please Drag the screen with water",
                post_check="Is the cross mark moving on the screen?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Drag the screen by wet finger",
                pre_condition="Please Drag the screen by wet finger",
                post_check="Is the cross mark moving on the screen?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Drag the screen by finger with standard Hospital Grade Surgical Gloves",
                pre_condition="Please Drag the screen by finger with standard Hospital Grade Surgical Gloves",
                post_check="Is the cross mark moving on the screen?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Single draw",
                pre_condition="Please click the draw button and draw by single finger on the screen",
                post_check="Is the line drawn on the screen?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Double draw",
                pre_condition="Please click the draw button and draw by two fingers on the screen",
                post_check="Is the two lines drawn on the screen?"
            ),
            TestStep(
                command="ls",
                timeout=5,
                description="Quit touch test tool",
                pre_condition="Please click the quit button",
                post_check="Is the touch test tool closed?"
            ),

            # reset the device after testing completed ======================================================
            TestStep(
                command="reboot",
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
                command="root",
                timeout=5,
                description="enter password",
            )
        ]

