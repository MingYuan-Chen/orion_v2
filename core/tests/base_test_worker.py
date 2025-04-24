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
                 description: str = "", max_retries: int = 2, retry_delay: int = 1000):
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

class BaseTestWorker(QObject):
    """Base test worker class, provide test execution framework and retry mechanism"""
    
    # Signal definition
    test_step_completed = Signal(int, bool, str)  # step_index, success, message
    test_step_retrying = Signal(int, int, int, str)  # step_index, retry_count, max_retries, error_message
    test_progress = Signal(int, int)  # current_step, total_steps
    test_completed = Signal(bool, str)  # success, message
    
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
        
        # Save signal connection for later disconnection
        self.command_connection = self.device_worker.command_result.connect(self._on_command_result)
        
    def set_continue_on_failure(self, value: bool):
        """
        Set whether to continue testing after a step fails
        
        Args:
            value: True to continue, False to stop
        """
        self.continue_on_failure = value
        logger.debug(f"Set continue_on_failure to {value}")
        
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
            
        # Initialize progress
        self.test_progress.emit(0, len(self.steps))
        
        # Execute first step
        self._execute_next_step()
    
    def stop_test(self):
        """Stop test"""
        logger.info("Manually stop test")
        if self.retry_timer.isActive():
            self.retry_timer.stop()
        
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
        
        logger.debug(f"Execute test step {self.current_step_index+1}/{len(self.steps)}: {step.description}")
        
        # Send command
        self.device_worker.send_command(self.current_device_id, step.command, step.timeout)
    
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
        retry_message = f"Retry step {self.current_step_index+1}: {step.description} (第 {step.retry_count}/{step.max_retries} 次)"
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
    
    @Slot(str, str, str)
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
            except Exception as e:
                passed = False
                message = f"Validation function exception: {str(e)}"
                logger.error(f"Validation function exception: {str(e)}", exc_info=True)
        # Otherwise use expected response for comparison
        elif step.expected_response:
            if step.expected_response in response:
                passed = True
                message = f"Step passed: {step.description}"
            else:
                passed = False
                message = f"Step failed: Expected '{step.expected_response}' but received '{response}'"
        else:
            # No validation condition, default passed
            passed = True
            message = "Step passed (no validation condition)"
            
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