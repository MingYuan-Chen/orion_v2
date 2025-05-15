"""
Audio worker module
Implement audio function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger

class AudioWorker(BaseTestWorker):
    """Audio worker, implement audio function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare audio test steps
        
        Returns:
            audio test steps list
        """
        return [
            TestStep(
                command="aplay -l", 
                expected_response="sgtl5000audio", 
                timeout=5, 
                description="Check speaker device",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command="arecord -l", 
                expected_response="sgtl5000audio", 
                timeout=10, 
                description="Check microphone device",
                max_retries=3,
                retry_delay=1000
            ),
            TestStep(
                command="ls /unit_tests/audio8k16S.wav", 
                expected_response="audio8k16S.wav",
                timeout=10, 
                description="Check audio8k16S.wav exists",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command="amixer -c 0 set PCM 100%", 
                timeout=10, 
                description="Set speaker volume to 100%",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command="(aplay /unit_tests/audio8k16S.wav &) && arecord -f cd mic.wav -d 10", 
                validation_func=self._validate_microphone_record,
                timeout=10, 
                description="Play audio from speaker and record from microphone",
                post_check="Is the audio played from the speaker?",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command="aplay mic.wav", 
                validation_func=self._validate_speaker_playback,
                timeout=10, 
                description="Play the recorded audio from the speaker",
                post_check="Is the audio played from the speaker?",
                max_retries=2,
                retry_delay=1500
            ), 
            TestStep(
                command="rm -f mic.wav",
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