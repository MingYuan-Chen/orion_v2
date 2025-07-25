"""
HDMI worker module
Implement HDMI function test for device
"""
from typing import List, Tuple
from util.logger import logger
from core.tests.base_test_worker import BaseTestWorker, TestStep
from core.models.platform_command_set import CommandType

class HdmiWorker(BaseTestWorker):
    """Hdmi worker, implement HDMI function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_hdmi"
        self.video_file_path = "/run/media/sda1/demo.mp4"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare HDMI test steps
        
        Returns:
            HDMI test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
            # Step 1: Enable HDMI display
            TestStep(
                command=commands[0],
                timeout=5,
                description="Enable HDMI display",
            ),
            
            # Step 7: Start video playback with dual display
            TestStep(
                command=commands[1],
                timeout=5,
                description="Check required conditions",
                pre_condition="Please ensure:\n1. HDMI cable is connected\n2. External display is powered on\n3. Display shows desktop or signal\n4. Only one USB drive has 'demo.mp4' file\n (unexpected errors may occur if both USB drives have the file)",
                manual_only=True,
            ),

            # Step 7: Start video playback with dual display
            TestStep(
                command=commands[2],
                timeout=10,
                description="Start HDMI video playback in sda1",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[3],
                timeout=10,
                description="Start HDMI video playback in sdb1",
                max_retries=1,
                retry_delay=1000
            ),

            TestStep(
                command=commands[4],
                timeout=5,
                description="Check video playback on both displays",
                post_check="Can you see the video playing on both displays?\n- LCD display shows video\n- HDMI display shows video\n- Video quality is good\n- Audio is synchronized",
                criteria="Video playback should play correctly on both displays with good quality",
                manual_only=True,
            ),
            
            # Step 11: Stop video playback
            TestStep(
                command=commands[5],
                timeout=10,
                description="Stop video playback",
            )
            
            # Step 12: Restore original display configuration
            # TestStep(
            #     command="cp /usr/share/imx_6q_display_config.backup /usr/share/imx_6q_display_config",
            #     timeout=5,
            #     description="Restore original display configuration",
            #     criteria="Original configuration should be restored",
            #     validation_func=self._validate_config_restore,
            #     max_retries=1,
            #     retry_delay=500
            # ),
            
            # # Step 13: Clean up backup file
            # TestStep(
            #     command="rm -f /usr/share/imx_6q_display_config.backup",
            #     timeout=5,
            #     description="Clean up backup configuration file",
            #     criteria="Backup file should be removed",
            #     validation_func=self._validate_cleanup,
            #     max_retries=1,
            #     retry_delay=500
            # )
        ]