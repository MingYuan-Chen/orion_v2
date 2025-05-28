"""
USB worker module
Implement USB port function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class UsbWorker(BaseTestWorker):
    """USB worker, implement USB port function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        
        # set usb write speed threshold
        self.usb_write_speed_threshold = 60.0  # unit: MB/s
        # set usb read speed threshold
        self.usb_read_speed_threshold = 200.0  # unit: MB/s
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare USB test steps
        
        Returns:
            USB test steps list
        """
        return [
            TestStep(
                command="dd if=/dev/zero of=/run/media/sda1/usb_throughput bs=1M count=200 status=progress", 
                validation_func=self._validate_usb_write,
                timeout=5, 
                description="Write to usb_throughput",
                criteria=f"Write speed > {self.usb_write_speed_threshold} MB/s",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command="dd if=/run/media/sda1/usb_throughput of=/dev/null bs=1M", 
                validation_func=self._validate_usb_read,
                timeout=10, 
                description="Read from usb_throughput",
                criteria=f"Read speed > {self.usb_read_speed_threshold} MB/s",
                max_retries=3,
                retry_delay=1000
            ),
            TestStep(
                command="sudo umount /run/media/sda1", 
                validation_func=self._validate_usb_unmount, 
                timeout=10, 
                description="Unmount sda1",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command="sudo mount /dev/sda1 /run/media/sda1", 
                validation_func=self._validate_usb_mount_command,
                timeout=10, 
                description="Mount sda1",
                max_retries=2,
                retry_delay=1500
            ),
            TestStep(
                command="mount | grep sda1", 
                validation_func=self._validate_usb_mount,
                timeout=10, 
                description="Validate sda1 mounted",
                max_retries=2,
                retry_delay=2000
            )
        ]
    
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
            threshold = self.usb_write_speed_threshold
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
            threshold = self.usb_read_speed_threshold
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