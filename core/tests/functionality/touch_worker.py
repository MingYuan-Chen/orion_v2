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
                command="",
                timeout=5,
                description="Touch the left top corner",
                criteria="The cross mark should appear on the left top corner of the screen",
                pre_condition="Please touch the left top corner on the screen",
                post_check="Is the left top corner touched with cross mark?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Touch the right top corner",
                criteria="The cross mark should appear on the right top corner of the screen",
                pre_condition="Please touch the right top corner on the screen",
                post_check="Is the right top corner touched with cross mark?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Touch the left bottom corner",
                criteria="The cross mark should appear on the left bottom corner of the screen",
                pre_condition="Please touch the left bottom corner on the screen",
                post_check="Is the left bottom corner touched with cross mark?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Touch the right bottom corner",
                criteria="The cross mark should appear on the right bottom corner of the screen",
                pre_condition="Please touch the right bottom corner on the screen",
                post_check="Is the right bottom corner touched with cross mark?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Touch the center of the screen",
                criteria="The cross mark should appear on the center of the screen",
                pre_condition="Please touch the center of the screen",
                post_check="Is the center of the screen touched with cross mark?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Touch the left center of the screen",
                criteria="The cross mark should appear on the left center of the screen",
                pre_condition="Please touch the left center of the screen",
                post_check="Is the left center of the screen touched with cross mark?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Touch the right center of the screen",
                criteria="The cross mark should appear on the right center of the screen",
                pre_condition="Please touch the right center of the screen",
                post_check="Is the right center of the screen touched with cross mark?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Touch the top center of the screen",
                criteria="The cross mark should appear on the top center of the screen",
                pre_condition="Please touch the top center of the screen",
                post_check="Is the top center of the screen touched with cross mark?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Touch the bottom center of the screen",
                criteria="The cross mark should appear on the bottom center of the screen",
                pre_condition="Please touch the bottom center of the screen",
                post_check="Is the bottom center of the screen touched with cross mark?",
                manual_only=True
            ),
            TestStep(
                command="",
                description="Single drag",
                criteria="The cross mark should move on the screen when a single finger is dragged",
                pre_condition="Please drag with a single finger on the screen",
                post_check="Is the cross mark moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Double drag",
                criteria="Two cross marks should move on the screen when two fingers are dragged",
                pre_condition="Please drag with two fingers on the screen",
                post_check="Are the two cross marks moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Drag the edge of the screen",
                criteria="The cross mark should move along the edge of the screen",
                pre_condition="Please drag along the edge of the screen",
                post_check="Is the cross mark moving along the edge of the screen?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Drag the screen with water",
                criteria="The cross mark should move on the screen even with water present",
                pre_condition="Please drag the screen with water",
                post_check="Is the cross mark moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Drag the screen by wet finger",
                criteria="The cross mark should move on the screen when using a wet finger",
                pre_condition="Please drag the screen with a wet finger",
                post_check="Is the cross mark moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Drag the screen by finger with standard Hospital Grade Surgical Gloves",
                criteria="The cross mark should move on the screen when using finger with surgical gloves",
                pre_condition="Please drag the screen with finger wearing standard Hospital Grade Surgical Gloves",
                post_check="Is the cross mark moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Single draw",
                criteria="A line should be drawn on the screen when drawing with a single finger",
                pre_condition="Please click the draw button and draw with a single finger on the screen",
                post_check="Is the line drawn on the screen?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Double draw",
                criteria="Two lines should be drawn on the screen when drawing with two fingers",
                pre_condition="Please click the draw button and draw with two fingers on the screen",
                post_check="Are the two lines drawn on the screen?",
                manual_only=True
            ),
            TestStep(
                command="",
                timeout=5,
                description="Quit touch test tool",
                pre_condition="Please click the quit button",
                post_check="Is the touch test tool closed?",
                manual_only=True
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
                description="login as root",
            )
        ]

