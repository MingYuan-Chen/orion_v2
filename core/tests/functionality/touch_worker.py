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
        if self.platform_name == "odin":
            return [
                TestStep(
                        command=commands[0], 
                        timeout=5, 
                        description="Make root filesystem writable"
                    ),
                TestStep(
                    command=commands[1], 
                    timeout=5, 
                    description="Stop Weston from auto-starting on boot"
                ),
                TestStep(
                        command=commands[2], 
                        timeout=5, 
                        description="Reboot system to apply Weston disable"
                    ),
                TestStep(
                    command=commands[3], 
                    timeout=5, 
                    description="Enable USB ports power"
                ),
                TestStep(
                    command=commands[4], 
                    timeout=5, 
                    description="Mount USB storage device"
                ),
                TestStep(
                    command=commands[5],
                    timeout=5,
                    description="Touch the 9 red circles",
                    criteria="The 9 red circles should become green",
                    pre_condition="Please touch the 9 red circles on the screen",
                    post_check='1.Please click "Close" button on Panel. \n2.Have the 9 red circles turned green?',
                    manual_only=True
                ),
                TestStep(
                    command=commands[6],  
                    timeout=5,
                    description="Launch ts_test_mt",
                ),
                TestStep(
                    command=commands[7],
                    description="Draw along the edge of the screen with Single & double draw",
                    criteria="A line should be drawn along on the screen when drawing with a single finger and double finger",
                    pre_condition='1.Please click the "Draw" "button \n2.Draw along the edge of the screen with a single and double fingers on the screen',
                    post_check="Can the line be drawn along the edge of the screen?",
                    manual_only=True
                ),
                TestStep(
                    command=commands[8],
                    timeout=5,
                    description="Quit touch test tool",
                    pre_condition='Please click the "Quit" button',
                    post_check="Is the touch test tool closed?",
                    manual_only=True
                ),
                TestStep(
                    command=commands[9],
                    timeout=5,
                    description="Enable the Weston service",
                )
            ]
        else:
            return [
                TestStep(
                    command=commands[0],  
                    timeout=5,
                    description="Launch touch test tool",
                ),
                TestStep(
                    command=commands[1],
                    timeout=5,
                    description="Touch the 9 red circles",
                    criteria="The 9 red circles should become green",
                    pre_condition="Please touch the 9 red circles on the screen",
                    post_check="Is the 9 red circles become green? \n NOTE: Please click 'Close' button on Panel before you click PASS/FAIL button",
                    manual_only=True
                ),
                TestStep(
                    command=commands[2],  
                    timeout=5,
                    description="Launch ts_test_mt",
                ),
                TestStep(
                    command=commands[3],
                    description="Single draw",
                    criteria="A line should be drawn on the screen when drawing with a single finger",
                    pre_condition="Please click the draw button and draw with a single finger on the screen",
                    post_check="Is the line drawn on the screen?",
                    manual_only=True
                ),
                TestStep(
                    command=commands[4],
                    timeout=5,
                    description="Double draw",
                    criteria="Two lines should be drawn on the screen when drawing with two fingers",
                    pre_condition="Please click the draw button and draw with two fingers on the screen",
                    post_check="Are the two lines drawn on the screen?",
                    manual_only=True
                ),
                TestStep(
                    command=commands[5],
                    timeout=5,
                    description="Draw along the edge of the screen",
                    criteria="A line should be drawn along the edge of the screen",
                    pre_condition="Please click the draw button and draw along the edge of the screen",
                    post_check="Is the line drawn along the edge of the screen?",
                    manual_only=True
                ),
                TestStep(
                    command=commands[6],
                    timeout=5,
                    description="Draw with wet finger",
                    criteria="A line should be drawn on the screen even with wet finger",
                    pre_condition="Please click the draw button and draw with a wet finger on the screen",
                    post_check="Is the line drawn on the screen?",
                    manual_only=True
                ),
                TestStep(
                    command=commands[7],
                    timeout=5,
                    description="Draw with wet finger",
                    criteria="A line should be drawn on the screen even with wet finger",
                    pre_condition="Please click the draw button and draw with a wet finger on the screen",
                    post_check="Is the line drawn on the screen?",
                    manual_only=True
                ),
                TestStep(
                    command=commands[8],
                    timeout=5,
                    description="Draw the screen by finger with standard Hospital Grade Surgical Gloves",
                    criteria="A line should be drawn on the screen when using finger with surgical gloves",
                    pre_condition="Please click the draw button and draw with finger wearing standard Hospital Grade Surgical Gloves",
                    post_check="Is the line drawn on the screen?",
                    manual_only=True
                ),
                TestStep(
                    command=commands[9],
                    timeout=5,
                    description="Quit touch test tool",
                    pre_condition="Please click the quit button",
                    post_check="Is the touch test tool closed?",
                    manual_only=True
                )
            ]

