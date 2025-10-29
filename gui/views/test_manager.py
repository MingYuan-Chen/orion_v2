"""
Test manager view module
Responsible for managing test execution, UI updates and result tracking
"""
from typing import Dict, List, Any, Optional
import datetime
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QDialogButtonBox
)
from PySide6.QtGui import QColor

from util.logger import logger
from core.services.hardware_test_manager import HardwareTestManagerService
from gui.widgets.test_container import TestContainer
from gui.widgets.test_selection_widget import TestSelectionDialog


class TestManagerView(QObject):
    """
    Test manager view class
    Responsible for managing test execution, UI updates and result tracking
    """
    
    # define a signal for all tests completed
    all_tests_completed = Signal()
    
    def __init__(self, device_id: str, hw_test_manager: HardwareTestManagerService):
        """
        Initialize test manager view
        
        Args:
            device_id: Device ID
            hw_test_manager: Hardware test manager service
        """
        super().__init__()
        
        # save device ID and hardware test manager
        self.device_id = device_id
        self.hw_test_manager = hw_test_manager
        
        # save the MainWindowController reference (set later)
        self.main_window_controller = None
        
        # test UI components reference
        self.test_container = None  # test container reference
        self.test_all_button = None  # test all button reference 
        self.result_table = None  # test result table reference
        self.progress_bar = None  # test progress bar reference
        self.abort_button = None  # abort button reference
        
        # test sequence related
        self.original_test_sequence = ["functionality_audio", "functionality_backlight", "functionality_battery", "functionality_camera",
                                       "functionality_charge", "functionality_eeprom", "functionality_emmc", "functionality_hdmi",
                                       "functionality_lcd", "functionality_led", "functionality_power_button", "functionality_touch", "functionality_usb"]
        self.test_sequence = self.original_test_sequence.copy()
        self.current_test_index = -1
        self.is_test_all_running = False
        
        # Parent widget reference for dialogs
        self.parent_widget = None
        
        # Add system log function
        self.add_system_log = None
        
        # result recorder callback function
        self.result_recorder = None
        self.progress_recorder = None
        
        # local temporary cache for UI display
        self.local_temp_results = {}
        self.local_temp_progress = {}
        
        # Define the tests that should remain disabled (In Dev tests)
        self.dev_tests = ["functionality_audio", "functionality_hdmi", "functionality_lcd", "functionality_power_button"]
        
        # connect signals
        self._connect_signals()
        
        logger.info("Test manager view initialized")
    
    def get_dev_tests_for_platform(self, platform_name):
        """根據平台名稱返回對應的開發中測試清單"""
        if platform_name in ["odin"]:
            return ["functionality_camera, functionality_hdmi"]
        else:
            return []  # 預設沒有 In Dev 測試
    
    def _connect_signals(self):
        """Connect hardware test manager signals"""
        # connect hardware test manager signals
        self.hw_test_manager.test_started.connect(self._on_test_started)
        self.hw_test_manager.test_completed.connect(self._on_test_completed)
        self.hw_test_manager.test_step_completed.connect(self._on_test_step_completed)
        self.hw_test_manager.test_step_retrying.connect(self._on_test_step_retrying)
        self.hw_test_manager.test_progress.connect(self._on_test_progress)
        
        # Connect new interaction signals
        self.hw_test_manager.test_pre_condition_required.connect(self._on_test_pre_condition_required)
        self.hw_test_manager.test_post_check_required.connect(self._on_test_post_check_required)
    
    def set_ui_components(self, test_container: TestContainer, test_all_button: QPushButton,
                          result_table: QTableWidget, progress_bar: QProgressBar, 
                          parent_widget=None, abort_button=None):
        """
        Set UI components references
        
        Args:
            test_container: Test container widget
            test_all_button: "Test All" button
            result_table: Table widget for displaying test steps
            progress_bar: Progress bar for displaying test progress
            parent_widget: Parent widget for dialogs
            abort_button: Abort test button
        """
        self.test_container = test_container
        self.test_all_button = test_all_button
        self.result_table = result_table
        self.progress_bar = progress_bar
        self.parent_widget = parent_widget
        self.abort_button = abort_button
        
        # Connect test container signals
        self.test_container.test_selected.connect(self.start_test)
        self.test_container.test_aborted_by_user.connect(self.abort_test)
        
        # Connect test all button
        self.test_all_button.clicked.connect(self.start_test_all)
        
        # Connect abort button if available
        if self.abort_button:
            self.abort_button.clicked.connect(self.abort_test)
            # Hide abort button by default
            self.abort_button.setVisible(False)
        
        # initialize test results and progress records
        test_ids = self.test_container.get_all_test_ids()
        for test_id in test_ids:
            self.local_temp_results[test_id] = {
                "steps": [],
                "success": None,
                "message": "",
                "start_time": None
            }
            self.local_temp_progress[test_id] = []
            
        # Set initial state for all tests
        for test_id in test_ids:
            # Skip the dev tests - they should always remain disabled
            if test_id in self.dev_tests:
                continue
            self.test_container.set_test_state(test_id, "not_started")
        
        # Ensure dev tests remain disabled after any state changes
        for test_id in self.dev_tests:
            test_widget = self.test_container.get_test_widget(test_id)
            if test_widget:
                test_widget.set_always_disabled(True)
    
    def start_test(self, test_id: str):
        """
        Start a specific test with pre-check if available
        
        Args:
            test_id: Test ID to start
        """
        logger.warning(f">>> TEST RESTART DETECTED <<< Starting test: {test_id}")
        # Immediately change button state for better user experience
        self.test_container.set_test_state(test_id, "running", "Checking...")
        
        # if there is a MainWindowController reference, use the pre-check
        if self.main_window_controller:
            self.main_window_controller.execute_functionality_test_with_pre_check(test_id)
        else:
            # directly execute the test (backward compatibility)
            self._start_test_directly(test_id)
    
    def _start_test_directly(self, test_id: str):
        """
        Directly start a specific test without pre-check
        
        Args:
            test_id: Test ID to start
        """
        # clear the result of the previous test
        if self.result_table:
            self.result_table.setRowCount(0)
        
        # Record test start time
        start_time = datetime.datetime.now()
        if test_id in self.local_temp_results:
            self.local_temp_results[test_id]["start_time"] = start_time
        else:
            self.local_temp_results[test_id] = {"steps": [], "success": None, "message": "", "start_time": start_time}
        
        # Set the log function and record all test steps commands in advance
        if self.add_system_log is not None and test_id in self.hw_test_manager.test_workers:
            worker = self.hw_test_manager.test_workers[test_id]
            worker.log_function = self.add_system_log
        
        # Show abort button
        if self.abort_button:
            self.abort_button.setVisible(True)

        # Start the test
        self.hw_test_manager.start_test(self.device_id, test_id)
        
        # Record the test start
        logger.info(f"Starting {test_id} test for device {self.device_id}")
    
    def start_test_all(self):
        """Start executing selected test modules in sequence with pre-check if available"""
        # Immediately change button state for better user experience
        if self.is_test_all_running:
            return
        
        # Disable the test all button and change text immediately
        if self.test_all_button:
            self.test_all_button.setEnabled(False)
            self.test_all_button.setText("Running...")
        
        # Show abort button
        if self.abort_button:
            self.abort_button.setVisible(True)
        
        # if there is a MainWindowController reference, use the pre-check
        if self.main_window_controller:
            self.main_window_controller.execute_functionality_test_with_pre_check()
        else:
            # directly execute the test (backward compatibility)
            self._start_test_all_directly()
    
    def _start_test_all_directly(self):
        """Directly start executing selected test modules in sequence without pre-check"""
        # Button state should already be changed in start_test_all()
        
        # create the test selection dialog - filter out dev tests
        available_tests = [t for t in self.original_test_sequence if t not in self.dev_tests]
        test_mapping = {test_id: test_id.replace("functionality_", "").capitalize() for test_id in available_tests}
        dialog = TestSelectionDialog(test_mapping, self.parent_widget)
        
        # show the dialog and wait for user selection
        if dialog.exec() != QDialog.Accepted:
            logger.info("Test sequence selection cancelled")
            # Reset button state since user cancelled
            self._reset_test_all_button_state()
            return
            
        # get the user selected test sequence
        selected_tests = dialog.get_selected_tests()
        if not selected_tests:
            logger.warning("No tests selected")
            # Reset button state since no tests selected
            self._reset_test_all_button_state()
            return
            
        # update the test sequence with the selected tests
        self.test_sequence = selected_tests
        logger.info(f"Selected tests: {', '.join(selected_tests)}")
            
        # clear the result of the previous test
        if self.result_table:
            self.result_table.setRowCount(0)
        
        # reset the test sequence
        self.current_test_index = -1
        self.is_test_all_running = True
        
        # start the first test
        self._execute_next_test()
        
        # record the test sequence start
        logger.info("Starting Test All sequence")
    
    def abort_test(self):
        """Abort the current running test"""
        logger.info(f"Aborting test for device {self.device_id}")
        
        # Stop the current test
        self.stop_current_test()
        
        # Reset test sequence state
        self.current_test_index = -1
        
        # Reset button state
        self._reset_test_all_button_state()
        
        # Notify MainWindowController about test abortion
        if self.main_window_controller:
            test_type = "Functionality Test All" if self.is_test_all_running else "Individual Functionality Test"
            self.main_window_controller._on_test_execution_aborted(test_type, "User aborted test")
    
    def stop_current_test(self):
        """Stop the currently running test"""
        if self.hw_test_manager:
            self.hw_test_manager.stop_current_test()
    
    @Slot(str)
    def _on_test_started(self, test_id: str):
        """
        Handle test started event
        
        Args:
            test_id: Test ID
        """
        # only handle the functionality tests
        if not test_id.startswith("functionality_"):
            return
            
        # update the test UI state
        self.test_container.set_test_state(test_id, "running")
        
        # Record start time
        start_time = datetime.datetime.now()
        
        # initialize the local temporary cache
        self.local_temp_results[test_id] = {
            "steps": [],
            "success": None,
            "message": "",
            "start_time": start_time
        }
        
        # clear the local progress record
        self.local_temp_progress[test_id] = []
        
        # Debug log for start time
        logger.debug(f"Test {test_id} started at {start_time}")
        
        logger.info(f"Test started: {test_id} for device {self.device_id}")

    @Slot(str, bool, str)
    def _on_test_completed(self, test_id: str, success: bool, message: str):
        """
        Handle test completed event
        
        Args:
            test_id: Test ID
            success: Whether test passed
            message: Result message
        """
        
        # only handle the functionality tests
        if not test_id.startswith("functionality_"):
            return
            
        # get the data from the local cache
        if test_id in self.local_temp_results:
            result_data = self.local_temp_results[test_id]
            result_data["success"] = success
            result_data["message"] = message
            
            # Calculate test duration
            start_time = result_data.get("start_time")
            if start_time:
                end_time = datetime.datetime.now()
                duration = end_time - start_time
                time_str = f"{duration.seconds}.{duration.microseconds//1000:03d}s"
                result_data["time"] = time_str
                logger.debug(f"Test {test_id} duration calculated: start={start_time}, end={end_time}, duration={time_str}")
            else:
                result_data["time"] = "--:--:--"
                logger.warning(f"Test {test_id} has no start_time record!")
            
            # record the result through the callback function
            if self.result_recorder:
                self.result_recorder("functionality", test_id, result_data)
        
        # update the test UI state
        self.test_container.set_test_state(test_id, "pass" if success else "fail", message)
        
        # Hide abort button if not running a test sequence
        if self.abort_button and not self.is_test_all_running:
            self.abort_button.setVisible(False)
        
        # Notify MainWindowController about individual test completion if not part of Test All
        if self.main_window_controller and not self.is_test_all_running:
            self.main_window_controller._on_individual_test_completed(test_id, "Functionality")
        
        # record the test completed
        if success:
            logger.info(f"Test {test_id} completed: {message}")
        else:
            logger.error(f"Test {test_id} completed: {message}")
        
        # if we are running the test sequence, execute the next test
        if self.is_test_all_running:
            QTimer.singleShot(1000, self._execute_next_test)  # wait 1 second before starting the next test

    @Slot(str, int, bool, str)
    def _on_test_step_completed(self, test_id: str, step_index: int, success: bool, message: str):
        """
        Handle test step completed event
        
        Args:
            test_id: Test ID
            step_index: Step index
            success: Whether step passed
            message: Step result message
        """
        # only handle the functionality tests
        if not test_id.startswith("functionality_"):
            return
            
        # Calculate the execution time of the step
        step_time = "--:--:--"
        step_end_time = datetime.datetime.now()
        step_start_time = None
        
        # Strategy 1: Check if we have a stored step start time from the active worker
        if test_id == self.hw_test_manager.active_test_id and self.hw_test_manager.active_test_worker:
            active_worker = self.hw_test_manager.active_test_worker
            if hasattr(active_worker, 'steps') and len(active_worker.steps) > step_index:
                step = active_worker.steps[step_index]
                if hasattr(step, 'start_time') and step.start_time:
                    step_start_time = step.start_time
                    logger.debug(f"Found step start_time from active worker: {step_start_time}")
        
        # Strategy 2: Look for step start from progress records with current step
        if step_start_time is None:
            current_records = self.local_temp_progress.get(test_id, [])
            for record in current_records:
                if record.get('current_step') == step_index + 1:  # current_step starts from 1
                    if 'timestamp' in record:
                        try:
                            step_start_time = datetime.datetime.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
                            logger.debug(f"Found step start_time from progress record timestamp: {step_start_time}")
                            break
                        except Exception as e:
                            logger.debug(f"Failed to parse timestamp {record['timestamp']}: {e}")
                            pass
        
        # Strategy 3: Use previous step's completion time as approximation
        if step_start_time is None and test_id in self.local_temp_results:
            test_steps = self.local_temp_results[test_id].get("steps", [])
            # Look for the previous step's end time
            for step_data in reversed(test_steps):
                if step_data.get('index', -1) < step_index and 'end_time' in step_data:
                    step_start_time = step_data['end_time']
                    logger.debug(f"Using previous step's end_time as start_time: {step_start_time}")
                    break
        
        # Strategy 4: Use test start time with step offset estimation
        if step_start_time is None and test_id in self.local_temp_results:
            test_data = self.local_temp_results[test_id]
            if 'start_time' in test_data:
                try:
                    if isinstance(test_data['start_time'], str):
                        test_start = datetime.datetime.strptime(test_data['start_time'], "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        test_start = test_data['start_time']
                    
                    # Estimate step start time by adding some time for previous steps
                    # Assume each step takes about 5 seconds on average
                    estimated_offset = step_index * 5
                    step_start_time = test_start + datetime.timedelta(seconds=estimated_offset)
                    logger.debug(f"Estimated step start_time from test start: {step_start_time} (offset: {estimated_offset}s)")
                except Exception as e:
                    logger.debug(f"Failed to use test start_time: {e}")
                    pass
        
        # Strategy 5: Use a default duration if we still can't find start time
        if step_start_time is None:
            # Assume the step took 5 seconds by default
            step_start_time = step_end_time - datetime.timedelta(seconds=5)
            logger.debug(f"Using default 5s duration, estimated start_time: {step_start_time}")
                        
        # calculate the duration of the step
        if step_start_time:
            try:
                duration = step_end_time - step_start_time
                total_seconds = max(0, duration.total_seconds())  # Ensure non-negative duration
                step_time = f"{total_seconds:.2f}s"
                logger.debug(f"Step {step_index+1} time: {step_time}, start: {step_start_time}, end: {step_end_time}")
            except Exception as e:
                logger.warning(f"Failed to calculate step duration: {e}")
                step_time = "5.00s"  # Default fallback
        else:
            step_time = "5.00s"  # Default fallback
            logger.debug(f"Using default duration for step {step_index+1}: {step_time}")
        
        # store the step results
        if test_id in self.local_temp_results:
            # get the step command and response
            command = ""
            response = ""
            step_desc = ""
            step_specification = ""
            step_criteria = ""
            
            # try to get the step command and response from the active test worker
            if test_id == self.hw_test_manager.active_test_id and self.hw_test_manager.active_test_worker:
                active_worker = self.hw_test_manager.active_test_worker
                if hasattr(active_worker, 'steps') and len(active_worker.steps) > step_index:
                    step = active_worker.steps[step_index]
                    if hasattr(step, 'description'):
                        step_desc = step.description
                        logger.debug(f"Found description from active worker: '{step_desc}'")
                    if hasattr(step, 'command'):
                        command = step.command
                        logger.debug(f"Found command from active worker: '{command}'")
                    if hasattr(step, 'response') and step.response:
                        response = step.response
                        logger.debug(f"Found response from active worker: '{response}'")
                    elif hasattr(step, 'result') and step.result:
                        response = step.result
                        logger.debug(f"Found result from active worker: '{response}'")
                    # get the specification and criteria
                    if hasattr(step, 'specification'):
                        step_specification = step.specification
                        logger.debug(f"Found specification from active worker: '{step_specification}'")
                    if hasattr(step, 'criteria'):
                        step_criteria = step.criteria
                        logger.debug(f"Found criteria from active worker: '{step_criteria}'")
            
            # if failed to get the step command and response from the active test worker, try to get them from the registered test worker
            if (not step_desc or not command or not response) and test_id in self.hw_test_manager.test_workers:
                registered_worker = self.hw_test_manager.test_workers[test_id]
                if hasattr(registered_worker, 'steps') and len(registered_worker.steps) > step_index:
                    step = registered_worker.steps[step_index]
                    if not step_desc and hasattr(step, 'description'):
                        step_desc = step.description
                        logger.debug(f"Found description from registered worker: '{step_desc}'")
                    if not command and hasattr(step, 'command'):
                        command = step.command
                        logger.debug(f"Found command from registered worker: '{command}'")
                    if not response:
                        if hasattr(step, 'response') and step.response:
                            response = step.response
                            logger.debug(f"Found response from registered worker: '{response}'")
                        elif hasattr(step, 'result') and step.result:
                            response = step.result
                            logger.debug(f"Found result from registered worker: '{response}'")
                    # get the specification and criteria
                    if not step_specification and hasattr(step, 'specification'):
                        step_specification = step.specification
                        logger.debug(f"Found specification from registered worker: '{step_specification}'")
                    if not step_criteria and hasattr(step, 'criteria'):
                        step_criteria = step.criteria
                        logger.debug(f"Found criteria from registered worker: '{step_criteria}'")
            
            # correct the step message: for manual steps, ensure the correct PASS/FAIL status is saved
            final_message = message
            
            # check if the step is a manual step and the message needs to be corrected
            is_manual_step = False
            if test_id == self.hw_test_manager.active_test_id and self.hw_test_manager.active_test_worker:
                active_worker = self.hw_test_manager.active_test_worker
                if hasattr(active_worker, 'steps') and len(active_worker.steps) > step_index:
                    step = active_worker.steps[step_index]
                    is_manual_step = hasattr(step, 'manual_only') and step.manual_only
                    
                    # for manual steps, if the message is "No command specified", set the correct message based on the success status
                    if is_manual_step and message == "No command specified":
                        final_message = "PASS" if success else "FAIL"
                        logger.debug(f"Corrected manual step message for step {step_index+1}: '{final_message}'")
                        
                    # also ensure the manual steps have the correct handling of other status messages
                    elif is_manual_step and message in ["Step passed based on human judgement", "Step failed based on human judgement"]:
                        final_message = "PASS" if success else "FAIL"
                        logger.debug(f"Simplified manual step message for step {step_index+1}: '{final_message}'")
            
            # record the final collected information
            logger.debug(f"Step data collected - Test: {test_id}, Step: {step_index+1}, Desc: '{step_desc}', Cmd: '{command}', Response length: {len(response)}")
            
            step_data = {
                "index": step_index,
                "success": success,
                "message": final_message,  # use the corrected message
                "description": step_desc,  # add step description
                "time": step_time,
                "start_time": step_start_time,
                "end_time": step_end_time,
                "command": command,      # add command
                "response": response,    # add response
                "specification": step_specification,  # add specification
                "criteria": step_criteria     # add criteria
            }
            
            logger.debug(f"Storing step_data for step {step_index+1}: time='{step_time}', start_time='{step_start_time}', end_time='{step_end_time}'")
            
            # check if there is an existing step record with the same index, if so, update it, otherwise add a new record
            existing_step_index = None
            for i, existing_step in enumerate(self.local_temp_results[test_id]["steps"]):
                if existing_step.get("index") == step_index:
                    existing_step_index = i
                    break
            
            if existing_step_index is not None:
                # update the existing record
                self.local_temp_results[test_id]["steps"][existing_step_index] = step_data
                logger.debug(f"Updated existing step record for step {step_index+1}: '{final_message}'")
            else:
                # add a new record
                self.local_temp_results[test_id]["steps"].append(step_data)
                logger.debug(f"Added new step record for step {step_index+1}: '{final_message}'")
        
        # update the test step UI
        if self.result_table:
            table = self.result_table
            row = table.rowCount()
            table.insertRow(row)
            
            # get the step description
            step_description = f"Step {step_index+1}"  # default display step number
            
            # try to get the step description from the active test worker
            if test_id == self.hw_test_manager.active_test_id and self.hw_test_manager.active_test_worker:
                active_worker = self.hw_test_manager.active_test_worker
                if hasattr(active_worker, 'steps') and len(active_worker.steps) > step_index:
                    step = active_worker.steps[step_index]
                    if hasattr(step, 'description') and step.description:
                        step_description = step.description
            
            # if failed to get the step description from the active test worker, try to get it from the registered test worker
            if step_description == f"Step {step_index+1}" and test_id in self.hw_test_manager.test_workers:
                registered_worker = self.hw_test_manager.test_workers[test_id]
                if hasattr(registered_worker, 'steps') and len(registered_worker.steps) > step_index:
                    step = registered_worker.steps[step_index]
                    if hasattr(step, 'description') and step.description:
                        step_description = step.description
            
            # add the step details
            table.setItem(row, 0, QTableWidgetItem(step_description))
            table.setItem(row, 1, QTableWidgetItem("Pass" if success else "Fail"))
            table.setItem(row, 2, QTableWidgetItem(message))
            
            # set the row color
            color = QColor("#00AA00") if success else QColor("#FF0000")
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setForeground(color)
            
            # scroll to the latest item
            table.scrollToBottom()
        
        # record the step completed
        if success:
            logger.info(f"Test {test_id} step {step_index+1}: {message}")
        else:
            logger.warning(f"Test {test_id} step {step_index+1}: {message}")
    
    @Slot(str, int, int, int, str)
    def _on_test_step_retrying(self, test_id: str, step_index: int, retry_count: int, max_retries: int, error: str):
        """
        Handle test step retry event
        
        Args:
            test_id: Test ID
            step_index: Step index
            retry_count: Current retry count
            max_retries: Maximum retry count
            error: Error message
        """
        # record the retry
        logger.warning(f"Test {test_id} step {step_index+1} retrying ({retry_count}/{max_retries}): {error}")
    
    @Slot(str, int, int)
    def _on_test_progress(self, test_id: str, current_step: int, total_steps: int):
        """
        Handle test progress update
        
        Args:
            test_id: Test ID
            current_step: Current step index (1-based)
            total_steps: Total number of steps
        """
        try:
            # Calculate progress percentage
            progress_pct = int((current_step / total_steps) * 100) if total_steps > 0 else 0
            
            # Update progress in container
            if hasattr(self.test_container, 'set_test_progress'):
                self.test_container.set_test_progress(test_id, progress_pct)
            
            # Create progress data
            progress_data = {
                'test_id': test_id,
                'current_step': current_step,
                'total_steps': total_steps,
                'progress_percent': progress_pct,
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Record progress through callback
            if self.progress_recorder:
                self.progress_recorder("functionality", test_id, progress_data)
            
            # Update progress bar if available
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.progress_bar.setValue(progress_pct)
                self.progress_bar.setVisible(True)
        except Exception as e:
            # error handling, ensure the test will not be interrupted due to progress display issues
            logger.error(f"Error updating test progress: {str(e)}")
    
    def _execute_next_test(self):
        """Execute next test in the sequence"""
        self.current_test_index += 1
        
        # check if all tests are completed
        if self.current_test_index >= len(self.test_sequence):
            self._complete_test_all()
            return
            
        # get the next test ID
        test_id = self.test_sequence[self.current_test_index]
        
        # start the test directly (already passed the pre-check)
        self._start_test_directly(test_id)

    def _reset_test_all_button_state(self):
        """Reset Test All button to its initial state"""
        self.is_test_all_running = False
        
        # enable the test all button
        if self.test_all_button:
            self.test_all_button.setEnabled(True)
            self.test_all_button.setText("Test All")
        
        # Hide abort button
        if self.abort_button:
            self.abort_button.setVisible(False)

    def _complete_test_all(self):
        """Complete Test All sequence"""
        self.current_test_index = -1
        
        # Reset button state
        self._reset_test_all_button_state()
        
        # record the completion
        logger.info("Test All sequence completed")
        
        # emit the all tests completed signal
        self.all_tests_completed.emit()
    
    def clear_test_results(self):
        """
        Clear all test results and progress records
        Used after exporting results to avoid accumulating old data
        """
        # clear the local cache
        self.local_temp_results.clear()
        self.local_temp_progress.clear()
        
        # Get all test IDs from the test container
        if self.test_container:
            test_ids = self.test_container.get_all_test_ids()
            
            # Reset UI state to not started
            for test_id in test_ids:
                if test_id in self.dev_tests:
                    # Ensure dev tests remain disabled and show "In Dev"
                    test_widget = self.test_container.get_test_widget(test_id)
                    if test_widget:
                        test_widget.set_always_disabled(True)
                else:
                    self.test_container.set_test_state(test_id, "not_started")
        
        logger.info("Test results and progress records cleared")
    
    def cleanup(self):
        """Clean up test manager resources"""
        try:
            logger.debug("Cleaning up TestManagerView resources")
            
            # disconnect all signals
            try:
                self.hw_test_manager.test_started.disconnect(self._on_test_started)
                self.hw_test_manager.test_completed.disconnect(self._on_test_completed)
                self.hw_test_manager.test_step_completed.disconnect(self._on_test_step_completed)
                self.hw_test_manager.test_step_retrying.disconnect(self._on_test_step_retrying)
                self.hw_test_manager.test_progress.disconnect(self._on_test_progress)
                
                if self.test_container:
                    self.test_container.test_selected.disconnect(self.start_test)
                
                if self.test_all_button:
                    self.test_all_button.clicked.disconnect(self.start_test_all)
            except Exception:
                # signals may already be disconnected, ignore the error
                pass
            
            # clear the references
            self.test_container = None
            self.test_all_button = None
            self.result_table = None
            self.progress_bar = None
            
        except Exception as e:
            logger.error(f"Error during TestManagerView cleanup: {e}") 

    def set_test_buttons_enabled(self, enabled=True):
        """
        Enable or disable all test buttons
        
        Args:
            enabled: Whether to enable the buttons
        """
        if self.test_container:
            for test_id in self.test_container.get_all_test_ids():
                test_widget = self.test_container.get_test_widget(test_id)
                if test_widget:
                    if test_id in self.dev_tests:
                        # Ensure dev tests remain disabled and show "In Dev"
                        test_widget.set_always_disabled(True)
                    else:
                        test_widget.set_enabled(enabled)
            
        # Enable or disable "Test All" button
        if self.test_all_button:
            self.test_all_button.setEnabled(enabled)
    
    @Slot(str, int, str)
    def _on_test_pre_condition_required(self, test_id: str, step_index: int, pre_condition: str):
        """
        Handle test pre-condition required event
        
        Args:
            test_id: Test ID
            step_index: Step index
            pre_condition: Pre-condition instructions
        """
        logger.debug(f"Pre-condition required for test {test_id}, step {step_index}: {pre_condition}")
        
        if not self.parent_widget:
            # No parent widget to show dialog, continue automatically
            self.hw_test_manager.handle_pre_condition_response(test_id, step_index, True)
            return
            
        # Create and show pre-condition dialog
        msg_box = QMessageBox(self.parent_widget)
        msg_box.setWindowTitle("Pre-condition required")
        msg_box.setText(f"Step {step_index + 1} preparation:")
        msg_box.setInformativeText(pre_condition)
        msg_box.setIcon(QMessageBox.Information)
        
        # Set the dark style sheet
        msg_box.setStyleSheet(self._get_dark_style_sheet())
        
        # Add custom buttons
        confirm_button = msg_box.addButton("Confirm and continue", QMessageBox.AcceptRole)
        skip_button = msg_box.addButton("Skip", QMessageBox.RejectRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.DestructiveRole)
        
        # Make buttons larger for easier clicking
        confirm_button.setMinimumSize(150, 30)
        skip_button.setMinimumSize(100, 30)
        cancel_button.setMinimumSize(100, 30)
        
        # Set minimum width
        msg_box.setMinimumWidth(450)
        
        # Adjust the width of the text label in the message box
        for label in msg_box.findChildren(QLabel):
            if label.text() == pre_condition:
                # Set the width of the text label and enable word wrap
                label.setMinimumWidth(350)
                label.setWordWrap(True)
        
        # Show dialog
        msg_box.exec()
        
        # Handle response
        clicked_button = msg_box.clickedButton()
        if clicked_button == confirm_button:
            self.hw_test_manager.handle_pre_condition_response(test_id, step_index, True)
        elif clicked_button == skip_button:
            self.hw_test_manager.handle_pre_condition_response(test_id, step_index, False)
        else:  # cancel_button or dialog closed
            self.hw_test_manager.handle_pre_condition_cancel(test_id, step_index)
    
    @Slot(str, int, str)
    def _on_test_post_check_required(self, test_id: str, step_index: int, post_check: str):
        """
        Handle test post-check required event
        
        Args:
            test_id: Test ID
            step_index: Step index
            post_check: Post-check instructions
        """
        logger.debug(f"Post-check required for test {test_id}, step {step_index}: {post_check}")
        
        if not self.parent_widget:
            # No parent widget to show dialog, continue automatically
            self.hw_test_manager.handle_post_check_response(test_id, step_index, True)
            return
            
        # Create and show post-check dialog
        msg_box = QMessageBox(self.parent_widget)
        msg_box.setWindowTitle("Result confirmation")
        msg_box.setText(f"Step {step_index + 1} verification:")
        msg_box.setInformativeText(post_check)
        msg_box.setIcon(QMessageBox.Question)
        
        # Set the dark style sheet with wider dimensions
        style_sheet = self._get_dark_style_sheet()
        msg_box.setStyleSheet(style_sheet)
        
        # Add custom buttons
        pass_button = msg_box.addButton("Pass", QMessageBox.AcceptRole)
        fail_button = msg_box.addButton("Fail", QMessageBox.RejectRole)
        
        # Make buttons larger for easier clicking
        pass_button.setMinimumSize(100, 30)
        fail_button.setMinimumSize(100, 30)
        
        # Set fixed width
        msg_box.setMinimumWidth(450)
        
        # Adjust the width of the text label in the message box
        for label in msg_box.findChildren(QLabel):
            if label.text() == post_check:
                # Set the width of the text label and enable word wrap
                label.setMinimumWidth(350)
                label.setWordWrap(True)
        
        # Show dialog
        msg_box.exec()
        
        # Handle response
        clicked_button = msg_box.clickedButton()
        self.hw_test_manager.handle_post_check_response(
            test_id, step_index, clicked_button == pass_button)

    def _get_dark_style_sheet(self):
        """Return the dark style sheet"""
        return """
            QMessageBox {
                background-color: #2E2E2E;
                color: white;
                min-width: 400px;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
            QPushButton:pressed {
                background-color: #00559F;
            }
        """ 

    def set_result_recorders(self, result_recorder, progress_recorder):
        """set the result recorder and progress recorder callback functions
        
        Args:
            result_recorder: result recorder callback function
            progress_recorder: progress recorder callback function
        """
        self.result_recorder = result_recorder
        self.progress_recorder = progress_recorder
        
        logger.debug("Test manager result recorders set")
    
    def reset_ui(self):
        """reset the UI status - called by MainWindowController"""
        # clear the local cache
        self.local_temp_results.clear()
        self.local_temp_progress.clear()
        
        # reset the UI status of all the test items
        if self.test_container:
            test_ids = self.test_container.get_all_test_ids()
            
            for test_id in test_ids:
                if test_id in self.dev_tests:
                    # Ensure dev tests remain disabled and show "In Dev"
                    test_widget = self.test_container.get_test_widget(test_id)
                    if test_widget:
                        test_widget.set_always_disabled(True)
                else:
                    self.test_container.set_test_state(test_id, "not_started") 