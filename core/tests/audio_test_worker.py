"""
USB ports test worker module
Implement USB port function test for device
"""
from typing import List, Tuple
import logging
from .base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class AudioTestWorker(BaseTestWorker):
    """Audio test worker, implement audio function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True):
        super().__init__(device_worker, continue_on_failure)
    
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
                max_retries=1,           # Maximum retries 1 time
                retry_delay=500          # 0.5 seconds later retry
            ),
            TestStep(
                command="arecord -l", 
                expected_response="sgtl5000audio", 
                timeout=10, 
                description="Check microphone device",
                max_retries=3,           # Read operation may need multiple attempts
                retry_delay=1000         # 1 second later retry
            ),
            TestStep(
                command="arecord -f cd -d 10 mic.wav", 
                validation_func=self._validate_microphone_record,
                timeout=10, 
                description="Record from microphone",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            ),
            TestStep(
                command="aplay mic.wav", 
                validation_func=self._validate_speaker_playback,
                timeout=10, 
                description="Playback from speaker",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            ),
            TestStep(
                command="rm -f mic.wav",
                timeout=10, 
                description="Remove microphone recording",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            ),
            TestStep(
                command="ls /unit_tests/audio8k16S.wav", 
                expected_response="audio8k16S.wav",
                timeout=10, 
                description="Check audio8k16S.wav exists",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            ),
            TestStep(
                command="aplay /unit_tests/audio8k16S.wav", 
                validation_func=self._validate_speaker_playback_8k16s,
                timeout=10, 
                description="Playback from speaker",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            )
        ]
    
    def _validate_microphone_record(self, response: str) -> Tuple[bool, str]:
        """
        Validate microphone record
        """
        try:
            if "Signed 16 bit" in response and "44100 Hz" in response:
                return True, "Microphone recording cd format is successful"
            else:
                return False, "Unexpected microphone recording format"
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
    
    def _validate_speaker_playback_8k16s(self, response: str) -> Tuple[bool, str]:
        """
        Validate speaker playback 8k16s
        """
        try:
            if "Playing WAVE" in response and "audio8k16S.wav" in response:
                return True, "Speaker playback 8k16s is successful"
            else:
                return False, "Unexpected speaker playback 8k16s"
        except Exception as e:
            return False, f"Error validating speaker playback 8k16s: {e}"
