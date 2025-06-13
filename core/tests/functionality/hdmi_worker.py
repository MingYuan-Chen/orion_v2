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
        return [
            # Step 1: Enable HDMI display
            TestStep(
                command="echo 0 > /sys/class/graphics/fb2/blank",
                timeout=5,
                description="Enable HDMI display",
            ),
            
            # Step 2: Backup original display config
            # TestStep(
            #     command="cp /usr/share/imx_6q_display_config /usr/share/imx_6q_display_config.backup",
            #     timeout=5,
            #     description="Backup original display configuration",
            #     criteria="Original configuration should be backed up successfully",
            #     validation_func=self._validate_backup_config,
            #     max_retries=1,
            #     retry_delay=500
            # ),
            
            # Step 3: Modify display config for dual display mode
            # TestStep(
            #     command="cd /usr/share && echo 'ldb=sin0' > imx_6q_display_config && echo 'hdmi=1920x1080M@60' >> imx_6q_display_config",
            #     timeout=10,
            #     description="Configure dual display mode",
            #     criteria="Display configuration should be modified for dual display",
            #     validation_func=self._validate_config_modification,
            #     max_retries=1,
            #     retry_delay=500
            # ),
            
            # Step 4: Verify display configuration
            # TestStep(
            #     command="cat /usr/share/imx_6q_display_config",
            #     timeout=5,
            #     description="Verify display configuration",
            #     criteria="Configuration should contain dual display settings",
            #     validation_func=self._validate_display_config,
            #     max_retries=1,
            #     retry_delay=500
            # ),
            
            # Step 7: Start video playback with dual display
            TestStep(
                command="",
                timeout=5,
                description="Check required conditions",
                pre_condition="Please ensure:\n1. HDMI cable is connected\n2. External display is powered on\n3. Display shows desktop or signal\n4. Only one USB drive has 'demo.mp4' file\n (unexpected errors may occur if both USB drives have the file)",
                manual_only=True,
            ),

            # Step 7: Start video playback with dual display
            TestStep(
                command='gst-launch-1.0 playbin uri=file:///run/media/sda1/demo.mp4 video-sink="overlaysink display-master=true display-slave=true" &',
                timeout=10,
                description="Start HDMI video playback in sda1",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command='gst-launch-1.0 playbin uri=file:///run/media/sdb1/demo.mp4 video-sink="overlaysink display-master=true display-slave=true" &',
                timeout=10,
                description="Start HDMI video playback in sdb1",
                max_retries=1,
                retry_delay=1000
            ),

            TestStep(
                command="",
                timeout=5,
                description="Check video playback on both displays",
                post_check="Can you see the video playing on both displays?\n- LCD display shows video\n- HDMI display shows video\n- Video quality is good\n- Audio is synchronized",
                criteria="Video playback should play correctly on both displays with good quality",
                manual_only=True,
            ),
            
            # Step 11: Stop video playback
            TestStep(
                command="pkill -f gst-launch",
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