"""
Audio worker module
Implement audio function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType
import time
import os


class ProbeWorker(BaseTestWorker):
    """Audio worker, implement audio function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_probe"
        self.capture_buffer = ""
        self.config_buffer = ""
        self.config_start_time = None
        self.usb_path = None

    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare probe test steps
        
        Returns:
            probe test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
                TestStep(
                    command=commands[0], 
                    timeout=5, 
                    description="Make root filesystem writable"
                ),
                TestStep(
                    command=commands[1], 
                    timeout=5, 
                    description="Enable the USB Power"
                ),
                TestStep(
                    command=commands[2],
                    timeout=5, 
                    pre_condition="1.Please remove the AC \n2.Plug the Probe",
                    description="Remove the AC and plug the Probe",
                ),
                TestStep(
                    command=commands[3], 
                    timeout=100000, 
                    validation_func=self._validate_check_configuration,
                    description="Check the probe configuration",
                    criteria="The probe can be initialized with the configuration."
                ),
                TestStep(
                    command=commands[4], 
                    timeout=15000, 
                    validation_func=self._validate_probe_capture,
                    description="Capture raw data from Probe",
                    max_retries=2,
                    retry_delay=10000,
                    criteria="The probe can capture 14 planes data."
                ),
                TestStep(
                    command=commands[5], 
                    timeout=10000, 
                    validation_func=self._validate_check_CRC,
                    description="Probe's plans CRC validation",
                    criteria="All 14 planes passed CRC checks.",
                    max_retries=2,
                    retry_delay=3000
                )
        ]
        
    def _validate_check_configuration(self, response: str):
        try:
            # 正常成功的輸出會包含 "Successful"
            # 若出現 "Check sum error" 或其他異常則視為失敗
            if "Configuration complete" in response:
                time.sleep(5)
                return True, "Probe Configuration successfully"
            elif "Configuration failed" in response:
                return False, "Probe Configuration Failed"
            else:
                return False, f"Unexpected probe configuration output: {response.strip()[:100]}"
        except Exception as e:
            return False, f"Error validating probe configuration result: {e}"
    
    def _validate_probe_capture(self, response: str):

        # init timer
        if not hasattr(self, "capture_start_time") or self.capture_start_time is None:
            self.capture_start_time = time.time()
            self.capture_buffer = ""

        # append chunk
        if response:
            logger.debug(f"[ProbeCapture] Chunk: {response.strip()}")
            self.capture_buffer += response.lower()

        # 成功條件
        if "planes saved: 14/14" in self.capture_buffer:
            logger.info("[ProbeCapture] SUCCESS detected.")
            self.capture_start_time = None
            self.capture_buffer = ""
            return True, "Probe capture completed."

        # 尚未收完 → 必須等至少 2 秒讓兩段 output 到齊
        if time.time() - self.capture_start_time < 2:
            return None, "Waiting full probe capture output..."

        # 錯誤
        if "error" in self.capture_buffer:
            msg = self.capture_buffer
            self.capture_start_time = None
            self.capture_buffer = ""
            return False, msg

        # timeout（10 秒）
        if time.time() - self.capture_start_time > 10:
            msg = self.capture_buffer
            self.capture_start_time = None
            self.capture_buffer = ""
            return False, f"Probe capture timeout: {msg}"

        return None, "Waiting..."


    def _validate_check_CRC(self, response: str) -> Tuple[bool, str]:
        """
        Validate CRC check result from Probe raw data test
        """
        try:
            # 正常成功的輸出會包含 "Successful"
            # 若出現 "Check sum error" 或其他異常則視為失敗
            if "Check Sum Successful" in response:
                return True, "14 planes CRC check passed"
            elif "Check Sum Error" in response:
                return False, "CRC check failed: checksum mismatch detected"
            else:
                return False, f"Unexpected CRC check output: {response.strip()[:100]}"
        except Exception as e:
            return False, f"Error validating CRC check result: {e}"