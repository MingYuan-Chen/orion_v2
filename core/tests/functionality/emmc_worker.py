"""
Emmc worker module
Implement emmc function test for device
"""
from typing import List, Tuple
from util.logger import logger
from core.tests.base_test_worker import BaseTestWorker, TestStep


class EmmcWorker(BaseTestWorker):
    """Emmc worker, implement emmc function test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
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
                criteria="'copied' in the response",
                max_retries=1,
                retry_delay=500
            ),
            TestStep(
                command="sync", 
                timeout=5, 
                description="Sync",
            ),
            TestStep(
                command="echo 3 > /proc/sys/vm/drop_caches", 
                expected_response="drop_caches", 
                timeout=10, 
                description="Drop caches",
                criteria="'drop_caches' in the response",
                max_retries=3,
                retry_delay=1000
            ),
            TestStep(
                command="dd if=/emmc_througtput of=/dev/null bs=1M", 
                expected_response="copied", 
                timeout=10, 
                description="Read from emmc_throughput",
                criteria="'copied' in the response",
                max_retries=2,
                retry_delay=1500
            )
        ]

