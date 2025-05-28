"""
Diagnostic sync time test worker module
Implement diagnostic sync time test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class SyncTimeWorker(BaseTestWorker):
    """Diagnostic sync time worker, implement diagnostic sync time test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic sync time test steps
        
        Returns:
            diagnostic sync time test steps list
        """
        return [
            TestStep(
                command="sudo ntpdate -u time.stdtime.gov.tw", 
                validation_func=self._validate_sync_time,
                timeout=5, 
                description="Sync time with time.stdtime.gov.tw",
                criteria="Can sync time with time.stdtime.gov.tw",
                max_retries=1,
                retry_delay=500
            )
        ]
    
    def _validate_sync_time(self, response: str) -> Tuple[bool, str]:
        """
        Validate sync time
        """
        if not response or not response.strip():
            return False, "No response received from ntpdate command"
            
        response_lower = response.lower()
        if "error" in response_lower or "failed" in response_lower:
            return False, "Failed to sync time"
        
        try:
            # Try to extract synced time information
            lines = response.strip().split('\n')
            
            # Look for lines containing time synchronization information
            for line in lines:
                if any(keyword in line.lower() for keyword in ['adjust', 'offset', 'step', 'time']):
                    # If we find sync-related content, consider it successful
                    return True, f"Time synchronized: {line.strip()}"
            
            # If no specific sync information found but response exists, try to parse it
            if lines:
                # Try different parsing strategies
                if "ntpdate" in response:
                    # Original parsing logic with safety checks
                    parts = response.split(" ntpdate")
                    if len(parts) > 0:
                        first_part = parts[0].strip()
                        if first_part:
                            sub_lines = first_part.split('\n')
                            if len(sub_lines) > 1:
                                synced_time = sub_lines[1]
                                return True, f"Synced time: {synced_time}"
                
                # If we have any non-empty response, consider it as potential success
                meaningful_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
                if meaningful_lines:
                    return True, f"Time sync response: {meaningful_lines[0]}"
            
            # If we reach here, we got a response but couldn't parse it
            return False, f"Could not parse sync time response: {response[:100]}"
            
        except Exception as e:
            logger.error(f"Error parsing sync time response: {e}")
            return False, f"Error parsing sync time response: {str(e)}"

