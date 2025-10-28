"""
USB worker module
Implement USB port function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class UsbWorker(BaseTestWorker):
    """USB worker, implement USB port function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_usb"
        
        self.usb1_path = None
        self.usb2_path = None
        
        self.usb_write_speed_threshold = 30.0  # unit: MB/s
        self.usb_read_speed_threshold = 200.0  # unit: MB/s
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare USB test steps
        
        Returns:
            USB test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        return [
            TestStep(
                command=commands[0], 
                validation_func=self._find_valid_usb_path,
                timeout=5, 
                description="find valid usb path"
            ),
            TestStep(
                command=commands[1], 
                validation_func=self._validate_usb_write,
                timeout=5, 
                description="Write to usb_throughput on usb 1",
                criteria=f"Write speed > {self.usb_write_speed_threshold} MB/s",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command=commands[2], 
                validation_func=self._validate_usb_read,
                timeout=10, 
                description="Read from usb_throughput on usb 1",
                criteria=f"Read speed > {self.usb_read_speed_threshold} MB/s",
                max_retries=3,
                retry_delay=1000
            ),
            TestStep(
                command=commands[3], 
                validation_func=self._validate_usb_write, 
                timeout=10, 
                description="Write to usb_throughput on usb 2",
                criteria=f"Write speed > {self.usb_write_speed_threshold} MB/s",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command=commands[4], 
                validation_func=self._validate_usb_read,
                timeout=10, 
                description="Read from usb_throughput on usb 2",
                criteria=f"Read speed > {self.usb_read_speed_threshold} MB/s",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command=commands[5],  
                timeout=5,
                description="Remove usb_throughput on usb 1",
            ),
            TestStep(
                command=commands[6],  
                timeout=5,
                description="Remove usb_throughput on usb 2",
            )
        ]
    
    def _find_valid_usb_path(self, response: str) -> Tuple[bool, str]:
        """
        Find valid usb path from response.
        The response may contain device names separated by multiple spaces,
        and the names themselves can contain spaces.
        e.g., 'Main Data Partition-sdb1   sda1'
        """
        try:
            import re
            # Split by whitespace characters to get device names
            # Handle both single and multiple spaces, tabs, and newlines
            device_names = [name.strip() for name in re.split(r'\s+', response.strip()) if name]
            logger.debug(f"Original response: '{response}'")
            logger.debug(f"Parsed device names: {device_names}")
            
            self.usb1_path = None
            self.usb2_path = None
            
            # Prioritize assignment based on 'sda1' and 'sdb1'
            unassigned_names = []
            for name in device_names:
                if 'sda1' in name:
                    self.usb1_path = f"/run/media/{name}"
                elif 'sdb1' in name:
                    self.usb2_path = f"/run/media/{name}"
                else:
                    unassigned_names.append(name)
            
            # If paths are still unassigned, use the remaining names
            if not self.usb1_path and unassigned_names:
                self.usb1_path = f"/run/media/{unassigned_names.pop(0)}"
            
            if not self.usb2_path and unassigned_names:
                self.usb2_path = f"/run/media/{unassigned_names.pop(0)}"

            if self.usb1_path or self.usb2_path:
                paths = []
                if self.usb1_path:
                    paths.append(self.usb1_path)
                if self.usb2_path:
                    paths.append(self.usb2_path)
                return True, f"Found valid usb path(s): {', '.join(paths)}"
            else:
                logger.warning(f"Could not find any valid usb paths in response: {response}")
                return False, f"Could not find any valid usb paths in response: {response}"
            
        except Exception as e:
            logger.error(f"Find valid usb path error: {str(e)}", exc_info=True)
            return False, f"Find valid usb path error: {str(e)}"
    
    def _validate_usb_write(self, response: str) -> Tuple[bool, str]:
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
            # match various formats of speed values, including GB/s and MB/s
            speed_pattern = r'(\d+\.?\d*)\s+(MB/s|MiB/s|M/s|GB/s|GiB/s|G/s)'
            speed_match = re.search(speed_pattern, response)
            
            if not speed_match:
                # try to find all possible parts containing speed for diagnosis
                lines = response.split("\n")
                copied_line = next((line for line in lines if "copied" in line), "")
                logger.warning(f"Cannot match speed value, line containing 'copied': {copied_line}")
                return False, f"USB write test failed, cannot parse write speed. Line containing 'copied': {copied_line}"
                
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
            threshold = self.usb_write_speed_threshold
            logger.info(f"Speed threshold: {threshold} MB/s")
            
            if write_speed_mb >= threshold:
                logger.info(f"USB write speed test passed: {write_speed_mb} MB/s > {threshold} MB/s")
                return True, f"USB write test passed, write speed: {speed_value} {speed_unit} ({write_speed_mb} MB/s) > {threshold} MB/s"
            else:
                logger.warning(f"USB write speed test failed: {write_speed_mb} MB/s < {threshold} MB/s")
                return False, f"USB write test failed, write speed: {speed_value} {speed_unit} ({write_speed_mb} MB/s) < {threshold} MB/s"
                
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

    def _validate_usb_read(self, response: str) -> Tuple[bool, str]:
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
            # match various formats of speed values, including GB/s and MB/s
            speed_pattern = r'(\d+\.?\d*)\s+(MB/s|MiB/s|M/s|GB/s|GiB/s|G/s)'
            speed_match = re.search(speed_pattern, response)
            
            if not speed_match:
                # try to find all possible parts containing speed for diagnosis
                lines = response.split("\n")
                copied_line = next((line for line in lines if "copied" in line), "")
                logger.warning(f"Cannot match speed value, line containing 'copied': {copied_line}")
                return False, f"USB read test failed, cannot parse read speed. Line containing 'copied': {copied_line}"
                
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
            threshold = self.usb_read_speed_threshold
            logger.info(f"Speed threshold: {threshold} MB/s")
            
            if read_speed_mb >= threshold:
                logger.info(f"USB read speed test passed: {read_speed_mb} MB/s > {threshold} MB/s")
                return True, f"USB read test passed, read speed: {speed_value} {speed_unit} ({read_speed_mb} MB/s) > {threshold} MB/s"
            else:
                logger.warning(f"USB read speed test failed: {read_speed_mb} MB/s < {threshold} MB/s")
                return False, f"USB read test failed, read speed: {speed_value} {speed_unit} ({read_speed_mb} MB/s) < {threshold} MB/s"
                
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

    def _validate_usb_mount(self, response: str) -> Tuple[bool, str]:
        """
        Validate USB mount test result by checking mount output
        
        Args:
            response: Device response string from 'mount | grep sda1'
            
        Returns:
            (success flag, message) tuple
        """
        try:
            # If response is empty, device is not mounted
            if not response or response.strip() == "":
                return False, "Target device not mounted (no mount entry found)"
            
            # Check if target device is mounted
            if "/dev/sda1" not in response:
                return False, f"Target device not found in mount output: {response[:100]}"
                
            if "/run/media/sda1" not in response:
                return False, f"Unexpected mount point in response: {response[:100]}"
            
            # Check for file system (more flexible - accept vfat, fat32, etc.)
            if not any(fs in response.lower() for fs in ["vfat", "fat32", "fat"]):
                logger.warning(f"Unexpected file system in mount output: {response}")
                # Don't fail for file system mismatch, just warn
                
            return True, f"Device sda1 mounted at /run/media/sda1: {response.strip()}"
            
        except Exception as e:
            logger.error(f"Mount validation error: {str(e)}", exc_info=True)
            return False, f"Mount validation error: {str(e)}"

    def _validate_usb_unmount(self, response: str) -> Tuple[bool, str]:
        """
        Validate USB unmount test result
        """
        try:
            # Unmount command typically returns empty response on success
            # Accept empty response, single newline, or "not mounted" message
            if not response or response.strip() == "" or response == "\n":
                return True, "Device unmounted successfully"
            elif "/run/media/sda1: not mounted" in response:
                return True, "Device unmounted successfully"
            elif "umount:" in response and "not mounted" in response:
                return True, "Device unmounted successfully"
            else:
                logger.warning(f"Unexpected unmount response: '{response}'")
                return False, f"Device not unmounted: {response[:100]}"
        except Exception as e:
            logger.error(f"Unmount validation error: {str(e)}", exc_info=True)
            return False, f"Unmount validation error: {str(e)}"

    def _validate_usb_mount_command(self, response: str) -> Tuple[bool, str]:
        """
        Validate USB mount command execution result
        
        Args:
            response: Device response string
            
        Returns:
            (success flag, message) tuple
        """
        try:
            # Mount command typically returns empty response on success
            # Only check for error messages
            if not response or response.strip() == "" or response == "\n":
                return True, "Mount command executed successfully"
            
            # Check for common error messages
            if any(error in response.lower() for error in ["error", "failed", "cannot", "no such", "already mounted"]):
                return False, f"Mount command failed: {response[:100]}"
            
            # If there's output but no error keywords, consider it successful
            return True, f"Mount command completed: {response[:50]}"
            
        except Exception as e:
            logger.error(f"Mount command validation error: {str(e)}", exc_info=True)
            return False, f"Mount command validation error: {str(e)}"