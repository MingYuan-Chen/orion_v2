"""
Hardware test manager service module
Provide a unified hardware test management interface, coordinate the execution of different test workers
"""
from typing import Dict, List, Type, Any
from PySide6.QtCore import QObject, Signal, Slot
from util.logger import logger

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
    
    def __init__(self, device_worker, platform_name="hydra_fhd"):
        """
        Initialize hardware test manager
        
        Args:
            device_worker: Device worker object, will be passed to all test workers
            platform_name: Platform name for command set, default is "hydra_fhd"
        """
        super().__init__()
        self.device_worker = device_worker
        self.platform_name = platform_name
        
        # Register all module test workers
        self.test_workers = {}
        self._register_test_workers()
        
        # Current active test
        self.active_test_id = None
        self.active_test_worker = None
        
        logger.info(f"Hardware test manager initialized with platform: {platform_name}")
        
    def set_platform(self, platform_name: str):
        """
        Set platform name for all test workers
        
        Args:
            platform_name: Platform name
        """
        logger.info(f"Setting platform name to: {platform_name}")
        self.platform_name = platform_name
        
        # Update platform name for all existing test workers
        for test_id, worker in self.test_workers.items():
            if hasattr(worker, 'set_platform'):
                worker.set_platform(platform_name)
        
        logger.info(f"Platform name updated for {len(self.test_workers)} test workers")
        
    def _register_test_workers(self):
        """Register all module test workers"""
        
        # Functionality test workers
        from core.tests.functionality.usb_worker import UsbWorker
        self._register_worker("functionality_usb", UsbWorker, continue_on_failure=True)
        from core.tests.functionality.emmc_worker import EmmcWorker
        self._register_worker("functionality_emmc", EmmcWorker, continue_on_failure=True)
        from core.tests.functionality.eeprom_worker import EepromWorker
        self._register_worker("functionality_eeprom", EepromWorker, continue_on_failure=True)
        from core.tests.functionality.battery_worker import BatteryWorker
        self._register_worker("functionality_battery", BatteryWorker, continue_on_failure=True)
        from core.tests.functionality.backlight_worker import BacklightWorker
        self._register_worker("functionality_backlight", BacklightWorker, continue_on_failure=True)
        from core.tests.functionality.led_worker import LedWorker
        self._register_worker("functionality_led", LedWorker, continue_on_failure=True)
        from core.tests.functionality.audio_worker import AudioWorker
        self._register_worker("functionality_audio", AudioWorker, continue_on_failure=True)
        from core.tests.functionality.lcd_worker import LcdWorker
        self._register_worker("functionality_lcd", LcdWorker, continue_on_failure=True)
        from core.tests.functionality.camera_worker import CameraWorker
        self._register_worker("functionality_camera", CameraWorker, continue_on_failure=True)
        from core.tests.functionality.touch_worker import TouchWorker
        self._register_worker("functionality_touch", TouchWorker, continue_on_failure=True)
        from core.tests.functionality.power_button_worker import PowerButtonWorker
        self._register_worker("functionality_power_button", PowerButtonWorker, continue_on_failure=True)
        from core.tests.functionality.charge_worker import ChargeWorker
        self._register_worker("functionality_charge", ChargeWorker, continue_on_failure=True)
        from core.tests.functionality.hdmi_worker import HdmiWorker
        self._register_worker("functionality_hdmi", HdmiWorker, continue_on_failure=True)
        
        # Diagnostic test workers
        from core.tests.diagnostic.cpu_name_worker import CpuNameWorker
        self._register_worker("diagnostic_cpu_name", CpuNameWorker, continue_on_failure=True)
        from core.tests.diagnostic.cpu_processor_worker import CpuProcessorWorker
        self._register_worker("diagnostic_cpu_processor", CpuProcessorWorker, continue_on_failure=True)
        from core.tests.diagnostic.emmc_size_worker import EmmcSizeWorker
        self._register_worker("diagnostic_emmc_size", EmmcSizeWorker, continue_on_failure=True)
        from core.tests.diagnostic.mac_address_worker import MacAddressWorker
        self._register_worker("diagnostic_mac_address", MacAddressWorker, continue_on_failure=True)
        from core.tests.diagnostic.memory_size_worker import MemorySizeWorker
        self._register_worker("diagnostic_memory_size", MemorySizeWorker, continue_on_failure=True)
        from core.tests.diagnostic.nor_flash_size_worker import NorFlashSizeWorker
        self._register_worker("diagnostic_nor_flash_size", NorFlashSizeWorker, continue_on_failure=True)
        from core.tests.diagnostic.pic_version_worker import PicVersionWorker
        self._register_worker("diagnostic_pic_version", PicVersionWorker, continue_on_failure=True)
        from core.tests.diagnostic.sync_time_worker import SyncTimeWorker
        self._register_worker("diagnostic_sync_time", SyncTimeWorker, continue_on_failure=True)
        # from core.tests.diagnostic.set_get_rtc_time_worker import SetGetRtcTimeWorker
        # self._register_worker("diagnostic_set_get_rtc_time", SetGetRtcTimeWorker, continue_on_failure=True)
        from core.tests.diagnostic.design_capacity_worker import DesignCapacityWorker
        self._register_worker("diagnostic_design_capacity", DesignCapacityWorker, continue_on_failure=True)
        from core.tests.diagnostic.design_voltage_worker import DesignVoltageWorker
        self._register_worker("diagnostic_design_voltage", DesignVoltageWorker, continue_on_failure=True)
        from core.tests.diagnostic.uboot_version_worker import UbootVersionWorker
        self._register_worker("diagnostic_uboot_version", UbootVersionWorker, continue_on_failure=True)
        from core.tests.diagnostic.kernal_name_worker import KernalNameWorker
        self._register_worker("diagnostic_kernal_name", KernalNameWorker, continue_on_failure=True)
        from core.tests.diagnostic.panel_id_resolution_worker import PanelIdResolutionWorker
        self._register_worker("diagnostic_panel_id_resolution", PanelIdResolutionWorker, continue_on_failure=True)
        from core.tests.diagnostic.wifi_bt_worker import WifiBtWorker
        self._register_worker("diagnostic_wifi_bt", WifiBtWorker, continue_on_failure=True)
        from core.tests.diagnostic.ethernet_worker import EthernetWorker
        self._register_worker("diagnostic_ethernet", EthernetWorker, continue_on_failure=True)
        from core.tests.diagnostic.wifi_connection_worker import WifiConnectionWorker
        self._register_worker("diagnostic_wifi_connection", WifiConnectionWorker, continue_on_failure=True)


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
        # Create worker instance with platform name
        worker = worker_class(self.device_worker, continue_on_failure=continue_on_failure, platform_name=self.platform_name)
        
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
        if self.active_test_worker:
            self.stop_current_test()
        
        # Use existing method to create and connect worker
        worker = self._create_and_connect_worker(test_id, worker_class, continue_on_failure=True)
        
        # Save active test
        self.active_test_id = test_id
        self.active_test_worker = worker
        
        # prepare the test steps and save them, ensure the step information can be used for UI display
        worker.steps = worker.prepare_test_steps()
        
        # set the log_function for the test steps, ensure the commands are recorded in the system log
        for step in worker.steps:
            if hasattr(worker, 'log_function') and worker.log_function:
                step.log_function = worker.log_function
        
        # Start the test - emit signal AFTER steps are prepared
        logger.info(f"Starting test: {test_id} for device: {device_id}")
        logger.info(f"Test steps prepared: {len(worker.steps)} steps")
        self.test_started.emit(test_id)
        worker.start_test(device_id)
    
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