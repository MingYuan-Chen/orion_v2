"""
Touch worker module
Implement touch function test for device
"""
from typing import List, Tuple
from util.logger import logger
from core.tests.base_test_worker import BaseTestWorker, TestStep
from core.models.platform_command_set import CommandType

class TouchWorker(BaseTestWorker):
    """Touch worker, implement touch function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_touch"
        self.touch_tool_path = None
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare touch test steps
        
        Returns:
            touch test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
            TestStep(
                command=commands[0],  
                timeout=5,
                description="Launch touch test tool on usb 1",
            ),
            TestStep(
                command=commands[1],  
                timeout=5,
                description="Launch touch test tool on usb 2",
            ),
            TestStep(
                command=commands[2],
                timeout=5,
                description="Touch the 9 red circles",
                criteria="The 9 red circles should become green",
                pre_condition="Please touch the 9 red circles on the screen",
                post_check="Is the 9 red circles become green? \n NOTE: Please click 'Close' button after testing",
                manual_only=True
            ),
            TestStep(
                command=commands[3],  
                timeout=5,
                description="Launch touch test tool",
            ),
            TestStep(
                command=commands[4],
                description="Single drag",
                criteria="The cross mark should move on the screen when a single finger is dragged",
                pre_condition="Please drag with a single finger on the screen",
                post_check="Is the cross mark moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command=commands[5],
                timeout=5,
                description="Double drag",
                criteria="Two cross marks should move on the screen when two fingers are dragged",
                pre_condition="Please drag with two fingers on the screen",
                post_check="Are the two cross marks moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command=commands[6],
                timeout=5,
                description="Drag the edge of the screen",
                criteria="The cross mark should move along the edge of the screen",
                pre_condition="Please drag along the edge of the screen",
                post_check="Is the cross mark moving along the edge of the screen?",
                manual_only=True
            ),
            TestStep(
                command=commands[7],
                timeout=5,
                description="Drag the screen with water",
                criteria="The cross mark should move on the screen even with water present",
                pre_condition="Please drag the screen with water",
                post_check="Is the cross mark moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command=commands[8],
                timeout=5,
                description="Drag the screen by wet finger",
                criteria="The cross mark should move on the screen when using a wet finger",
                pre_condition="Please drag the screen with a wet finger",
                post_check="Is the cross mark moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command=commands[9],
                timeout=5,
                description="Drag the screen by finger with standard Hospital Grade Surgical Gloves",
                criteria="The cross mark should move on the screen when using finger with surgical gloves",
                pre_condition="Please drag the screen with finger wearing standard Hospital Grade Surgical Gloves",
                post_check="Is the cross mark moving on the screen?",
                manual_only=True
            ),
            TestStep(
                command=commands[10],
                timeout=5,
                description="Single draw",
                criteria="A line should be drawn on the screen when drawing with a single finger",
                pre_condition="Please click the draw button and draw with a single finger on the screen",
                post_check="Is the line drawn on the screen?",
                manual_only=True
            ),
            TestStep(
                command=commands[11],
                timeout=5,
                description="Double draw",
                criteria="Two lines should be drawn on the screen when drawing with two fingers",
                pre_condition="Please click the draw button and draw with two fingers on the screen",
                post_check="Are the two lines drawn on the screen?",
                manual_only=True
            ),
            TestStep(
                command=commands[12],
                timeout=5,
                description="Quit touch test tool",
                pre_condition="Please click the quit button",
                post_check="Is the touch test tool closed?",
                manual_only=True
            )
        ]

