"""
Base test worker module
Provide test step definition and execution framework, including retry mechanism
"""
from typing import List, Callable, Dict, Any, Tuple
from PySide6.QtCore import QObject, Signal, Slot, QTimer
import logging

# Get logger
logger = logging.getLogger(__name__)

class TestStep:
    """Test step class, define a command and its expected result and validation method"""
    def __init__(self, command: str, expected_response=None, timeout=5, 
                 validation_func: Callable[[str], Tuple[bool, str]] = None, 
                 description: str = "", max_retries: int = 2, retry_delay: int = 1000,
                 pre_condition: str = "", post_check: str = ""):
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
    
    def __init__(self, device_worker, continue_on_failure=True):
        """
        Initialize test worker
        
        Args:
            device_worker: Device worker object, must provide send_command method and command_result signal
            continue_on_failure: Whether to continue testing after a step fails
        """
        super().__init__()
        self.device_worker = device_worker
        
        self.current_device_id = None
        self.steps = []
        self.current_step_index = -1
        self.retry_timer = QTimer()
        self.retry_timer.setSingleShot(True)
        self.retry_timer.timeout.connect(self._retry_current_step)
        
        # Add failed step tracking
        self.failed_steps = []
        self.continue_on_failure = continue_on_failure  # Set to True to continue after failure
        
        # Add wait timer for wait steps
        self.wait_timer = QTimer()
        self.wait_timer.setSingleShot(True)
        self.wait_timer.timeout.connect(self._wait_completed)
        
        # Save signal connection for later disconnection
        self.command_connection = self.device_worker.command_result.connect(self._on_command_result)
        
        # Add pause state for user interaction
        self.is_paused_for_interaction = False
    
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
    
    def start_test(self, device_id: str):
        """
        Start test
        
        Args:
            device_id: Device ID
        """
        logger.info(f"Start test, device ID: {device_id}")
        self.current_device_id = device_id
        self.steps = self.prepare_test_steps()
        self.current_step_index = -1
        
        # Clear failed step records
        self.failed_steps = []
        
        # Stop possible existing retry timer
        if self.retry_timer.isActive():
            self.retry_timer.stop()
            
        # Stop possible existing wait timer
        if self.wait_timer.isActive():
            self.wait_timer.stop()
            
        # Initialize progress
        self.test_progress.emit(0, len(self.steps))
        
        # Execute first step
        self._execute_next_step()
    
    def stop_test(self):
        """Stop test"""
        logger.info("Manually stop test")
        if self.retry_timer.isActive():
            self.retry_timer.stop()
            
        if self.wait_timer.isActive():
            self.wait_timer.stop()
        
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
        """Execute next test step"""
        self.current_step_index += 1
        
        # Check if all steps are completed
        if self.current_step_index >= len(self.steps):
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
            return
            
        # Get current step
        step = self.steps[self.current_step_index]
        
        # Reset retry count
        step.retry_count = 0
        step.retry_messages = []
        
        # Update progress
        self.test_progress.emit(self.current_step_index + 1, len(self.steps))
        
        # Check if pre-condition exists, emit signal and pause for user confirmation
        if step.pre_condition:
            logger.debug(f"Step {self.current_step_index+1} requires pre-condition confirmation: {step.pre_condition}")
            self.is_paused_for_interaction = True
            self.pre_condition_required.emit(self.current_step_index, step.pre_condition)
            return  # Wait for user response
            
        # Continue with normal step execution
        self._execute_step(step)
    
    def _execute_step(self, step):
        """Execute the given step"""
        # Check if this is a wait step
        if step.is_wait_step:
            logger.debug(f"Execute wait step {self.current_step_index+1}/{len(self.steps)}: {step.description} ({step.wait_time} ms)")
            # Start wait timer
            self.wait_timer.setInterval(step.wait_time)
            self.wait_timer.start()
            return
        
        # Normal command step
        logger.debug(f"Execute test step {self.current_step_index+1}/{len(self.steps)}: {step.description}")
        
        # Send command
        self.device_worker.send_command(self.current_device_id, step.command, step.timeout)
    
    @Slot(bool)
    def handle_pre_condition_response(self, should_continue: bool):
        """
        Handle user response to pre-condition
        
        Args:
            should_continue: True if continue with step, False if skip
        """
        if self.is_paused_for_interaction and self.current_step_index >= 0:
            self.is_paused_for_interaction = False
            
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
                self._execute_next_step()
    
    @Slot()
    def handle_pre_condition_cancel(self):
        """Handle user cancellation of the entire test from pre-condition dialog"""
        if self.is_paused_for_interaction:
            self.is_paused_for_interaction = False
            logger.warning("User cancelled test during pre-condition confirmation")
            self.test_completed.emit(False, "Test cancelled by user")
            self._disconnect_signals()
    
    @Slot(bool)
    def handle_post_check_response(self, is_passed: bool):
        """
        Handle user response to post-check verification
        
        Args:
            is_passed: True if user judges the step passed, False if failed
        """
        if self.is_paused_for_interaction and self.current_step_index >= 0:
            self.is_paused_for_interaction = False
            
            # Record human judgement
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
        
        # Resend command
        self.device_worker.send_command(self.current_device_id, step.command, step.timeout)
    
    def _on_command_result(self, device_id: str, command: str, response: str):
        """
        Process command execution result
        
        Args:
            device_id: Device ID
            command: Executed command
            response: Command response
        """
        # If not current device or test not started, ignore
        if device_id != self.current_device_id or self.current_step_index < 0:
            return
            
        # Get current step
        step = self.steps[self.current_step_index]
        
        # If not current command, ignore
        if step.command != command:
            return
            
        # Store result
        step.result = response
        
        # Validate result
        passed = False
        message = ""
        
        # Use custom validation function first
        if step.validation_func:
            try:
                passed, message = step.validation_func(response)
                if passed:
                    message = f"Validation PASSED: {message}"
            except Exception as e:
                passed = False
                message = f"Validation exception: {str(e)}"
                logger.error(f"Validation exception: {str(e)}", exc_info=True)
        # Otherwise use expected response for comparison
        elif step.expected_response:
            if step.expected_response in response:
                passed = True
                message = f"Step PASSED: {step.description}"
            else:
                passed = False
                message = f"Step FAILED: Expected '{step.expected_response}' but received '{response}'"
        else:
            # No validation condition, default passed
            passed = True
            message = "Step PASSED: skip validation"
            
        # Set step result
        step.passed = passed
        
        # If test step failed, check if it can be retried
        if not passed:
            step.retry_messages.append(message)
            logger.warning(f"Test step {self.current_step_index+1} failed: {message}")
            
            if step.retry_count < step.max_retries:
                logger.info(f"Retrying in {step.retry_delay}ms")
                # Set delay retry
                self.retry_timer.setInterval(step.retry_delay)
                self.retry_timer.start()
                return
        else:
            logger.info(f"Test step {self.current_step_index+1} passed: {message}")
                
        # If step passed or reached maximum retries
        if passed:
            # If retry succeeded, add retry information to message
            if step.retry_count > 0:
                message = f"{message} (Retried {step.retry_count} times successfully)"
        else:
            # Final failure, add current step index to failed list
            self.failed_steps.append(self.current_step_index)
            
            # Final failure, add retry count
            message = f"{message} (Retried {step.retry_count} times still failed)"
        
        # Check if post-check is required
        if step.post_check:
            logger.debug(f"Step {self.current_step_index+1} requires post-check verification: {step.post_check}")
            # Only update UI but don't continue to next step yet
            self.test_step_completed.emit(self.current_step_index, passed, message)
            
            # Pause for user verification
            self.is_paused_for_interaction = True
            self.post_check_required.emit(self.current_step_index, step.post_check)
            return
        
        # Send step completed signal
        self.test_step_completed.emit(self.current_step_index, passed, message)
        
        # Based on continue_on_failure, decide whether to continue
        if not passed and not self.continue_on_failure:
            # If step failed and set to not continue after failure, end test
            failed_steps_str = ", ".join([f"Step {i+1}" for i in self.failed_steps])
            logger.error(f"Test stopped due to step failure. Failed steps: {failed_steps_str}")
            self.test_completed.emit(False, f"Test stopped at step {self.current_step_index+1}. Failed steps: {failed_steps_str}")
            self._disconnect_signals()
            return
        
        # Continue to execute next step
        self._execute_next_step() 