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
    
    # New signals for user interaction
    test_pre_condition_required = Signal(str, int, str)  # test_id, step_index, pre_condition
    test_post_check_required = Signal(str, int, str)  # test_id, step_index, post_check
    
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
        self._register_worker("usb_ports", UsbPortsTestWorker, continue_on_failure=True)
        from core.tests.emmc_test_worker import EmmcTestWorker
        self._register_worker("emmc", EmmcTestWorker, continue_on_failure=True)
        from core.tests.eeprom_test_worker import EepromTestWorker
        self._register_worker("eeprom", EepromTestWorker, continue_on_failure=True)
        from core.tests.battery_test_worker import BatteryTestWorker
        self._register_worker("battery", BatteryTestWorker, continue_on_failure=True)
        from core.tests.backlight_test_worker import BacklightTestWorker
        self._register_worker("backlight", BacklightTestWorker, continue_on_failure=True)
        from core.tests.led_test_worker import LedTestWorker
        self._register_worker("led", LedTestWorker, continue_on_failure=True)
        from core.tests.audio_test_worker import AudioTestWorker
        self._register_worker("audio", AudioTestWorker, continue_on_failure=True)
        from core.tests.lcd_test_worker import LcdTestWorker
        self._register_worker("lcd", LcdTestWorker, continue_on_failure=True)
        from core.tests.diagnostic_cpu_name_worker import DiagnosticCpuNameWorker
        self._register_worker("diagnostic_cpu_name", DiagnosticCpuNameWorker, continue_on_failure=True)
        from core.tests.diagnostic_cpu_processor_worker import DiagnosticCpuProcessorWorker
        self._register_worker("diagnostic_cpu_processor", DiagnosticCpuProcessorWorker, continue_on_failure=True)
        from core.tests.diagnostic_emmc_size_worker import DiagnosticEmmcSizeWorker
        self._register_worker("diagnostic_emmc_size", DiagnosticEmmcSizeWorker, continue_on_failure=True)
        from core.tests.diagnostic_mac_address_worker import DiagnosticMacAddressWorker
        self._register_worker("diagnostic_mac_address", DiagnosticMacAddressWorker, continue_on_failure=True)
        from core.tests.diagnostic_memory_size_worker import DiagnosticMemorySizeWorker
        self._register_worker("diagnostic_memory_size", DiagnosticMemorySizeWorker, continue_on_failure=True)
        from core.tests.diagnostic_nor_flash_size_worker import DiagnosticNorFlashSizeWorker
        self._register_worker("diagnostic_nor_flash_size", DiagnosticNorFlashSizeWorker, continue_on_failure=True)
        from core.tests.diagnostic_pic_version_worker import DiagnosticPicVersionWorker
        self._register_worker("diagnostic_pic_version", DiagnosticPicVersionWorker, continue_on_failure=True)
        from core.tests.diagnostic_sync_time_worker import DiagnosticSyncTimeWorker
        self._register_worker("diagnostic_sync_time", DiagnosticSyncTimeWorker, continue_on_failure=True)
        from core.tests.diagnostic_set_get_rtc_time_worker import DiagnosticSetGetRtcTimeWorker
        self._register_worker("diagnostic_set_get_rtc_time", DiagnosticSetGetRtcTimeWorker, continue_on_failure=True)
        from core.tests.diagnostic_design_capacity_worker import DiagnosticDesignCapacityWorker
        self._register_worker("diagnostic_design_capacity", DiagnosticDesignCapacityWorker, continue_on_failure=True)
        from core.tests.diagnostic_design_voltage_worker import DiagnosticDesignVoltageWorker
        self._register_worker("diagnostic_design_voltage", DiagnosticDesignVoltageWorker, continue_on_failure=True)
        from core.tests.diagnostic_uboot_version_worker import DiagnosticUbootVersionWorker
        self._register_worker("diagnostic_uboot_version", DiagnosticUbootVersionWorker, continue_on_failure=True)


        # self._register_worker("touch_screen", TouchScreenTestWorker, continue_on_failure=True)
        
        logger.info(f"Registered test workers: {', '.join(self.test_workers.keys())}")
    
    def _create_and_connect_worker(self, test_id: str, worker_class, continue_on_failure: bool = True):
        """
        Create a worker instance and connect its signals
        
        Args:
            test_id: Test ID
            worker_class: Test worker class
            
        Returns:
            Created worker instance
        """
        # Create worker instance
        worker = worker_class(self.device_worker, continue_on_failure=continue_on_failure)
        
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
        
        # Connect new user interaction signals
        worker.pre_condition_required.connect(
            lambda step_index, pre_condition:
                self.test_pre_condition_required.emit(test_id, step_index, pre_condition)
        )
        worker.post_check_required.connect(
            lambda step_index, post_check:
                self.test_post_check_required.emit(test_id, step_index, post_check)
        )
        
        # Save worker class for later use
        worker.worker_class = worker_class
        
        return worker
    
    def _register_worker(self, test_id: str, worker_class, continue_on_failure: bool = True):
        """
        Register a single test worker
        
        Args:
            test_id: Test ID, used to identify different test types
            worker_class: Test worker class
        """
        # Create worker and connect signals
        worker = self._create_and_connect_worker(test_id, worker_class, continue_on_failure)
        
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
        # Check if the test ID is valid
        if test_id not in self.test_workers:
            error_msg = f"Unknown test: {test_id}"
            logger.error(error_msg)
            self.test_completed.emit(test_id, False, error_msg)
            return
        
        # Get worker class from the worker
        worker_class = self.test_workers[test_id].worker_class
        
        # If there is a test running, stop it first
        if self.active_test_worker is not None:
            logger.warning(f"Stop current running test: {self.active_test_id}")
            self.active_test_worker.stop_test()
        
        # Create worker and connect signals
        worker = self._create_and_connect_worker(test_id, worker_class)
        
        # Update dictionary and active test
        self.test_workers[test_id] = worker
        self.active_test_id = test_id
        self.active_test_worker = worker
        
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

    def cleanup(self):
        """Clean up hardware test manager resources"""
        try:
            logger.debug("Cleaning up HardwareTestManagerService resources")
            
            # Stop current test
            if self.active_test_worker:
                self.active_test_worker.stop_test()
                self.active_test_id = None
                self.active_test_worker = None
            
            # Disconnect all signals
            try:
                self.test_started.disconnect()
                self.test_completed.disconnect()
                self.test_step_completed.disconnect()
                self.test_step_retrying.disconnect()
                self.test_progress.disconnect()
                self.test_pre_condition_required.disconnect()
                self.test_post_check_required.disconnect()
            except Exception:
                # Signals may already be disconnected, ignore errors
                pass
            
            # Clean up all test workers
            for test_id, worker in list(self.test_workers.items()):
                try:
                    worker.stop_test()  # Ensure all tests are stopped
                except Exception as e:
                    logger.warning(f"Error stopping test worker {test_id}: {e}")
                
            # Clear worker dictionary, let garbage collection handle these objects
            self.test_workers.clear()
            
        except Exception as e:
            logger.error(f"Error during HardwareTestManagerService cleanup: {e}")

    def __del__(self):
        """Destructor, ensure resources are released"""
        try:
            logger.debug("HardwareTestManagerService is being destroyed")
            # Do not call cleanup in the destructor to avoid accessing deleted objects
        except Exception:
            # Avoid throwing exceptions in the destructor
            pass 

    @Slot(str, int, bool)
    def handle_pre_condition_response(self, test_id: str, step_index: int, should_continue: bool):
        """
        Handle user response to pre-condition
        
        Args:
            test_id: Test ID
            step_index: Step index
            should_continue: True if continue with step, False if skip
        """
        if self.active_test_id == test_id and self.active_test_worker:
            self.active_test_worker.handle_pre_condition_response(should_continue)
    
    @Slot(str, int)
    def handle_pre_condition_cancel(self, test_id: str, step_index: int):
        """
        Handle user cancellation of the test during pre-condition
        
        Args:
            test_id: Test ID
            step_index: Step index
        """
        if self.active_test_id == test_id and self.active_test_worker:
            self.active_test_worker.handle_pre_condition_cancel()
    
    @Slot(str, int, bool)
    def handle_post_check_response(self, test_id: str, step_index: int, is_passed: bool):
        """
        Handle user response to post-check verification
        
        Args:
            test_id: Test ID
            step_index: Step index
            is_passed: True if user judges the step passed, False if failed
        """
        if self.active_test_id == test_id and self.active_test_worker:
            self.active_test_worker.handle_post_check_response(is_passed) 