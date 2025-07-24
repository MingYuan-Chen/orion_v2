"""
Diagnostic u-boot version test worker module
Implement diagnostic u-boot version test for device
"""
import re
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class UbootVersionWorker(BaseTestWorker):
    """Diagnostic u-boot version worker, implement diagnostic u-boot version test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_uboot_version"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic u-boot version test steps
        
        Returns:
            diagnostic u-boot version test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        
        return [
            TestStep(
                command=commands[0], 
                validation_func=self._validate_uboot_version,
                timeout=5, 
                description="Check U-Boot Version",
                criteria=f"The U-Boot version can be found",
                max_retries=1,
                retry_delay=500
            )
        ]
    
    def _validate_uboot_version(self, response: str) -> bool:
        """
        Validate U-Boot version and extract version information
        
        Args:
            response: Command response containing U-Boot version info
            
        Returns:
            bool: True if U-Boot version is found and extracted successfully
        """
        try:
            logger.info(f"Validating U-Boot version from response: {response}")
            
            # First try: original pattern for older format
            # match: U-Boot 2016.03-argo_production+g2c7fd59 (May 31 2024 - 14:00:48 +0800)
            pattern1 = r'U-Boot\s+([0-9]+\.[0-9]+[^\n]*?\([^)]+\))'
            match = re.search(pattern1, response)
            
            if match:
                # extract the full version
                full_version = match.group(1).strip()
                logger.info(f"Extract U-Boot version (pattern 1): {full_version}")
                return True, f"U-Boot version validation passed: {full_version}"
            
            # Second try: new pattern for newer format
            # match: U-Boot 2023.01 (May 28 2025 - 10:00:44 +0000)
            pattern2 = r'U-Boot\s+(\d+\.\d+(?:\.\d+)?\s+\([^)]+\))'
            match = re.search(pattern2, response)
            
            if match:
                # extract the full version including "U-Boot" prefix
                version_part = match.group(1).strip()
                full_version = f"U-Boot {version_part}"
                logger.info(f"Extract U-Boot version (pattern 2): {full_version}")
                return True, f"U-Boot version validation passed: {full_version}"
            
            # Third try: more flexible pattern to catch any U-Boot with version number and date
            # This will match any line that has U-Boot followed by version number and parentheses
            pattern3 = r'(U-Boot\s+\d+\.\d+(?:\.\d+)?(?:[^\n]*?)?\s+\([^)]+\))'
            match = re.search(pattern3, response)
            
            if match:
                full_version = match.group(1).strip()
                logger.info(f"Extract U-Boot version (pattern 3): {full_version}")
                return True, f"U-Boot version validation passed: {full_version}"
            
            # If no pattern matches, log the response for debugging
            logger.warning(f"No U-Boot version pattern matched. Response content: {response}")
            return False, f"U-Boot version not found"
                
        except Exception as e:
            logger.error(f"Error occurred while validating U-Boot version: {e}")
            return False, f"Error occurred while validating U-Boot version: {e}"

