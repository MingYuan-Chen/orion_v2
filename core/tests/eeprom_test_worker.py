"""
EEPROM test worker module
Implement EEPROM function test for device
"""
from typing import List, Tuple
import logging
from .base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class EepromTestWorker(BaseTestWorker):
    """EEPROM test worker, implement EEPROM function test for device"""
    
    def __init__(self, device_worker):
        super().__init__(device_worker)
        self.i2c_bus = "/dev/i2c-0"
        self.eeprom0 = "0x55"  # external 128Kbit EEPROM chip
        self.eeprom1 = "0x57"  # 1Kbit EEPROM inside RTC
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
        return [
            # First step: Generate random test data
            TestStep(
                command="dd if=/dev/urandom of=to_eeprom0_data bs=1K count=16", 
                expected_response="copied", 
                timeout=5, 
                description="Generate EEPROM0 test data",
                max_retries=2,
                retry_delay=500
            ),
            TestStep(
                command="dd if=/dev/urandom of=to_eeprom1_data bs=1 count=128", 
                expected_response="copied", 
                timeout=5, 
                description="Generate EEPROM1 test data",
                max_retries=2,
                retry_delay=500
            ),
            TestStep(
                command="sync", 
                expected_response="#", 
                timeout=3, 
                description="Sync",
                max_retries=1,
                retry_delay=500
            ),
            
            # Second step: Calculate the MD5 of the test data
            TestStep(
                command="md5sum to_eeprom0_data | cut -d' ' -f1", 
                validation_func=self._store_to_eeprom0_md5,
                timeout=5, 
                description="Calculate the MD5 of EEPROM0 test data",
                max_retries=2,
                retry_delay=500
            ),
            TestStep(
                command="md5sum to_eeprom1_data | cut -d' ' -f1", 
                validation_func=self._store_to_eeprom1_md5,
                timeout=5, 
                description="Calculate the MD5 of EEPROM1 test data",
                max_retries=2,
                retry_delay=500
            ),
            
            # Third step: Write the data to EEPROM
            TestStep(
                command=f"cat to_eeprom0_data | eeprog -f -16 {self.i2c_bus} {self.eeprom0} -w 0x0", 
                expected_response="eeprog", 
                timeout=10, 
                description="Write data to EEPROM0",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command=f"cat to_eeprom1_data | eeprog -f -8 {self.i2c_bus} {self.eeprom1} -w 0x0", 
                expected_response="eeprog", 
                timeout=10, 
                description="Write data to EEPROM1",
                max_retries=1,
                retry_delay=1000
            ),
            TestStep(
                command="sync", 
                expected_response="#", 
                timeout=3, 
                description="Sync",
                max_retries=1,
                retry_delay=500
            ),
            
            # Fourth step: Read the data from EEPROM
            TestStep(
                command=f"eeprog {self.i2c_bus} {self.eeprom0} -16 -f -q -r 0x0:16384 > from_eeprom0_data", 
                expected_response="eeprog", 
                timeout=10, 
                description="Read data from EEPROM0",
                max_retries=3,
                retry_delay=1000
            ),
            TestStep(
                command=f"eeprog {self.i2c_bus} {self.eeprom1} -8 -f -q -r 0x0:128 > from_eeprom1_data", 
                expected_response="eeprog", 
                timeout=10, 
                description="Read data from EEPROM1",
                max_retries=3,
                retry_delay=1000
            ),
            TestStep(
                command="sync", 
                expected_response="#", 
                timeout=3, 
                description="Sync",
                max_retries=1,
                retry_delay=500
            ),
            
            # Fifth step: Calculate the MD5 of the read data
            TestStep(
                command="md5sum from_eeprom0_data | cut -d' ' -f1", 
                validation_func=self._store_from_eeprom0_md5,
                timeout=5, 
                description="Calculate the MD5 of the read data from EEPROM0",
                max_retries=2,
                retry_delay=500
            ),
            TestStep(
                command="md5sum from_eeprom1_data | cut -d' ' -f1", 
                validation_func=self._store_from_eeprom1_md5,
                timeout=5, 
                description="Calculate the MD5 of the read data from EEPROM1",
                max_retries=2,
                retry_delay=500
            ),
            
            # Sixth step: Compare the MD5 values
            TestStep(
                command="echo 'Comparing MD5 values'", 
                validation_func=self._validate_md5_values,
                timeout=3, 
                description="Validate the consistency of EEPROM read and write",
                max_retries=0,
                retry_delay=0
            ),
            
            # Seventh step: Clean up files
            TestStep(
                command="rm -f to_eeprom0_data from_eeprom0_data", 
                expected_response="#", 
                timeout=3, 
                description="Clean up EEPROM0 test files",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command="rm -f to_eeprom1_data from_eeprom1_data", 
                expected_response="#", 
                timeout=3, 
                description="Clean up EEPROM1 test files",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command="sync", 
                expected_response="#", 
                timeout=3, 
                description="Sync",
                max_retries=1,
                retry_delay=500
            )
        ]
    
    def _store_to_eeprom0_md5(self, response: str) -> Tuple[bool, str]:
        """Store the MD5 value of EEPROM0 test data"""
        if not response.strip():
            return False, "Failed to get the MD5 value of EEPROM0 test data"
        self.to_eeprom0_md5 = response.strip()
        return True, f"The MD5 value of EEPROM0 test data: {self.to_eeprom0_md5}"
    
    def _store_to_eeprom1_md5(self, response: str) -> Tuple[bool, str]:
        """Store the MD5 value of EEPROM1 test data"""
        if not response.strip():
            return False, "Failed to get the MD5 value of EEPROM1 test data"
        self.to_eeprom1_md5 = response.strip()
        return True, f"The MD5 value of EEPROM1 test data: {self.to_eeprom1_md5}"
    
    def _store_from_eeprom0_md5(self, response: str) -> Tuple[bool, str]:
        """Store the MD5 value of the read data from EEPROM0"""
        if not response.strip():
            return False, "Failed to get the MD5 value of the read data from EEPROM0"
        self.from_eeprom0_md5 = response.strip()
        return True, f"The MD5 value of the read data from EEPROM0: {self.from_eeprom0_md5}"
    
    def _store_from_eeprom1_md5(self, response: str) -> Tuple[bool, str]:
        """Store the MD5 value of the read data from EEPROM1"""
        if not response.strip():
            return False, "Failed to get the MD5 value of the read data from EEPROM1"
        self.from_eeprom1_md5 = response.strip()
        return True, f"The MD5 value of the read data from EEPROM1: {self.from_eeprom1_md5}"
    
    def _validate_md5_values(self, response: str) -> Tuple[bool, str]:
        """Validate the consistency of EEPROM read and write"""
        eeprom0_success = self.to_eeprom0_md5 == self.from_eeprom0_md5
        eeprom1_success = self.to_eeprom1_md5 == self.from_eeprom1_md5
        
        if not eeprom0_success and not eeprom1_success:
            return False, f"EEPROM0 and EEPROM1 test failed! EEPROM0 expected: {self.to_eeprom0_md5}, actual: {self.from_eeprom0_md5}; EEPROM1 expected: {self.to_eeprom1_md5}, actual: {self.from_eeprom1_md5}"
        elif not eeprom0_success:
            return False, f"EEPROM0 test failed! Expected MD5: {self.to_eeprom0_md5}, actual MD5: {self.from_eeprom0_md5}"
        elif not eeprom1_success:
            return False, f"EEPROM1 test failed! Expected MD5: {self.to_eeprom1_md5}, actual MD5: {self.from_eeprom1_md5}"
        
        return True, "EEPROM0 and EEPROM1 read and write test passed!" 