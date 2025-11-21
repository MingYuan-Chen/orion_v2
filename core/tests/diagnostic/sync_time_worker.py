"""
Diagnostic sync time test worker module
Implement diagnostic sync time test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger
from core.models.platform_command_set import CommandType
from datetime import datetime
import time

class SyncTimeWorker(BaseTestWorker):
    """Diagnostic sync time worker, implement diagnostic sync time test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
        self.test_id = "diagnostic_sync_time"
        self.time_components = None
        self.platform_name = platform_name
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic sync time test steps
        
        Returns:
            diagnostic sync time test steps list
        """
        commands = self.get_commands(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        expected_responses = self.get_expected_responses(self.test_id, CommandType.AUTO_DIAGNOSTIC)
        if self.platform_name == "athena":
            return [
                TestStep(
                    command=commands[0],
                    timeout=5, 
                    description="Set system time",
                ),
                TestStep(
                    command=commands[1],
                    validation_func=self._athena_parse_hwclock_time,
                    timeout=5, 
                    description="Read RTC Time",
                ),
                TestStep(
                    command=commands[2],
                    validation_func=self._athena_validate_date,
                    timeout=5, 
                    description="Verify RTC time synced with server time",
                    criteria=f"RTC time is same as server time",
                )
            ]
        if self.platform_name == "odin":
            return [
                TestStep(
                    command=commands[0],
                    timeout=5, 
                    description="Make root filesystem writable",
                ),
                TestStep(
                    command=commands[1],
                    timeout=5, 
                    description="Enable the USB Power",
                ),
                TestStep(
                    command=commands[2],
                    timeout=5, 
                    description='Copy the "ntpdate" and library to the system',
                ),
                TestStep(
                    command=commands[3],
                    validation_func=self._validate_hwclock_time,
                    timeout=5, 
                    description='Check if the system can handle leap-year dates',
                    criteria=f"System can handle leap-year dates",
                ),
                TestStep(
                    command=commands[4],
                    validation_func=self._validate_odin_sync_time,
                    timeout=5, 
                    description='Sync time with server:192.168.6.11',
                    criteria=f"ntp sync time succeed and system can write system time to RTC time",
                )
            ]
        else:
            return [
                TestStep(
                    command=commands[0], 
                    validation_func=self._validate_sync_time,
                    timeout=5, 
                    description="Sync time with server",
                    criteria="Can sync time with server",
                    max_retries=1,
                    retry_delay=500
                ),
                TestStep(
                    command=commands[1],
                    timeout=5, 
                    description="Write RTC Time",
                ),
                TestStep(
                    command=commands[2],
                    validation_func=self._validate_hwclock_time,
                    timeout=5, 
                    description="Read RTC Time",
                ),
                TestStep(
                    command=commands[3],
                    validation_func=self._validate_date,
                    timeout=5, 
                    description="Verify RTC time synced with server time",
                    criteria=f"RTC time is same as server time",
                )
            ]
    
    def _validate_sync_time(self, response: str) -> Tuple[bool, str]:
        """
        Validate sync time
        """

        try:
            response = response.strip()
            lines = response.split("\n") if response else []

            # 1. Look for sync-related keywords
            for line in lines:
                low = line.lower()
                if any(k in low for k in ["adjust", "offset", "step", "time"]):
                    return True, f"Time synchronized: {line.strip()}"

            meaningful = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]

            # 4. Could not parse any sync-related information → fail
            return False, f"Could not parse sync time response: {response[:100]}"

        except Exception as e:
            logger.error(f"Error parsing sync time response: {e}")
            return False, f"Error parsing sync time response: {str(e)}"
        
    def _validate_hwclock_time(self, response: str) -> Tuple[bool, str]:
        """
        Validate hwclock time and extract key time components
        """
        try:
            response_clean = response.strip()
            if not response_clean:
                return False, "Empty response from hwclock command"
            
            # Filter out ntpdate/sync time mixed information, only keep hwclock time start with weekday
            weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            hwclock_line = None
            
            lines = response_clean.split('\n')
            for line in lines:
                line = line.strip()
                # skip empty line
                if not line:
                    continue
                # skip line contains ntpdate
                if 'ntpdate' in line:
                    continue
                # skip line contains adjust/offset/server
                if any(keyword in line.lower() for keyword in ['adjust', 'offset', 'server']):
                    continue
                # find line start with weekday
                if any(line.startswith(day) for day in weekdays):
                    hwclock_line = line
                    break
            
            if not hwclock_line:
                return False, f"No valid hwclock time found in response: {response_clean}"
            
            logger.debug(f"Filtered hwclock line: '{hwclock_line}'")
            
            # clean hwclock line, remove possible suffix like " 0.000000 seconds"
            # hwclock normal format: "Wed May 28 09:17:26 2025  0.000000 seconds"
            # we only need: "Wed May 28 09:17:26 2025"
            if " seconds" in hwclock_line:
                # remove " 0.000000 seconds" part
                hwclock_line = hwclock_line.split(" seconds")[0].strip()
                # remove extra spaces
                hwclock_line = ' '.join(hwclock_line.split())
            
            logger.debug(f"Cleaned hwclock line: '{hwclock_line}'")
            
            # extract time components from cleaned hwclock line
            split_words = hwclock_line.split()
            if len(split_words) < 5:
                return False, f"Invalid hwclock format after cleaning: {hwclock_line}"
            
            # Store multiple time components for flexible matching
            # cleaned format: "Wed May 28 09:17:26 2025"
            self.synced_time = hwclock_line  # Store clean hwclock response
            self.time_components = {
                'weekday': split_words[0],  # "Wed"
                'month': split_words[1],    # "May" 
                'day': split_words[2],      # "28"
                'year': split_words[4] if len(split_words) > 4 else ''  # "2025"
            }
            
            logger.debug(f"Extracted time components: {self.time_components}")
            return True, f"RTC time: {hwclock_line}"
            
        except Exception as e:
            logger.error(f"Error parsing hwclock response: {e}")
            return False, f"Error parsing hwclock response: {str(e)}"
            
    def _validate_date(self, response: str) -> Tuple[bool, str]:
        """
        Validate date command by checking if key time components match
        """
        logger.debug(f"[SyncTimeWorker] ntpdate response repr: {repr(response)}")
        try:
            if not hasattr(self, 'time_components') or not self.time_components:
                return False, "No time components available from previous hwclock step"
            
            response_clean = response.strip()
            if not response_clean:
                return False, "Empty response from date command"
            
            logger.debug(f"Date response: '{response_clean}'")
            logger.debug(f"Checking against time components: {self.time_components}")
            
            # Check if key time components from hwclock appear in date response
            matches = 0
            total_checks = 0
            
            for component, value in self.time_components.items():
                if value:  # Only check non-empty components
                    total_checks += 1
                    if value in response_clean:
                        matches += 1
                        logger.debug(f"Found {component} '{value}' in date response")
                    else:
                        logger.debug(f"Missing {component} '{value}' in date response")
            
            # Require at least 2 out of 4 components to match (flexible matching)
            if matches >= 2 and total_checks >= 3:
                return True, f"RTC time is synced with system time ({matches}/{total_checks} components match)"
            else:
                return False, f"Time components mismatch: only {matches}/{total_checks} components match. HWClock: {self.synced_time}, Date: {response_clean}"
                
        except Exception as e:
            logger.error(f"Error validating date: {e}")
            return False, f"Error validating date: {str(e)}"
    
    def _athena_parse_hwclock_time(self, response: str) -> Tuple[bool, str]:
        """
        Parse the time string from `hwclock -r` for the Athena platform.
        The expected format is similar to ISO 8601, e.g., '2025-10-07 14:22:18.12345-07:00'.
        The response may contain extra text like a shell prompt on a new line.
        """
        try:
            if not response or not response.strip():
                return False, "Empty response from hwclock command"

            # Isolate the first line, which should contain the timestamp.
            timestamp_str = response.strip().split('\n')[0]

            # The fromisoformat method can handle most standard formats.
            self.hw_time = datetime.fromisoformat(timestamp_str)
            logger.info(f"Parsed hwclock time: {self.hw_time}")
            return True, f"Successfully parsed RTC time: {timestamp_str}"
        except Exception as e:
            logger.error(f"Error parsing hwclock response: {e}")
            return False, f"Could not parse hwclock time: {response.strip()}"
    
    def _athena_validate_date(self, response: str) -> Tuple[bool, str]:
        """
        Parse the time from the `date` command and validate it against the stored hwclock time.
        The expected format for date is e.g., 'Tue Oct  7 14:22:19 UTC 2025'.
        The response may contain extra text like a shell prompt on a new line.
        """
        try:
            if not hasattr(self, 'hw_time') or not self.hw_time:
                return False, "hwclock time was not parsed successfully in the previous step."

            if not response or not response.strip():
                return False, "Empty response from date command"

            # Isolate the first line, which should contain the date string.
            date_str = response.strip().split('\n')[0]

            # The format code for this is %a %b %d %H:%M:%S %Z %Y
            # Example: 'Tue Oct  7 14:22:19 UTC 2025'
            system_time = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Z %Y")
            logger.info(f"Parsed system date time: {system_time}")

            # Make both datetimes offset-aware (assuming UTC if not specified)
            # For simplicity, we can make them naive if they are in the same timezone
            hw_time_naive = self.hw_time.replace(tzinfo=None)
            system_time_naive = system_time.replace(tzinfo=None)

            # Calculate the difference in seconds
            time_difference = abs((system_time_naive - hw_time_naive).total_seconds())
            logger.info(f"Time difference between hwclock and system date is {time_difference:.2f} seconds.")

            # Set a tolerance of 2 seconds
            tolerance_seconds = 2.0

            if time_difference <= tolerance_seconds:
                return True, f"Time is in sync. Difference: {time_difference:.2f}s"
            else:
                return False, f"Time is out of sync. Difference: {time_difference:.2f}s > {tolerance_seconds}s"

        except Exception as e:
            logger.error(f"Error validating date: {e}")
            return False, f"Could not validate date: {response.strip()}"

    def _validate_odin_sync_time(self, response: str) -> Tuple[bool, str]:
        """
        Validate sync time by checking ONLY the first 'Sync Time = ...' result.
        If multiple results exist, the earliest one decides PASS/FAIL.
        """

        if not response:
            return False, "Sync time failed (empty response)"

        # Normalize: split by line
        lines = response.lower().splitlines()

        # Find ALL "sync time =" lines
        sync_lines = [line.strip() for line in lines if "sync time =" in line]

        if not sync_lines:
            return False, "Sync time failed (no sync result found)"

        # Get ONLY the first result
        first_result = sync_lines[0]

        if "sync time = pass" in first_result:
            return True, "Sync time passed"

        return False, "Sync time failed"
