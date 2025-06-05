"""
Emmc worker module
Implement emmc function test for device
"""
from typing import List, Tuple
from util.logger import logger
from core.tests.base_test_worker import BaseTestWorker, TestStep
from core.models.platform_command_set import CommandType

class EmmcWorker(BaseTestWorker):
    """Emmc worker, implement emmc function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_emmc"
        
        # set emmc write speed threshold
        self.emmc_write_speed_threshold = 60.0  # unit: MB/s
        # set emmc read speed threshold
        self.emmc_read_speed_threshold = 200.0  # unit: MB/s
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare emmc test steps
        
        Returns:
            emmc test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY) 
        return [
            TestStep(
                command=commands[0], 
                validation_func=self._validate_emmc_write,
                timeout=5, 
                description="Write to emmc_throughput",
                criteria=f"Write speed > {self.emmc_write_speed_threshold} MB/s",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[1], 
                timeout=5, 
                description="Sync",
            ),
            TestStep(
                command=commands[2], 
                timeout=10, 
                description="Drop caches",
                max_retries=3,
                retry_delay=1000
            ),
            TestStep(
                command=commands[3], 
                validation_func=self._validate_emmc_read,
                timeout=10, 
                description="Read from emmc_throughput",
                criteria=f"Read speed > {self.emmc_read_speed_threshold} MB/s",
                max_retries=2,
                retry_delay=1500
            )
        ]
    
    def _validate_emmc_write(self, response: str) -> Tuple[bool, str]:
        """
        Validate USB write test result, parse write speed and determine if it meets the requirement
        
        Args:
            response: command response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            logger.info(f"Start validating USB write speed: {response}")
            
            if not response or response.strip() == "":
                return False, "USB write test failed, response is empty"
                
            if "copied" not in response:
                return False, "USB write test failed, 'copied' not found"
                
            # use regex to extract write speed
            import re
            # match various formats of speed values, e.g. 79.7 MB/s, 79.7 MiB/s, 79.7 M/s, etc.
            speed_pattern = r'(\d+\.?\d*)\s+(?:MB/s|MiB/s|M/s)'
            speed_match = re.search(speed_pattern, response)
            
            if not speed_match:
                # try to find all possible parts containing speed for diagnosis
                lines = response.split("\n")
                copied_line = next((line for line in lines if "copied" in line), "")
                logger.warning(f"Cannot match speed value, line containing 'copied': {copied_line}")
                return False, f"USB write test failed, cannot parse write speed. Line containing 'copied': {copied_line}"
                
            # extract speed value and convert to float
            write_speed = float(speed_match.group(1))
            logger.info(f"Extracted write speed: {write_speed} MB/s")
            
            # use configured threshold to determine
            threshold = self.emmc_write_speed_threshold
            logger.info(f"Speed threshold: {threshold} MB/s")
            
            if write_speed >= threshold:
                logger.info(f"USB write speed test passed: {write_speed} MB/s > {threshold} MB/s")
                return True, f"USB write test passed, write speed: {write_speed} MB/s > {threshold} MB/s"
            else:
                logger.warning(f"USB write speed test failed: {write_speed} MB/s < {threshold} MB/s")
                return False, f"USB write test failed, write speed: {write_speed} MB/s < {threshold} MB/s"
                
        except Exception as e:
            logger.error(f"USB write validation error: {str(e)}", exc_info=True)
            # add more diagnosis information
            diag_info = "N/A"
            try:
                if response:
                    lines = response.split("\n")
                    copied_lines = [line for line in lines if "copied" in line]
                    diag_info = ", ".join(copied_lines) if copied_lines else response[:100]
            except:
                pass
            return False, f"USB write validation error: {str(e)}, related response content: {diag_info}"

    def _validate_emmc_read(self, response: str) -> Tuple[bool, str]:
        """
        Validate USB read test result, parse read speed and determine if it meets the requirement
        
        Args:
            response: command response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            logger.info(f"Start validating USB read speed: {response}")
            
            if not response or response.strip() == "":
                return False, "USB read test failed, response is empty"
                
            if "copied" not in response:
                return False, "USB read test failed, 'copied' not found"
                
            # use regex to extract read speed
            import re
            # match various formats of speed values, e.g. 291 MB/s, 291 MiB/s, 291 M/s, etc.
            speed_pattern = r'(\d+\.?\d*)\s+(?:MB/s|MiB/s|M/s)'
            speed_match = re.search(speed_pattern, response)
            
            if not speed_match:
                # try to find all possible parts containing speed for diagnosis
                lines = response.split("\n")
                copied_line = next((line for line in lines if "copied" in line), "")
                logger.warning(f"Cannot match speed value, line containing 'copied': {copied_line}")
                return False, f"USB read test failed, cannot parse read speed. Line containing 'copied': {copied_line}"
                
            # extract speed value and convert to float
            read_speed = float(speed_match.group(1))
            logger.info(f"Extracted read speed: {read_speed} MB/s")
            
            # use configured threshold to determine
            threshold = self.emmc_read_speed_threshold
            logger.info(f"Speed threshold: {threshold} MB/s")
            
            if read_speed >= threshold:
                logger.info(f"USB read speed test passed: {read_speed} MB/s > {threshold} MB/s")
                return True, f"USB read test passed, read speed: {read_speed} MB/s > {threshold} MB/s"
            else:
                logger.warning(f"USB read speed test failed: {read_speed} MB/s < {threshold} MB/s")
                return False, f"USB read test failed, read speed: {read_speed} MB/s < {threshold} MB/s"
                
        except Exception as e:
            logger.error(f"USB read validation error: {str(e)}", exc_info=True)
            # add more diagnosis information
            diag_info = "N/A"
            try:
                if response:
                    lines = response.split("\n")
                    copied_lines = [line for line in lines if "copied" in line]
                    diag_info = ", ".join(copied_lines) if copied_lines else response[:100]
            except:
                pass
            return False, f"USB read validation error: {str(e)}, related response content: {diag_info}"


