"""
Hardware test manager service module
Provide a unified hardware test management interface, coordinate the execution of different test workers
"""
from typing import Dict, List, Type, Any
import logging
from PySide6.QtCore import QObject, Signal, Slot

# Get logger
logger = logging.getLogger(__name__)

class HardwareTestManagerService(QObject):
    """
    Hardware test manager service
    Responsible for managing and coordinating the execution of various hardware test workers
    """
    # Test result signal
    test_started = Signal(str)  # test_id
    test_completed = Signal(str, bool, str)  # test_id, success, message
    test_step_completed = Signal(str, int, bool, str)  # test_id, step_index, success, message
    test_step_retrying = Signal(str, int, int, int, str)  # test_id, step_index, retry_count, max_retries, error
    test_progress = Signal(str, int, int)  # test_id, current_step, total_steps
    
    def __init__(self, device_worker):
        """
        Initialize hardware test manager
        
        Args:
            device_worker: Device worker object, will be passed to all test workers
        """
        super().__init__()
        self.device_worker = device_worker
        
        # Register all module test workers
        self.test_workers = {}
        self._register_test_workers()
        
        # Current active test
        self.active_test_id = None
        self.active_test_worker = None
        
        logger.info("Hardware test manager initialized")
        
    def _register_test_workers(self):
        """Register all module test workers"""
        # Currently only implement USB test
        from core.tests.usb_ports_test_worker import UsbPortsTestWorker
        self._register_worker("usb_ports", UsbPortsTestWorker)
        
        # self._register_worker("touch_screen", TouchScreenTestWorker)
        
        logger.info(f"Registered test workers: {', '.join(self.test_workers.keys())}")
    
    def _register_worker(self, test_id: str, worker_class):
        """
        Register a single test worker
        
        Args:
            test_id: Test ID, used to identify different test types
            worker_class: Test worker class
        """
        worker = worker_class(self.device_worker)
        
        # Connect worker signals to manager signals
        worker.test_step_completed.connect(
            lambda step_index, success, message: 
                self.test_step_completed.emit(test_id, step_index, success, message)
        )
        worker.test_step_retrying.connect(
            lambda step_index, retry_count, max_retries, error_message:
                self.test_step_retrying.emit(test_id, step_index, retry_count, max_retries, error_message)
        )
        worker.test_progress.connect(
            lambda current, total: 
                self.test_progress.emit(test_id, current, total)
        )
        worker.test_completed.connect(
            lambda success, message: 
                self._handle_test_completion(test_id, success, message)
        )
        
        # Store worker
        self.test_workers[test_id] = worker
        logger.debug(f"Registered test worker: {test_id}")
    
    def get_available_tests(self) -> List[str]:
        """
        Get all available test IDs
        
        Returns:
            Test ID list
        """
        return list(self.test_workers.keys())
    
    def start_test(self, device_id: str, test_id: str):
        """
        Start executing the specified test
        
        Args:
            device_id: Device ID
            test_id: Test ID
        """
        if test_id not in self.test_workers:
            error_msg = f"Unknown test: {test_id}"
            logger.error(error_msg)
            self.test_completed.emit(test_id, False, error_msg)
            return
        
        # If there is a test running, stop it first
        if self.active_test_worker is not None:
            logger.warning(f"Stop current running test: {self.active_test_id}")
            self.active_test_worker.stop_test()
            
        # Set current active test
        self.active_test_id = test_id
        self.active_test_worker = self.test_workers[test_id]
        
        logger.info(f"Start test: {test_id}, device ID: {device_id}")
        
        # Notify test started
        self.test_started.emit(test_id)
        
        # Start test worker
        self.active_test_worker.start_test(device_id)
    
    def stop_current_test(self):
        """Stop current running test"""
        if self.active_test_worker is not None:
            logger.info(f"Manually stop test: {self.active_test_id}")
            self.active_test_worker.stop_test()
            
            # Test stop signal will be emitted by the worker, handled in _on_worker_test_completed
    
    @Slot(bool, str)
    def _handle_test_completion(self, test_id: str, success: bool, message: str):
        """
        Handle test worker test completed event
        
        Args:
            success: Whether the test is successful
            message: Test result message
        """
        if self.active_test_id is None:
            return
            
        # Forward test completed signal
        logger.info(f"Test completed: {test_id}, result: {'Success' if success else 'Failed'}, message: {message}")
        self.test_completed.emit(test_id, success, message)
        
        # Clear current active test
        self.active_test_id = None
        self.active_test_worker = None 