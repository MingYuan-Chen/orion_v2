"""
USB ports test worker module
Implement USB port function test for device
"""
from typing import List, Tuple
import logging
from .base_test_worker import BaseTestWorker, TestStep

# Get logger
logger = logging.getLogger(__name__)

class EmmcTestWorker(BaseTestWorker):
    """Emmc test worker, implement emmc function test for device"""
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare emmc test steps
        
        Returns:
            emmc test steps list
        """
        return [
            TestStep(
                command="dd if=/dev/zero of=/emmc_througtput bs=1M count=200", 
                expected_response="copied", 
                timeout=5, 
                description="Write to emmc_throughput",
                max_retries=1,           # Maximum retries 1 time
                retry_delay=500          # 0.5 seconds later retry
            ),
            TestStep(
                command="sync && echo 3 > /proc/sys/vm/drop_caches", 
                expected_response="drop_caches", 
                timeout=10, 
                description="Drop caches",
                max_retries=3,           # Read operation may need multiple attempts
                retry_delay=1000         # 1 second later retry
            ),
            TestStep(
                command="dd if=/emmc_througtput of=/dev/null bs=1M", 
                expected_response="copied", 
                timeout=10, 
                description="Read from emmc_throughput",
                max_retries=2,           # Maximum retries 2 times
                retry_delay=1500         # 1.5 seconds later retry
            )
        ]