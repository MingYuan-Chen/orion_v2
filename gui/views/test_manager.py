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
        
        # test UI components reference
        self.test_container = None  # test container reference
        self.test_all_button = None  # test all button reference 
        self.result_table = None  # test result table reference
        self.progress_bar = None  # test progress bar reference
        self.abort_button = None  # abort button reference
        
        # test sequence related
        self.original_test_sequence = ["functionality_audio", "functionality_backlight", "functionality_battery",
                                       "functionality_camera", "functionality_charge", "functionality_eeprom", "functionality_emmc", "functionality_lcd",
                                       "functionality_led", "functionality_power_button", "functionality_touch", "functionality_usb"]
        self.test_sequence = self.original_test_sequence.copy()
        self.current_test_index = -1
        self.is_test_all_running = False
        
        # Parent widget reference for dialogs
        self.parent_widget = None
        
        # Add system log function
        self.add_system_log = None
        
        # 結果記錄回調函數，由MainWindowController設置
        self.result_recorder = None
        self.progress_recorder = None
        
        # 本地臨時緩存用於UI顯示
        self.local_temp_results = {}
        self.local_temp_progress = {}
        
        # connect signals
        self._connect_signals()
        
        logger.info("Test manager view initialized")
    
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
            self.test_container.set_test_state(test_id, "not_started")
    
    def start_test(self, test_id: str):
        """
        Start a specific test
        
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
        
        # Start the test
        self.hw_test_manager.start_test(self.device_id, test_id)
        
        # Show abort button
        if self.abort_button:
            self.abort_button.setVisible(True)
        
        # Record the test start
        logger.info(f"Starting {test_id} test for device {self.device_id}")
    
    def start_test_all(self):
        """Start executing selected test modules in sequence"""
        # if the test sequence is already running, ignore this call
        if self.is_test_all_running:
            return
            
        # create the test selection dialog - always use the original test sequence
        test_mapping = {test_id: test_id.replace("functionality_", "").capitalize() for test_id in self.original_test_sequence}
        dialog = TestSelectionDialog(test_mapping, self.parent_widget)
        
        # show the dialog and wait for user selection
        if dialog.exec() != QDialog.Accepted:
            logger.info("Test sequence selection cancelled")
            return
            
        # get the user selected test sequence
        selected_tests = dialog.get_selected_tests()
        if not selected_tests:
            logger.warning("No tests selected")
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
        
        # disable the test all button
        if self.test_all_button:
            self.test_all_button.setEnabled(False)
            self.test_all_button.setText("Running...")
        
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
        self.is_test_all_running = False
        self.current_test_index = -1
        
        # Enable the test all button
        if self.test_all_button:
            self.test_all_button.setEnabled(True)
            self.test_all_button.setText("Test All")
        
        # Hide abort button
        if self.abort_button:
            self.abort_button.setVisible(False)
    
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
        
        # get the start time of the step
        step_start_time = None
        current_records = self.local_temp_progress.get(test_id, [])
        for record in current_records:
            if record.get('current_step') == step_index + 1:  # current_step starts from 1
                if 'start_time' in record:
                    step_start_time = record['start_time']
                    break
        
        # if the start time of the step is not found, use the latest progress record time
        if step_start_time is None and current_records:
            for record in reversed(current_records):
                if 'timestamp' in record:
                    try:
                        step_start_time = datetime.datetime.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
                        break
                    except:
                        pass
                        
        # calculate the duration of the step
        if step_start_time:
            duration = step_end_time - step_start_time
            step_time = f"{duration.seconds}.{duration.microseconds//1000:02d}s"
            logger.debug(f"Step {step_index+1} time: {step_time}, start: {step_start_time}, end: {step_end_time}")
        
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
                    # 获取规格与标准
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
                    # 获取规格与标准
                    if not step_specification and hasattr(step, 'specification'):
                        step_specification = step.specification
                        logger.debug(f"Found specification from registered worker: '{step_specification}'")
                    if not step_criteria and hasattr(step, 'criteria'):
                        step_criteria = step.criteria
                        logger.debug(f"Found criteria from registered worker: '{step_criteria}'")
            
            # 修正步骤消息：对于手动步骤，确保保存正确的PASS/FAIL状态
            final_message = message
            
            # 检查是否是手动步骤且消息需要修正
            is_manual_step = False
            if test_id == self.hw_test_manager.active_test_id and self.hw_test_manager.active_test_worker:
                active_worker = self.hw_test_manager.active_test_worker
                if hasattr(active_worker, 'steps') and len(active_worker.steps) > step_index:
                    step = active_worker.steps[step_index]
                    is_manual_step = hasattr(step, 'manual_only') and step.manual_only
                    
                    # 对于手动步骤，如果消息是"No command specified"，则根据success状态设置正确的消息
                    if is_manual_step and message == "No command specified":
                        final_message = "PASS" if success else "FAIL"
                        logger.debug(f"Corrected manual step message for step {step_index+1}: '{final_message}'")
                        
                    # 同时确保手动步骤也有其他状态消息的正确处理
                    elif is_manual_step and message in ["Step passed based on human judgement", "Step failed based on human judgement"]:
                        final_message = "PASS" if success else "FAIL"
                        logger.debug(f"Simplified manual step message for step {step_index+1}: '{final_message}'")
            
            # record the final collected information
            logger.debug(f"Step data collected - Test: {test_id}, Step: {step_index+1}, Desc: '{step_desc}', Cmd: '{command}', Response length: {len(response)}")
            
            step_data = {
                "index": step_index,
                "success": success,
                "message": final_message,  # 使用修正后的消息
                "description": step_desc,  # add step description
                "time": step_time,
                "start_time": step_start_time,
                "end_time": step_end_time,
                "command": command,      # add command
                "response": response,    # add response
                "specification": step_specification,  # 添加规格
                "criteria": step_criteria     # 添加标准
            }
            
            # 检查是否已存在相同索引的步骤记录，如果存在则更新，否则添加新记录
            existing_step_index = None
            for i, existing_step in enumerate(self.local_temp_results[test_id]["steps"]):
                if existing_step.get("index") == step_index:
                    existing_step_index = i
                    break
            
            if existing_step_index is not None:
                # 更新现有记录
                self.local_temp_results[test_id]["steps"][existing_step_index] = step_data
                logger.debug(f"Updated existing step record for step {step_index+1}: '{final_message}'")
            else:
                # 添加新记录
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
        
        # start the test
        self.start_test(test_id)

    def _complete_test_all(self):
        """Complete Test All sequence"""
        self.is_test_all_running = False
        self.current_test_index = -1
        
        # enable the test all button
        if self.test_all_button:
            self.test_all_button.setEnabled(True)
            self.test_all_button.setText("Test All")
        
        # Hide abort button when all tests are completed
        if self.abort_button:
            self.abort_button.setVisible(False)
        
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
                self.test_container.get_test_widget(test_id).set_enabled(enabled)
            
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
                self.test_container.set_test_state(test_id, "not_started") 