"""
EEPROM worker module
Implement EEPROM function test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType

class EepromWorker(BaseTestWorker):
    """EEPROM worker, implement EEPROM function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "functionality_eeprom"
        self.to_eeprom0_md5 = ""
        self.to_eeprom1_md5 = ""
        self.from_eeprom0_md5 = ""
        self.from_eeprom1_md5 = ""
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare eeprom test steps
        
        Returns:
            eeprom test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.FUNCTIONALITY)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.FUNCTIONALITY)
        
        return [
            # First step: Generate random test data
            TestStep(
                command=commands[0], 
                expected_response=expected_responses[0] if len(expected_responses) > 0 else None, 
                timeout=5, 
                description="Generate EEPROM 24c04 test data",
                max_retries=2,
                retry_delay=500
            ),
            TestStep(
                command=commands[1], 
                expected_response=expected_responses[1] if len(expected_responses) > 1 else None, 
                timeout=5, 
                description="Generate EEPROM 24c128 test data",
                max_retries=2,
                retry_delay=500
            ),
            TestStep(
                command=commands[2], 
                timeout=3, 
                description="Sync"
            ),
            
            # Second step: Calculate the MD5 of the test data
            TestStep(
                command=commands[3], 
                validation_func=self._store_to_eeprom0_md5,
                timeout=5, 
                description="Calculate the MD5 of EEPROM 24c04 test data",
                max_retries=2,
                retry_delay=500
            ),
            TestStep(
                command=commands[4], 
                validation_func=self._store_to_eeprom1_md5,
                timeout=5, 
                description="Calculate the MD5 of EEPROM 24c128 test data",
                max_retries=2,
                retry_delay=500
            ),
            
            # Third step: Write the data to EEPROM
            TestStep(
                command=commands[5], 
                expected_response=expected_responses[5] if len(expected_responses) > 5 else None, 
                timeout=10, 
                description="Write data to EEPROM 24c04",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[6], 
                expected_response=expected_responses[6] if len(expected_responses) > 6 else None, 
                timeout=10, 
                description="Write data to EEPROM 24c128",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=commands[7], 
                timeout=3, 
                description="Sync"
            ),
            
            # Fourth step: Read the data from EEPROM
            TestStep(
                command=commands[8], 
                timeout=10, 
                description="Read data from EEPROM 24c04",
                max_retries=3,
                retry_delay=1000
            ),
            TestStep(
                command=commands[9], 
                timeout=10, 
                description="Read data from EEPROM 24c128",
                max_retries=3,
                retry_delay=1000
            ),
            TestStep(
                command=commands[10],  
                timeout=3, 
                description="Sync"
            ),
            
            # Fifth step: Calculate the MD5 of the read data
            TestStep(
                command=commands[11], 
                validation_func=self._store_from_eeprom0_md5,
                timeout=5, 
                description="Calculate the MD5 of the read data from EEPROM 24c04",
                max_retries=2,
                retry_delay=500
            ),
            TestStep(
                command=commands[12], 
                validation_func=self._store_from_eeprom1_md5,
                timeout=5, 
                description="Calculate the MD5 of the read data from EEPROM 24c128",
                max_retries=2,
                retry_delay=500
            ),
            
            # Sixth step: Compare the MD5 values
            TestStep(
                command=commands[13], 
                validation_func=self._validate_md5_values,
                timeout=3, 
                description="Validate the consistency of EEPROM read and write",
                criteria="EEPROM Read data and Write data are consistent",
                max_retries=0,
                retry_delay=0
            ),
            
            # Seventh step: Clean up files
            TestStep(
                command=commands[14], 
                timeout=3, 
                description="Clean up EEPROM 24c04 test files",
            ),
            TestStep(
                command=commands[15], 
                timeout=3, 
                description="Clean up EEPROM 24c128 test files",
            ),
            TestStep(
                command=commands[16], 
                timeout=3, 
                description="Sync"
            )
        ]
    
    def _store_to_eeprom0_md5(self, response: str) -> Tuple[bool, str]:
        """Store the MD5 value of EEPROM 24c04 test data"""
        if not response.strip():
            return False, "Failed to get the MD5 value of EEPROM 24c04 test data"
        
        # Extract MD5 hash from response (32 characters hexadecimal)
        import re
        md5_pattern = r'[a-fA-F0-9]{32}'
        matches = re.findall(md5_pattern, response)
        
        if not matches:
            return False, f"No valid MD5 hash found in response: {response.strip()}"
        
        # Take the last MD5 hash found (in case there are multiple)
        self.to_eeprom0_md5 = matches[-1].lower()
        return True, f"The MD5 value of EEPROM 24c04 test data: {self.to_eeprom0_md5}"
    
    def _store_to_eeprom1_md5(self, response: str) -> Tuple[bool, str]:
        """Store the MD5 value of EEPROM 24c128 test data"""
        if not response.strip():
            return False, "Failed to get the MD5 value of EEPROM 24c128 test data"
        
        # Extract MD5 hash from response (32 characters hexadecimal)
        import re
        md5_pattern = r'[a-fA-F0-9]{32}'
        matches = re.findall(md5_pattern, response)
        
        if not matches:
            return False, f"No valid MD5 hash found in response: {response.strip()}"
        
        # Take the last MD5 hash found (in case there are multiple)
        self.to_eeprom1_md5 = matches[-1].lower()
        return True, f"The MD5 value of EEPROM 24c128 test data: {self.to_eeprom1_md5}"
    
    def _store_from_eeprom0_md5(self, response: str) -> Tuple[bool, str]:
        """Store the MD5 value of the read data from EEPROM 24c04"""
        if not response.strip():
            return False, "Failed to get the MD5 value of the read data from EEPROM 24c04"
        
        # Extract MD5 hash from response (32 characters hexadecimal)
        import re
        md5_pattern = r'[a-fA-F0-9]{32}'
        matches = re.findall(md5_pattern, response)
        
        if not matches:
            return False, f"No valid MD5 hash found in response: {response.strip()}"
        
        # Take the last MD5 hash found (in case there are multiple)
        self.from_eeprom0_md5 = matches[-1].lower()
        return True, f"The MD5 value of the read data from EEPROM 24c04: {self.from_eeprom0_md5}"
    
    def _store_from_eeprom1_md5(self, response: str) -> Tuple[bool, str]:
        """Store the MD5 value of the read data from EEPROM 24c128"""
        if not response.strip():
            return False, "Failed to get the MD5 value of the read data from EEPROM 24c128"
        
        # Extract MD5 hash from response (32 characters hexadecimal)
        import re
        md5_pattern = r'[a-fA-F0-9]{32}'
        matches = re.findall(md5_pattern, response)
        
        if not matches:
            return False, f"No valid MD5 hash found in response: {response.strip()}"
        
        # Take the last MD5 hash found (in case there are multiple)
        self.from_eeprom1_md5 = matches[-1].lower()
        return True, f"The MD5 value of the read data from EEPROM 24c128: {self.from_eeprom1_md5}"
    
    def _validate_md5_values(self, response: str) -> Tuple[bool, str]:
        """Validate the consistency of EEPROM read and write"""
        eeprom0_success = self.to_eeprom0_md5 == self.from_eeprom0_md5
        eeprom1_success = self.to_eeprom1_md5 == self.from_eeprom1_md5
        
        if not eeprom0_success and not eeprom1_success:
            return False, f"EEPROM 24c04 and 24c128 test failed! EEPROM 24c04 expected: {self.to_eeprom0_md5}, actual: {self.from_eeprom0_md5}; EEPROM 24c128 expected: {self.to_eeprom1_md5}, actual: {self.from_eeprom1_md5}"
        elif not eeprom0_success:
            return False, f"EEPROM 24c04 test failed! Expected MD5: {self.to_eeprom0_md5}, actual MD5: {self.from_eeprom0_md5}"
        elif not eeprom1_success:
            return False, f"EEPROM 24c128 test failed! Expected MD5: {self.to_eeprom1_md5}, actual MD5: {self.from_eeprom1_md5}"
        
        return True, "EEPROM 24c04 and 24c128 read and write test passed!" 