"""
Audio worker module
Implement audio function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class AudioWorker(BaseTestWorker):
    """Audio worker, implement audio function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_audio"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare audio test steps
        
        Returns:
            audio test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
            TestStep(
                command=commands[0], 
                timeout=10, 
                description="Set speaker volume to 100%",
                max_retries=2,
                retry_delay=500
            ),
            TestStep(
                command=commands[1], 
                timeout=10, 
                description="Play audio from speaker and record from microphone",
                post_check="Is the audio played from the speaker?",
                criteria="Recording from microphone is successful",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command=commands[2], 
                timeout=10, 
                description="Play the recorded audio from the speaker",
                post_check="Is the audio played from the speaker?",
                criteria="Speaker playback is successful",
                max_retries=2,
                retry_delay=1500
            ), 
            TestStep(
                command=commands[3],
                timeout=10, 
                description="Remove microphone recording",
                max_retries=2,
                retry_delay=1500
            )
        ]
    
    def _validate_microphone_record(self, response: str) -> Tuple[bool, str]:
        """
        Validate microphone record
        """
        try:
            if "Recording WAVE" in response and "Playing WAVE" in response:
                return True, "Microphone recording cd format is successful"
            else:
                return False, "Unexpected microphone recording"
        except Exception as e:
            return False, f"Error validating microphone record: {e}"
    
    def _validate_speaker_playback(self, response: str) -> Tuple[bool, str]:
        """
        Validate speaker playback
        """
        try:
            if "Playing WAVE" in response and "mic.wav" in response:
                return True, "Speaker playback is successful"
            else:
                return False, "Unexpected speaker playback"
        except Exception as e:
            return False, f"Error validating speaker playback: {e}"