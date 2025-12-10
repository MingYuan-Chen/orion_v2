"""
SD card worker module
Implement SD card function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class SDcardWorker(BaseTestWorker):
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_SDcard"
        self.sd_write_speed_threshold = 30.0  # unit: MB/s
        self.sd_read_speed_threshold = 200.0  # unit: MB/s
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare SD card test steps
        
        Returns:
            SD card test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
            TestStep(
                command=commands[0], 
                timeout=5, 
                post_check=f'Please check SD card is inserted',
                description="Check the SD card is inserted by tester"
            ),
            TestStep(
                command=commands[1], 
                timeout=10, 
                description="Create mount point /run/media/sdcard and mount the SD card",
            ),
            TestStep(
                command=commands[2], 
                timeout=5, 
                description="Make SD card filesystem writable"
            ),
            TestStep(
                command=commands[3], 
                timeout=10, 
                validation_func=self._validate_sd_write,
                description="Write a 200 MB sd_throughput test file to the SD card and check write speed",
                criteria=f"Write speed > {self.sd_write_speed_threshold} MB/s",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command=commands[4], 
                timeout=10, 
                validation_func=self._validate_sd_read,
                description="Read from sd_throughput and check the read speed",
                criteria=f"Read speed > {self.sd_read_speed_threshold} MB/s",
                max_retries=2,
                retry_delay=1500
            ), 
            TestStep(
                command=commands[5],
                timeout=10, 
                description="Remove the test file to clean up",
                max_retries=2,
                retry_delay=1500
            )
        ]
    
    def _validate_sd_write(self, response: str) -> Tuple[bool, str]:
        """
        Validate SD card write test result, parse write speed and determine if it meets the requirement
        
        Args:
            response: command response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            logger.info(f"Start validating SD card write speed: {response}")
            
            if not response or response.strip() == "":
                return False, "SD card write test failed, response is empty"
                
            if "copied" not in response:
                return False, "SD card write test failed, 'copied' not found"
                
            # use regex to extract write speed
            import re
            # match various formats of speed values, including GB/s and MB/s
            speed_pattern = r'(\d+\.?\d*)\s+(MB/s|MiB/s|M/s|GB/s|GiB/s|G/s)'
            speed_match = re.search(speed_pattern, response)
            
            if not speed_match:
                # try to find all possible parts containing speed for diagnosis
                lines = response.split("\n")
                copied_line = next((line for line in lines if "copied" in line), "")
                logger.warning(f"Cannot match speed value, line containing 'copied': {copied_line}")
                return False, f"SD card write test failed, cannot parse write speed. Line containing 'copied': {copied_line}"
                
            # extract speed value and unit
            speed_value = float(speed_match.group(1))
            speed_unit = speed_match.group(2)
            
            # convert to MB/s for comparison
            if speed_unit in ['GB/s', 'GiB/s', 'G/s']:
                write_speed_mb = speed_value * 1024  # convert GB to MB
                logger.info(f"Extracted write speed: {speed_value} {speed_unit} = {write_speed_mb} MB/s")
            else:
                write_speed_mb = speed_value
                logger.info(f"Extracted write speed: {write_speed_mb} MB/s")
            
            # use configured threshold to determine
            threshold = self.sd_write_speed_threshold
            logger.info(f"Speed threshold: {threshold} MB/s")
            
            if write_speed_mb >= threshold:
                logger.info(f"SD card write speed test passed: {write_speed_mb} MB/s > {threshold} MB/s")
                return True, f"SD card write test passed, write speed: {speed_value} {speed_unit} ({write_speed_mb} MB/s) > {threshold} MB/s"
            else:
                logger.warning(f"SD card write speed test failed: {write_speed_mb} MB/s < {threshold} MB/s")
                return False, f"SD card write test failed, write speed: {speed_value} {speed_unit} ({write_speed_mb} MB/s) < {threshold} MB/s"
                
        except Exception as e:
            logger.error(f"SD card write validation error: {str(e)}", exc_info=True)
            # add more diagnosis information
            diag_info = "N/A"
            try:
                if response:
                    lines = response.split("\n")
                    copied_lines = [line for line in lines if "copied" in line]
                    diag_info = ", ".join(copied_lines) if copied_lines else response[:100]
            except:
                pass
            return False, f"SD card write validation error: {str(e)}, related response content: {diag_info}"

    def _validate_sd_read(self, response: str) -> Tuple[bool, str]:
        """
        Validate SD card read test result, parse read speed and determine if it meets the requirement
        
        Args:
            response: command response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            logger.info(f"Start validating SD card read speed: {response}")
            
            if not response or response.strip() == "":
                return False, "SD card read test failed, response is empty"
                
            if "copied" not in response:
                return False, "SD card read test failed, 'copied' not found"
                
            # use regex to extract read speed
            import re
            # match various formats of speed values, including GB/s and MB/s
            speed_pattern = r'(\d+\.?\d*)\s+(MB/s|MiB/s|M/s|GB/s|GiB/s|G/s)'
            speed_match = re.search(speed_pattern, response)
            
            if not speed_match:
                # try to find all possible parts containing speed for diagnosis
                lines = response.split("\n")
                copied_line = next((line for line in lines if "copied" in line), "")
                logger.warning(f"Cannot match speed value, line containing 'copied': {copied_line}")
                return False, f"SD card read test failed, cannot parse read speed. Line containing 'copied': {copied_line}"
                
            # extract speed value and unit
            speed_value = float(speed_match.group(1))
            speed_unit = speed_match.group(2)
            
            # convert to MB/s for comparison
            if speed_unit in ['GB/s', 'GiB/s', 'G/s']:
                read_speed_mb = speed_value * 1024  # convert GB to MB
                logger.info(f"Extracted read speed: {speed_value} {speed_unit} = {read_speed_mb} MB/s")
            else:
                read_speed_mb = speed_value
                logger.info(f"Extracted read speed: {read_speed_mb} MB/s")
            
            # use configured threshold to determine
            threshold = self.sd_read_speed_threshold
            logger.info(f"Speed threshold: {threshold} MB/s")
            
            if read_speed_mb >= threshold:
                logger.info(f"SD card read speed test passed: {read_speed_mb} MB/s > {threshold} MB/s")
                return True, f"SD card read test passed, read speed: {speed_value} {speed_unit} ({read_speed_mb} MB/s) > {threshold} MB/s"
            else:
                logger.warning(f"SD card read speed test failed: {read_speed_mb} MB/s < {threshold} MB/s")
                return False, f"SD card read test failed, read speed: {speed_value} {speed_unit} ({read_speed_mb} MB/s) < {threshold} MB/s"
                
        except Exception as e:
            logger.error(f"SD card read validation error: {str(e)}", exc_info=True)
            # add more diagnosis information
            diag_info = "N/A"
            try:
                if response:
                    lines = response.split("\n")
                    copied_lines = [line for line in lines if "copied" in line]
                    diag_info = ", ".join(copied_lines) if copied_lines else response[:100]
            except:
                pass
            return False, f"SD card read validation error: {str(e)}, related response content: {diag_info}"