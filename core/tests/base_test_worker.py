"""
Base test worker module
Provide test step definition and execution framework, including retry mechanism
"""
from typing import List, Callable, Dict, Any, Tuple
from PySide6.QtCore import QObject, Signal, Slot, QTimer
import datetime
from enum import Enum
from util.logger import logger
from core.models.platform_command_set import PlatformCommandSet, CommandType

class InteractionState(Enum):
    """Enum class defining test interaction states"""
    NONE = 0                # no interaction
    PRE_CONDITION = 1       # waiting for pre-condition confirmation
    POST_CHECK = 2          # waiting for verification confirmation

class TestStep:
    """Test step class, define a command and its expected result and validation method"""
    def __init__(self, command: str, expected_response=None, timeout=5, 
                 validation_func: Callable[[str], Tuple[bool, str]] = None, 
                 description: str = "", max_retries: int = 2, retry_delay: int = 1000,
                 pre_condition: str = "", post_check: str = "",
                 specification: str = "", criteria: str = ""):
        """
        Initialize test step
        
        Args:
            command: The command to send
            expected_response: The expected response string
            timeout: Command timeout (seconds)
            validation_func: Custom validation function, receive response string, return (success flag, message)
            description: Step description
            max_retries: Maximum retry times
            retry_delay: Retry delay (milliseconds)
            pre_condition: Preparation instructions displayed before step execution
            post_check: Human verification instructions displayed after step execution
        """
        self.command = command
        self.expected_response = expected_response
        self.timeout = timeout
        self.validation_func = validation_func
        self.description = description
        self.result = None
        self.response = None  # initialize the response attribute
        self.passed = None
        self.max_retries = max_retries  # Maximum retry times
        self.retry_delay = retry_delay  # Retry delay (milliseconds)
        self.retry_count = 0            # Current retry count
        self.retry_messages = []        # Retry error messages
        self.is_wait_step = False       # Whether this is a special wait step
        self.wait_time = 0              # Wait time in milliseconds
        self.pre_condition = pre_condition  # Preparation instructions
        self.post_check = post_check    # Human verification instructions
        self.human_judgement = None     # Human judgement result (True/False/None)
        self.log_function = None        # Function to log messages to system log
        self.specification = specification  # Specification
        self.criteria = criteria              # Criteria
        
    def log_to_system(self, level, message):
        """
        Log message to system log if log function is available
        
        Args:
            level: Log level (INFO, WARNING, ERROR, etc.)
            message: Log message
        """
        if callable(self.log_function):
            self.log_function(level, message)

class BaseTestWorker(QObject):
    """Base test worker class, provide test execution framework and retry mechanism"""
    
    # Signal definition
    test_step_completed = Signal(int, bool, str)  # step_index, success, message
    test_step_retrying = Signal(int, int, int, str)  # step_index, retry_count, max_retries, error_message
    test_progress = Signal(int, int)  # current_step, total_steps
    test_completed = Signal(bool, str)  # success, message
    
    # New signals for user interaction
    pre_condition_required = Signal(int, str)  # step_index, pre_condition
    post_check_required = Signal(int, str)  # step_index, post_check
    
    def __init__(self, device_worker, device_id=None, continue_on_failure=False, platform_name="hydra"):
        """
        Initialize test worker
        
        Args:
            device_worker: Device worker object, must provide send_command method and command_result signal
            device_id: Target device ID, can be set later when starting test
            continue_on_failure: Whether to continue testing after a step fails
            platform_name: Platform name for command set, default is "hydra"
        """
        super().__init__()
        self.device_worker = device_worker
        self.device_id = device_id
        self.continue_on_failure = continue_on_failure
        self.platform_name = platform_name
        
        # Initialize platform command set
        self.platform_command_set = PlatformCommandSet(platform_name=platform_name)
        
        self.current_device_id = None
        self.steps = []
        self.current_step_index = -1
        self.retry_timer = QTimer()
        self.retry_timer.setSingleShot(True)
        self.retry_timer.timeout.connect(self._retry_current_step)
        
        # Add failed step tracking
        self.failed_steps = []
        
        # Add wait timer for wait steps
        self.wait_timer = QTimer()
        self.wait_timer.setSingleShot(True)
        self.wait_timer.timeout.connect(self._wait_completed)
        
        # Save signal connection for later disconnection
        self.command_connection = None
        
        # Test status
        self.is_running = False
        self.test_start_time = None
        self.test_end_time = None
        
        # Interaction state management
        self.interaction_state = InteractionState.NONE
        
        # Create custom logger
        self.log_function = None
        
        # Connect device worker signals
        if hasattr(self.device_worker, 'command_result'):
            self.command_connection = self.device_worker.command_result.connect(self._on_command_result)
        else:
            logger.error("Device worker does not have command_result signal")
    
    def set_platform(self, platform_name: str):
        """
        Set platform name and reload command set
        
        Args:
            platform_name: Platform name
        """
        logger.info(f"Setting platform to: {platform_name}")
        self.platform_name = platform_name
        self.platform_command_set.set_platform(platform_name)
    
    def get_command(self, command_name: str, command_type: CommandType = CommandType.AUTO_DIAGNOSTIC):
        """
        Get command from platform command set
        
        Args:
            command_name: Command name
            command_type: Command type, default is AUTO_DIAGNOSTIC
        
        Returns:
            Command string, or None if not found
        """
        cmd_value = self.platform_command_set.get_command(command_type, command_name)
        
        # Handle command list format
        if isinstance(cmd_value, list) and len(cmd_value) > 0:
            # For diagnostic tests that have multiple commands, return the first one by default
            return cmd_value[0]
        
        return cmd_value
    
    def get_commands(self, command_name: str, command_type: CommandType = CommandType.AUTO_DIAGNOSTIC):
        """
        Get all commands for a command name (handles multi-step commands)
        
        Args:
            command_name: Command name
            command_type: Command type, default is AUTO_DIAGNOSTIC
        
        Returns:
            List of command strings, or empty list if not found
        """
        cmd_value = self.platform_command_set.get_command(command_type, command_name)
        
        if isinstance(cmd_value, list):
            return cmd_value
        elif cmd_value:
            return [cmd_value]
        
        return []
    
    def set_continue_on_failure(self, value: bool):
        """
        Set whether to continue testing after a step fails
        
        Args:
            value: True to continue, False to stop
        """
        self.continue_on_failure = value
        logger.debug(f"Set continue_on_failure to {value}")
    
    def create_wait_step(self, wait_time_ms: int, description: str = None) -> TestStep:
        """
        Create a special wait step that will pause the test execution for the specified time
        
        Args:
            wait_time_ms: Wait time in milliseconds
            description: Step description (optional)
            
        Returns:
            TestStep object configured as a wait step
        """
        if description is None:
            description = f"Wait for {wait_time_ms} ms"
            
        # Create a dummy step that won't actually send a command
        step = TestStep(
            command="",  # Empty command
            description=description,
            timeout=max(1, wait_time_ms // 1000)  # Convert to seconds for timeout
        )
        
        # Mark as a wait step
        step.is_wait_step = True
        step.wait_time = wait_time_ms
        
        return step
        
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare test steps, subclasses must implement
        
        Returns:
            Test step list
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def start_test(self, device_id=None):
        """
        Start test procedure
        
        Args:
            device_id: Target device ID
        """
        if self.is_running:
            return
        
        # Save device ID
        if device_id is not None:
            self.device_id = device_id
            self.current_device_id = device_id
        
        # Check if device ID is set
        if self.device_id is None:
            logger.error("Device ID is not set")
            self.test_completed.emit(False, "Device ID is not set")
            return
        
        logger.info(f"Starting test, device ID: {self.device_id}")
        
        # Initialize test status
        self.is_running = True
        self.current_step_index = -1
        self.test_start_time = datetime.datetime.now()
        self.test_end_time = None
        self.steps = self.prepare_test_steps()
        self.failed_steps = []
        self.interaction_state = InteractionState.NONE
        
        # Set log_function for all steps if available
        if self.log_function is not None:
            for step in self.steps:
                step.log_function = self.log_function
        
        # Stop possible existing retry timer
        if self.retry_timer.isActive():
            self.retry_timer.stop()
            
        # Stop possible existing wait timer
        if self.wait_timer.isActive():
            self.wait_timer.stop()
            
        # Initialize progress
        self.test_progress.emit(0, len(self.steps))
        
        # Check if there are steps to execute
        if not self.steps:
            logger.warning("No test steps defined")
            self.test_completed.emit(False, "No test steps defined")
            self.is_running = False
            return
        
        # Start executing the first step
        self._execute_next_step()
    
    def stop_test(self):
        """Stop test"""
        logger.info("Manually stop test")
        if self.retry_timer.isActive():
            self.retry_timer.stop()
            
        if self.wait_timer.isActive():
            self.wait_timer.stop()
        
        # reset the interaction state
        self.interaction_state = InteractionState.NONE
        
        # Emit test completed signal, marked as cancelled
        if self.current_step_index >= 0:
            self.test_completed.emit(False, "Test cancelled")
            
        # Reset test state
        self.current_step_index = -1
        self.current_device_id = None
        
        # Disconnect signals
        self._disconnect_signals()
    
    def _disconnect_signals(self):
        """
        Disconnect all signals, avoid processing command results after test completion
        """
        try:
            # Try to disconnect command result signal
            if self.device_worker and self.command_connection:
                self.device_worker.command_result.disconnect(self._on_command_result)
            logger.debug("Test worker signals disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting signals: {e}")
    
    def _execute_next_step(self):
        """Execute next test step, or complete test if all steps are done"""
        # Go to next step
        self.current_step_index += 1
        
        # Check if all steps are executed
        if self.current_step_index >= len(self.steps):
            self._complete_test()
            return
            
        # Get current step
        step = self.steps[self.current_step_index]
        
        # Check pre-condition
        if step.pre_condition:
            # Don't execute step yet, wait for user to confirm pre-condition is met
            self.interaction_state = InteractionState.PRE_CONDITION
            # Emit signal to notify UI
            self.pre_condition_required.emit(self.current_step_index, step.pre_condition)
            return
            
        # Update progress
        self.test_progress.emit(self.current_step_index + 1, len(self.steps))

        # If step is a wait step, handle it specially
        if step.is_wait_step:
            self._execute_wait_step(step)
            return
            
        # Log command to system log
        if step.command and hasattr(step, 'log_to_system'):
            step.log_to_system("INFO", f"[Command] {step.command}")
            
        # Send command
        if step.command:
            try:
                # Prepare to execute command
                logger.debug(f"Execute step {self.current_step_index+1}/{len(self.steps)}: {step.description}")
                logger.debug(f"Original command: '{step.command}'")
                
                # Process variables directly using parse_command
                original_command = step.command
                processed_command = self.parse_command(original_command)
                
                # Only update if the command actually changes
                if processed_command != original_command:
                    step.command = processed_command
                
                # Send processed command
                logger.info(f"Send command to device: '{step.command}'")
                self.device_worker.send_command(self.current_device_id, step.command, step.timeout)
            except Exception as e:
                logger.error(f"Failed to send command: {e}")
                self._handle_step_result(False, f"Failed to send command: {e}")
        else:
            # No command to execute, pass the step
            self._handle_step_result(True, "No command specified")
    
    def _execute_step(self, step):
        """Execute the given step"""
        # Check if this is a wait step
        if step.is_wait_step:
            logger.debug(f"Execute wait step {self.current_step_index+1}/{len(self.steps)}: {step.description} ({step.wait_time} ms)")
            # Start wait timer
            self.wait_timer.setInterval(step.wait_time)
            self.wait_timer.start()
            return
        
        logger.debug(f"Executing step {self.current_step_index+1}/{len(self.steps)}: {step.description}")
        
        # Check if command is empty before executing
        if not step.command:
            logger.debug("Step has no command, skipping command execution")
            self._handle_step_result(True, "No command specified")
            return
            
        logger.debug(f"Original command: '{step.command}'")
        
        # Process variables directly using parse_command
        original_command = step.command
        processed_command = self.parse_command(original_command)
        
        # Only update if the command actually changes
        if processed_command != original_command:
            step.command = processed_command
        
        # Send processed command
        logger.info(f"Send command to device: '{step.command}'")
        self.device_worker.send_command(self.current_device_id, step.command, step.timeout)
    
    @Slot(bool)
    def handle_pre_condition_response(self, should_continue: bool):
        """
        Handle user response to pre-condition
        
        Args:
            should_continue: True if continue with step, False if skip
        """
        if self.interaction_state == InteractionState.PRE_CONDITION and self.current_step_index >= 0:
            self.interaction_state = InteractionState.NONE
            
            if should_continue:
                # Continue with step execution
                logger.debug(f"User confirmed pre-condition for step {self.current_step_index+1}")
                self._execute_step(self.steps[self.current_step_index])
            else:
                # Skip this step, mark as passed and move to next
                logger.warning(f"User skipped step {self.current_step_index+1}")
                step = self.steps[self.current_step_index]
                step.passed = True
                self.test_step_completed.emit(self.current_step_index, True, "Step skipped by user")
    
    @Slot()
    def handle_pre_condition_cancel(self):
        """Handle user cancellation of the entire test from pre-condition dialog"""
        if self.interaction_state != InteractionState.NONE:
            self.interaction_state = InteractionState.NONE
            logger.warning("User cancelled test during interaction")
            self.test_completed.emit(False, "Test cancelled by user")
            self._disconnect_signals()
    
    @Slot(bool)
    def handle_post_check_response(self, is_passed: bool):
        """
        Handle user response to post-check verification
        """
        if self.interaction_state == InteractionState.POST_CHECK and self.current_step_index >= 0:
            self.interaction_state = InteractionState.NONE
            
            # Record human judgement result
            step = self.steps[self.current_step_index]
            step.human_judgement = is_passed
            
            # Update step result based on human judgement
            if not is_passed:
                step.passed = False
                if self.current_step_index not in self.failed_steps:
                    self.failed_steps.append(self.current_step_index)
                logger.warning(f"Step {self.current_step_index+1} failed based on human judgement")
                self.test_step_completed.emit(
                    self.current_step_index, False, "Step failed based on human judgement")
            
            # Continue to next step
            self._execute_next_step()
    
    def _wait_completed(self):
        """Handle wait step completion"""
        # Get current step
        if self.current_step_index < 0 or self.current_step_index >= len(self.steps):
            return
            
        step = self.steps[self.current_step_index]
        if not step.is_wait_step:
            return
            
        # Mark as passed
        step.passed = True
        
        # Emit step completed signal
        message = f"Wait completed: {step.description}"
        logger.debug(message)
        self.test_step_completed.emit(self.current_step_index, True, message)
        
        # Continue to next step
        self._execute_next_step()
    
    def _retry_current_step(self):
        """Retry current step"""
        # Ensure test is still running
        if self.current_step_index < 0 or self.current_step_index >= len(self.steps):
            return
            
        # Get current step
        step = self.steps[self.current_step_index]
        
        # Update retry count and resend command
        step.retry_count += 1
        
        # Record retry information
        retry_message = f"Retry step {self.current_step_index+1}: {step.description} ({step.retry_count}/{step.max_retries})"
        logger.warning(retry_message)
        
        # Send retry signal
        self.test_step_retrying.emit(
            self.current_step_index, 
            step.retry_count, 
            step.max_retries,
            step.retry_messages[-1] if step.retry_messages else "Unknown error"
        )
        
        # retry before processing variables
        original_command = step.command
        processed_command = self.parse_command(original_command)
        
        # only update if the command actually changes
        if processed_command != original_command:
            step.command = processed_command
        
        # send processed command
        logger.info(f"Retry, sending command to device: '{step.command}'")
        self.device_worker.send_command(self.current_device_id, step.command, step.timeout)
    
    def _handle_step_result(self, passed, message):
        """
        Handle step result processing
        
        Args:
            passed: Whether the step passed
            message: Result message
        """
        # Get current step
        step = self.steps[self.current_step_index]
        step.passed = passed
        
        if not passed:
            self.failed_steps.append(self.current_step_index)
        
        # Emit step completed signal
        self.test_step_completed.emit(self.current_step_index, passed, message)
        
        # Based on continue_on_failure, decide whether to continue
        if not passed and not self.continue_on_failure:
            # If step failed and set to not continue after failure, end test
            failed_steps_str = ", ".join([f"Step {i+1}" for i in self.failed_steps])
            logger.error(f"Test stopped due to step failure. Failed steps: {failed_steps_str}")
            self.test_completed.emit(False, f"Test stopped at step {self.current_step_index+1}. Failed steps: {failed_steps_str}")
            self._disconnect_signals()
            return
        
        # Check if the step has post_check requirements
        if hasattr(step, 'post_check') and step.post_check:
            # Set interaction state to post_check and emit signal
            self.interaction_state = InteractionState.POST_CHECK
            # Emit signal to notify UI
            logger.info(f"Post-check required for step {self.current_step_index+1}: {step.post_check}")
            self.post_check_required.emit(self.current_step_index, step.post_check)
            return
        
        # Continue to execute next step
        self._execute_next_step()

    def _on_command_result(self, device_id: str, command: str, response: str):
        """
        Process command execution result
        
        Args:
            device_id: Device ID
            command: Executed command
            response: Command response
        """
        # If not current device or test not started, ignore
        if device_id != self.current_device_id or not self.is_running:
            return
            
        # Check if step index is valid
        if self.current_step_index < 0 or self.current_step_index >= len(self.steps):
            logger.error(f"Invalid step index: {self.current_step_index}, total steps: {len(self.steps)}")
            return
            
        # Get current step
        step = self.steps[self.current_step_index]
        
        logger.info(f"Current step command: '{step.command}'")
        
        # Check if command matches, allow partial match (processed variable command)
        command_match = False
        expected_command = step.command
        
        # Simple exact match
        if command.strip() == expected_command.strip():
            command_match = True
            logger.info(f"Command matches exactly: '{command}' matches '{expected_command}'")
        # Or if command is a part of original command (possibly because of variable replacement)
        elif command.strip() in expected_command.strip() or expected_command.strip() in command.strip():
            command_match = True
            logger.info(f"Command partially matches: '{command}' matches '{expected_command}'")
        # Or check if there is a trace of variable replacement
        elif ('{' in expected_command and '}' in expected_command):
            command_match = True
            logger.info(f"Command contains variables, assumed match: '{command}' matches '{expected_command}'")
        
        # If command does not match, it might be an asynchronous result, ignore
        if not command_match:
            logger.warning(f"Command does not match, ignoring this result, received command: '{command}', expected command: '{expected_command}'")
            return
        
        # Always record command output to step - ensure the response is set
        step.response = response
        # Also set the result attribute to be the same as response for consistency
        step.result = response
        
        # call the response collector function (if set)
        if hasattr(self, 'response_collector') and callable(self.response_collector):
            test_id = getattr(self, 'test_id', self.__class__.__name__)
            self.response_collector(test_id, self.current_step_index, command, response)
        
        # Log response to system log if configured (保留这个日志记录功能)
        if hasattr(step, 'log_function') and callable(step.log_function):
            # use a clear format to record the response, ensure it can be clearly distinguished in the log
            step.log_function("INFO", f"[Response] {response}")
        
        # Validate the response if validation function is provided
        if step.validation_func is not None:
            try:
                result, message = step.validation_func(response)
                if result:
                    # Validation passed
                    step.passed = True
                    logger.info(f"Test step {self.current_step_index+1} validation PASSED: {message}")
                    self._handle_step_result(True, f"Validation PASSED: {message}")
                    return
                else:
                    # Validation failed
                    step.passed = False
                    step.retry_messages.append(message)
                    logger.warning(f"Test step {self.current_step_index+1} FAILED: {message}")
                    
                    # Check if should retry
                    if step.retry_count < step.max_retries:
                        # Schedule retry
                        self.retry_timer.setInterval(step.retry_delay)
                        logger.info(f"Retrying in {step.retry_delay}ms")
                        self.retry_timer.start()
                    else:
                        # Max retries reached, fail the step
                        logger.warning(f"Test step {self.current_step_index+1} FAILED: {message} (Retried {step.retry_count} times still failed)")
                        self._handle_step_result(False, f"{message} (Retried {step.retry_count} times still failed)")
                    return
            except Exception as e:
                # Validation function error
                step.passed = False
                error_message = f"Validation function error: {str(e)}"
                step.retry_messages.append(error_message)
                logger.error(error_message, exc_info=True)
                self._handle_step_result(False, error_message)
                return
        elif step.expected_response is not None:
            # check if the response contains the expected result
            if step.expected_response in response:
                step.passed = True
                logger.info(f"Test step {self.current_step_index+1} PASSED: expected string '{step.expected_response}' found in response")
                self._handle_step_result(True, f"Expected string '{step.expected_response}' found in response")
                return
            else:
                # Validation failed
                step.passed = False
                error_message = f"Expected string '{step.expected_response}' not found in response"
                step.retry_messages.append(error_message)
                logger.warning(f"Test step {self.current_step_index+1} FAILED: {error_message}")
                
                # Check if should retry
                if step.retry_count < step.max_retries:
                    # Schedule retry
                    self.retry_timer.setInterval(step.retry_delay)
                    logger.info(f"Retrying in {step.retry_delay}ms")
                    self.retry_timer.start()
                else:
                    # Max retries reached, fail the step
                    logger.warning(f"Test step {self.current_step_index+1} FAILED: {error_message} (Retried {step.retry_count} times still failed)")
                    self._handle_step_result(False, f"{error_message} (Retried {step.retry_count} times still failed)")
                return
        else:
            # No validation function, pass the step
            step.passed = True
            logger.info(f"Test step {self.current_step_index+1} PASSED: skip validation")
            self._handle_step_result(True, "Step PASSED: skip validation")
            return
    
    def _execute_wait_step(self, step):
        """Execute wait step"""
        logger.debug(f"Execute wait step {self.current_step_index+1}/{len(self.steps)}: {step.description} ({step.wait_time} ms)")
        # Start wait timer
        self.wait_timer.setInterval(step.wait_time)
        self.wait_timer.start()
    
    def _complete_test(self):
        """Complete test, check test results and send test completed signal"""
        # Record test end time
        self.test_end_time = datetime.datetime.now()
        self.is_running = False
        self.interaction_state = InteractionState.NONE
        
        # All steps completed, check if test passed based on failed steps
        is_test_passed = len(self.failed_steps) == 0
        
        if is_test_passed:
            logger.info("All test steps completed, test passed")
            self.test_completed.emit(True, "Test completed successfully")
        else:
            # Test completed but with failed steps
            failed_steps_str = ", ".join([f"Step {i+1}" for i in self.failed_steps])
            logger.warning(f"Test completed with {len(self.failed_steps)} failed steps: {failed_steps_str}")
            self.test_completed.emit(False, f"Test completed with {len(self.failed_steps)} failed steps: {failed_steps_str}")
        
        # Disconnect signals
        self._disconnect_signals() 

    def parse_command(self, command: str) -> str:
        """
        Process command string, replace {variable_name} format placeholders with corresponding class attribute values
        
        Args:
            command: Original command string, possibly containing {variable_name} format placeholders
            
        Returns:
            Processed command string
        """
        # If command is empty, return directly
        if not command:
            return command
            
        # Quick check if command contains variable placeholders
        if '{' not in command or '}' not in command:
            return command
            
        try:
            
            # Find all {variable_name} format placeholders in command
            import re
            # Regex pattern to match {variable_name} format
            pattern = r'\{([a-zA-Z0-9_]+)\}'
            
            # Find all matches
            matches = list(re.finditer(pattern, command))
            
            # If no matches, return original command
            if not matches:
                return command
            
            # Record all found placeholders
            logger.debug(f"Found {len(matches)} variable placeholders in command")
            for i, match in enumerate(matches):
                var_name = match.group(1)
                logger.debug(f"Placeholder {i+1}: '{var_name}'")
            
            # Create processed command string
            processed_command = command
            
            # Replace each match
            for match in matches:
                var_name = match.group(1)  # Get variable name (without brackets)
                
                # Check if instance has corresponding attribute
                if hasattr(self, var_name):
                    # Get class attribute value
                    var_value = getattr(self, var_name)
                    logger.info(f"Found variable '{var_name}' value: {var_value}")
                    
                    # If value is None, record warning
                    if var_value is None:
                        logger.warning(f"Variable '{var_name}' value is None, not replaced")
                        continue
                    
                    # Convert value to string (ensure non-string values can be processed correctly)
                    value_str = str(var_value)
                    
                    # Replace placeholder
                    placeholder = f"{{{var_name}}}"
                    processed_command = processed_command.replace(placeholder, value_str)
                    logger.info(f"After replacing '{placeholder}': '{processed_command}'")
                else:
                    # List available attributes for debugging
                    all_attrs = [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self, a))]
                    logger.warning(f"Variable '{var_name}' not found in worker, available attributes: {', '.join(all_attrs[:10])}...")
            
            # Record final command
            if processed_command != command:
                logger.info(f"Command processing completed: '{command}' -> '{processed_command}'")
            else:
                logger.warning(f"Command processing unchanged: '{command}'")
                
            return processed_command
        except Exception as e:
            logger.error(f"Error processing command '{command}': {str(e)}", exc_info=True)
            # Return original command when error occurs
            return command 

    def set_response_collector(self, collector_func):
        """
        Set the response collector function, call it after the command execution
        
        Args:
            collector_func: Collector function, parameters are (test_id, step_index, command, response)
        """
        self.response_collector = collector_func
        logger.debug(f"Response collector function set for {self.__class__.__name__}") 