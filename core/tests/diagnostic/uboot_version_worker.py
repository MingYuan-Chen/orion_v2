"""
Diagnostic u-boot version test worker module
Implement diagnostic u-boot version test for device
"""
import re
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class UbootVersionWorker(BaseTestWorker):
    """Diagnostic u-boot version worker, implement diagnostic u-boot version test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic u-boot version test steps
        
        Returns:
            diagnostic u-boot version test steps list
        """
        return [
            TestStep(
                command="strings /dev/mtd0 | grep -E 'U-Boot'", 
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
            # Use regex to extract U-Boot version from response
            # match: U-Boot 2016.03-argo_production+g2c7fd59 (May 31 2024 - 14:00:48 +0800)
            pattern = r'U-Boot\s+([0-9]+\.[0-9]+[^\n]*?\([^)]+\))'
            match = re.search(pattern, response)
            
            if match:
                # extract the full version
                full_version = match.group(1).strip()
                logger.info(f"Extract U-Boot version: {full_version}")
                return True, f"U-Boot version validation passed: {full_version}"
            
            else:
                return False, f"U-Boot version not found"
                
        except Exception as e:
            logger.error(f"Error occurred while validating U-Boot version: {e}")
            return False, f"Error occurred while validating U-Boot version: {e}"

