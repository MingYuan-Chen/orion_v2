"""
Auto diagnostic view module
Responsible for managing diagnostic test execution and UI updates
"""

from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
from typing import Dict, List, Any, Optional
import datetime

from core.services.hardware_test_manager import HardwareTestManagerService
from gui.widgets.diagnostic_container import DiagnosticContainer
from util.logger import logger

class AutoDiagnosticView(QObject):
    """
    Auto diagnostic view controller
    Manages diagnostic test execution and UI updates
    """
    
    # define signals
    all_diagnostics_completed = Signal()  # when all the diagnostic tests are completed
    export_report_requested = Signal()    # when the export report is requested
    
    def __init__(self, device_id: str, hw_test_manager: HardwareTestManagerService):
        """
        initialize the auto diagnostic view
        
        Args:
            device_id: the device id
            hw_test_manager: the hardware test manager service
        """
        super().__init__()
        
        # save the device id and hardware test manager
        self.device_id = device_id
        self.hw_test_manager = hw_test_manager
        
        # MainWindowController reference (set later)
        self.main_window_controller = None
        
        # UI components references
        self.main_widget = None
        self.diagnostic_container = None
        self.run_all_button = None
        self.export_button = None
        self.title_label = None
        
        # result recorder callback function, set by MainWindowController
        self.result_recorder = None
        self.progress_recorder = None
        
        # local temporary cache for UI display
        self.local_diagnostic_results = {}
        self.current_diagnostics = []
        self.is_running = False
        
        # connect signals
        self._connect_signals()
        
        logger.info("Auto diagnostic view initialized")
    
    def set_result_recorders(self, result_recorder, progress_recorder):
        """set the result recorder callback function"""
        self.result_recorder = result_recorder
        self.progress_recorder = progress_recorder
    
    def _connect_signals(self):
        """connect the hardware test manager signals"""
        # connect the hardware test manager signals
        self.hw_test_manager.test_started.connect(self._on_test_started)
        self.hw_test_manager.test_completed.connect(self._on_test_completed)
        self.hw_test_manager.test_progress.connect(self._on_test_progress)
        # connect the step completed signal
        self.hw_test_manager.test_step_completed.connect(self._on_test_step_completed)
    
    def create_widget(self) -> QWidget:
        """
        create and return the auto diagnostic main widget
        
        Returns:
            QWidget: the auto diagnostic main widget
        """
        # create the main widget
        self.main_widget = QWidget()
        self.main_widget.setObjectName("diagnosticWidget")
        self.main_widget.setStyleSheet("""
            QWidget#diagnosticWidget {
                background-color: #1E1E1E;
                color: white;
                border-radius: 5px;
            }
            QLabel#titleLabel {
                font-weight: bold;
                font-size: 14px;
                color: #4FC3F7;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
        """)
        
        # create the main layout
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(5)
        
        # create the top layout (title and buttons)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 10, 10, 10)
        
        # title
        self.title_label = QLabel("Auto Diagnostic")
        self.title_label.setObjectName("titleLabel")
        top_layout.addWidget(self.title_label)
        
        # add stretch
        top_layout.addStretch()
        
        # export report button
        self.export_button = QPushButton("Export Report")
        self.export_button.clicked.connect(self._on_export_report)
        top_layout.addWidget(self.export_button)
        
        # spacing
        top_layout.addSpacing(10)
        
        # run all tests button
        self.run_all_button = QPushButton("Run All Tests")
        self.run_all_button.clicked.connect(self._on_run_all_tests)
        top_layout.addWidget(self.run_all_button)
        
        # add the top layout to the main layout
        main_layout.addLayout(top_layout)
        
        # add the separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #333333;")
        line.setMaximumHeight(1)
        main_layout.addWidget(line)
        
        # create the diagnostic container
        self.diagnostic_container = DiagnosticContainer()
        
        # calculate the item height and visible items number
        item_height = 32  # the height of each diagnostic item
        visible_items = 5  # the number of visible items
        
        # set the diagnostic container height - fixed height regardless of content
        scroll_height = item_height * visible_items
        self.diagnostic_container.set_fixed_height(scroll_height)
        
        # add the diagnostic container to the main layout
        main_layout.addWidget(self.diagnostic_container)
        
        # set the main widget fixed height - always the same regardless of content
        title_area_height = 60  # the title area is about 60 pixels
        separator_height = 1
        total_height = title_area_height + separator_height + scroll_height
        
        # force set the fixed height, ensure it does not change with content
        self.main_widget.setFixedHeight(total_height)
        self.main_widget.setMinimumHeight(total_height)
        self.main_widget.setMaximumHeight(total_height)
        
        # set the SizePolicy, prevent the layout from stretching
        self.main_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        return self.main_widget
    
    def setup_diagnostic_items(self, diagnostic_tests):
        """
        setup the diagnostic test items
        
        Args:
            diagnostic_tests: a dictionary, the key is the test id, the value is the test name
        """
        # clear the existing items
        if self.diagnostic_container:
            for test_id in self.diagnostic_container.get_all_test_ids():
                # remove the item (not implemented, because DiagnosticContainer has no remove method)
                pass
        
        # add the diagnostic test items
        for test_id, test_name in diagnostic_tests.items():
            self.diagnostic_container.add_diagnostic_item(test_id, test_name)
            self.local_diagnostic_results[test_id] = {
                "status": "PENDING",
                "time": "--:--:--",
                "details": {
                    "message": ""
                },
                "start_time": datetime.datetime.now()
            }
            
        # record all the diagnostic items
        self.current_diagnostics = list(diagnostic_tests.keys())
    
    def _on_run_all_tests(self):
        """handle the run all tests button click with pre-check if available"""
        # Immediately change button state for better user experience
        if self.is_running:
            return
            
        self.is_running = True
        self.run_all_button.setText("Running...")
        self.run_all_button.setEnabled(False)
        
        # Reset all diagnostic items status
        self.diagnostic_container.reset_all_items()
        
        # if there is a MainWindowController reference, use pre-check
        if self.main_window_controller:
            self.main_window_controller.execute_auto_diagnostic_with_pre_check()
        else:
            # directly execute the diagnostic (backward compatibility)
            self._run_all_tests_directly()
    
    def _run_all_tests_directly(self):
        """Directly handle the run all tests button click without pre-check"""
        # Button state should already be changed in _on_run_all_tests()
        # Just start the test sequence
        self._run_diagnostic_sequence()
        
        logger.info("Starting auto diagnostic sequence")
    
    def _run_diagnostic_sequence(self):
        """start running the diagnostic sequence"""
        # reset the diagnostic results, don't modify status, we need to show diagnostics that have already been run
        self.pending_tests = self.current_diagnostics.copy()
        
        # if no tests, complete immediately
        if not self.pending_tests:
            self._complete_all_diagnostics()
            return
            
        # start the first test
        self._start_test(self.pending_tests.pop(0))
    
    def _start_test(self, test_id):
        """start a test in the diagnostic sequence"""
        # reset the diagnostic status
        self.diagnostic_container.update_item_status(test_id, "PENDING")
        
        # execute the test
        self._execute_test(test_id)
    
    def _execute_test(self, test_id):
        """execute the test"""
        try:
            # Pass the log recording function to the test worker
            if test_id in self.hw_test_manager.test_workers:
                worker = self.hw_test_manager.test_workers[test_id]
                # Set the log recording function
                if hasattr(self, 'add_system_log'):
                    # Ensure the log function is set
                    worker.log_function = self.add_system_log
                    
                    # Record all the test steps commands
                    if hasattr(worker, 'steps') and worker.steps:
                        for step in worker.steps:
                            if hasattr(step, 'command') and step.command:
                                self.add_system_log("INFO", f"[Command][{test_id}] {step.command}")
                    
                    # Set response collector function
                    if hasattr(worker, 'set_response_collector'):
                        # create the response collector function
                        def response_collector(test_id, step_index, command, response):
                            self.add_system_log("INFO", f"[Response][{test_id}] {response}")
                        
                        # set the response collector
                        worker.set_response_collector(response_collector)
            
            # start the test
            self.hw_test_manager.start_test(self.device_id, test_id)
            
            # record the start time
            start_time = datetime.datetime.now()
            self.local_diagnostic_results[test_id]["start_time"] = start_time
            
            # ensure we scroll to the current test item
            self.diagnostic_container.scroll_to_item(test_id)
            
            logger.info(f"Test {test_id} execution started")
        except Exception as e:
            logger.error(f"Error executing test {test_id}: {str(e)}")
            # if the error occurs when executing the test, try to continue with the next test
            if hasattr(self, 'pending_tests') and self.pending_tests:
                next_test = self.pending_tests.pop(0)
                self._start_test(next_test)
    
    def _on_export_report(self):
        """handle the export report button click"""
        # emit the export report requested signal
        self.export_report_requested.emit()
        
        logger.info("Export diagnostic report requested")
    
    @Slot(str)
    def _on_test_started(self, test_id: str):
        """
        handle the test started event
        
        Args:
            test_id: the test id
        """
        # only handle the diagnostic tests
        if not test_id.startswith("diagnostic_") or test_id not in self.current_diagnostics:
            return
            
        # update the UI status
        self.diagnostic_container.update_item_status(test_id, "PENDING")
        
        # scroll to the test item being executed
        self.diagnostic_container.scroll_to_item(test_id)
        
        # initialize the local result cache
        self.local_diagnostic_results[test_id] = {
            "status": "PENDING",
            "time": "--:--:--",
            "details": {
                "message": ""
            },
            "start_time": datetime.datetime.now(),
            "steps": []  # initialize the steps list
        }
        
        logger.info(f"Diagnostic test started: {test_id}")
    
    @Slot(str, bool, str)
    def _on_test_completed(self, test_id: str, success: bool, message: str):
        """
        handle the test completed event
        
        Args:
            test_id: the test id
            success: whether the test is successful
            message: the result message
        """
        # only handle the diagnostic tests
        if not test_id.startswith("diagnostic_") or test_id not in self.current_diagnostics:
            return
        
        # prevent duplicate processing of the same test completion event
        if test_id in self.local_diagnostic_results and self.local_diagnostic_results[test_id]["status"] != "PENDING":
            logger.warning(f"Received duplicate completion for test {test_id}, ignoring.")
            return
        
        # check if the message is a cancellation message
        if not success and "cancelled" in message.lower():
            # if the message is a cancellation message, but we have already received a success message, ignore the cancellation message
            if test_id in self.local_diagnostic_results and self.local_diagnostic_results[test_id]["status"] == "PASS":
                logger.warning(f"Ignoring cancellation message for successful test {test_id}")
                return
        
        # calculate the test duration
        time_str = "--:--:--"
        if test_id in self.local_diagnostic_results and "start_time" in self.local_diagnostic_results[test_id]:
            start_time = self.local_diagnostic_results[test_id]["start_time"]
            end_time = datetime.datetime.now()
            duration = end_time - start_time
            time_str = f"{duration.seconds}.{duration.microseconds//1000:02d}s"
        
        # update the diagnostic results
        status = "PASS" if success else "FAIL"
        
        # check if the message is the default success message
        is_default_success_message = (message == "Test completed successfully")
        
        # update the status information in the local cache
        if test_id in self.local_diagnostic_results:
            # update the test result status
            self.local_diagnostic_results[test_id]["status"] = status
            self.local_diagnostic_results[test_id]["time"] = time_str
            self.local_diagnostic_results[test_id]["details"]["message"] = message
            
            # if there are steps data, use the last step message to update the default message
            steps = self.local_diagnostic_results[test_id].get("steps", [])
            if is_default_success_message and steps:
                last_step = steps[-1]
                if "message" in last_step and last_step["message"].startswith("Validation PASSED:"):
                    message = last_step["message"]
                    self.local_diagnostic_results[test_id]["details"]["message"] = message
        else:
            # if there is no previous data, create a basic result
            self.local_diagnostic_results[test_id] = {
                "status": status,
                "time": time_str,
                "details": {"message": message},
                "steps": []
            }
            
            # if there is no step information, create a default step
            default_step = {
                "index": 0,
                "success": success,
                "message": message,
                "description": "Diagnostic Test",
                "time": time_str,
                "command": "",
                "response": ""
            }
            self.local_diagnostic_results[test_id]["steps"].append(default_step)
        
        # record the final result through the callback
        if self.result_recorder:
            self.result_recorder("diagnostic", test_id, self.local_diagnostic_results[test_id])
        
        # update the UI status
        self.diagnostic_container.update_item_status(test_id, status, time_str)
        
        # scroll to the completed test item to show its final status
        self.diagnostic_container.scroll_to_item(test_id)
        
        # record the test completion
        if success:
            logger.info(f"Diagnostic test {test_id} completed: PASS ({time_str})")
        else:
            logger.error(f"Diagnostic test {test_id} failed: {message} ({time_str})")
        
        # after the test is completed, start the next test or complete all the tests
        if hasattr(self, 'pending_tests') and self.pending_tests:
            # start the next test (with a short delay to ensure the system state is stable)
            next_test = self.pending_tests.pop(0)
            
            # scroll to the next test with a slight delay to let the user see the current result first
            QTimer.singleShot(300, lambda: self.diagnostic_container.scroll_to_item(next_test))
            
            # start the next test with a short delay
            QTimer.singleShot(500, lambda: self._start_test(next_test))
        else:
            # check if all the tests are completed
            all_completed = True
            for tid in self.current_diagnostics:
                if tid not in self.local_diagnostic_results or self.local_diagnostic_results[tid]["status"] == "PENDING":
                    all_completed = False
                    break
                
            if all_completed:
                # add a short delay to avoid UI update conflicts
                QTimer.singleShot(100, self._complete_all_diagnostics)
    
    @Slot(str, int, int)
    def _on_test_progress(self, test_id: str, current_step: int, total_steps: int):
        """
        handle the test progress event
        
        Args:
            test_id: the test id
            current_step: the current step index (starting from 1)
            total_steps: the total number of steps
        """
        # only handle the diagnostic tests
        if not test_id.startswith("diagnostic_") or test_id not in self.current_diagnostics:
            return
            
        # record the step start time
        if current_step > 0:
            now = datetime.datetime.now()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            
            # create the progress record
            progress_record = {
                "timestamp": timestamp,
                "start_time": now,  # record the step start time
                "current_step": current_step,
                "total_steps": total_steps
            }
            
            # ensure the local result exists
            if test_id not in self.local_diagnostic_results:
                self.local_diagnostic_results[test_id] = {
                    "status": "PENDING",
                    "time": "--:--:--",
                    "details": {"message": ""},
                    "start_time": now,
                    "steps": []
                }
            
            # if the steps list is not long enough, expand it
            steps = self.local_diagnostic_results[test_id].get("steps", [])
            step_index = current_step - 1  # convert to 0-based index
            
            while len(steps) <= step_index:
                steps.append({})
            
            # update the step start time
            if "start_time" not in steps[step_index]:
                steps[step_index]["start_time"] = now
            
            # save the steps list
            self.local_diagnostic_results[test_id]["steps"] = steps
            
            # record the progress through the callback
            if self.progress_recorder:
                self.progress_recorder("diagnostic", test_id, progress_record)
            
            logger.debug(f"Diagnostic test progress recorded: {test_id}, step {current_step}/{total_steps}")
        
        # do not update the UI progress, because the diagnostic items have no progress bar
    
    @Slot(str, int, bool, str)
    def _on_test_step_completed(self, test_id: str, step_index: int, success: bool, message: str):
        """
        handle the test step completed event
        
        Args:
            test_id: the test id
            step_index: the step index
            success: whether the step is successful
            message: the step result message
        """
        # only handle the diagnostic tests
        if not test_id.startswith("diagnostic_") or test_id not in self.current_diagnostics:
            return
        
        logger.debug(f"Diagnostic step completed: {test_id}, step {step_index+1}, success: {success}, message: {message}")
        
        # get the step execution time
        step_time = "--:--:--"
        step_end_time = datetime.datetime.now()
        
        # try to get the step start time from the test progress record
        step_start_time = None
        
        # get the step start time from the test worker
        if test_id == self.hw_test_manager.active_test_id and self.hw_test_manager.active_test_worker:
            worker = self.hw_test_manager.active_test_worker
            if hasattr(worker, 'steps') and len(worker.steps) > step_index:
                step = worker.steps[step_index]
                # try to get the step start time
                if hasattr(step, 'start_time'):
                    step_start_time = step.start_time
        
        # if the start time is not found in the worker, use the test start time
        if step_start_time is None and test_id in self.local_diagnostic_results:
            if "start_time" in self.local_diagnostic_results[test_id]:
                # for the first step, use the test start time
                if step_index == 0:
                    step_start_time = self.local_diagnostic_results[test_id]["start_time"]
                # for other steps, if there is a previous step, use the previous step's end time
                elif step_index > 0 and "steps" in self.local_diagnostic_results[test_id]:
                    steps = self.local_diagnostic_results[test_id]["steps"]
                    if len(steps) > step_index - 1 and "end_time" in steps[step_index - 1]:
                        step_start_time = steps[step_index - 1]["end_time"]
                    else:
                        # if there is no previous step's end time, use the test start time plus an offset
                        step_start_time = self.local_diagnostic_results[test_id]["start_time"] + datetime.timedelta(seconds=step_index * 1.5)  # assume each step takes about 1.5 seconds
        
        # calculate the step execution time
        if step_start_time:
            duration = step_end_time - step_start_time
            step_time = f"{duration.seconds}.{duration.microseconds//1000:03d}s"
            logger.debug(f"Step {step_index+1} time: {step_time}, start: {step_start_time}, end: {step_end_time}")
        
        # try to get the step detailed information from the test worker
        step_desc = f"Step {step_index+1}"
        step_command = ""
        step_response = ""
        step_specification = ""
        step_criteria = ""
        
        # get the step detailed information from the active test worker
        if test_id == self.hw_test_manager.active_test_id and self.hw_test_manager.active_test_worker:
            worker = self.hw_test_manager.active_test_worker
            if hasattr(worker, 'steps') and len(worker.steps) > step_index:
                step = worker.steps[step_index]
                if hasattr(step, 'description') and step.description:
                    step_desc = step.description
                if hasattr(step, 'command') and step.command:
                    step_command = step.command
                if hasattr(step, 'response') and step.response:
                    step_response = step.response
                elif hasattr(step, 'result') and step.result:
                    step_response = step.result
                # 获取specification和criteria
                if hasattr(step, 'specification') and step.specification:
                    step_specification = step.specification
                if hasattr(step, 'criteria') and step.criteria:
                    step_criteria = step.criteria
        
        # if there is no step detailed information from the active worker, try to get it from the registered workers
        if step_desc == f"Step {step_index+1}" and test_id in self.hw_test_manager.test_workers:
            worker = self.hw_test_manager.test_workers[test_id]
            if hasattr(worker, 'steps') and len(worker.steps) > step_index:
                step = worker.steps[step_index]
                if hasattr(step, 'description') and step.description:
                    step_desc = step.description
                if hasattr(step, 'command') and step.command:
                    step_command = step.command
                if hasattr(step, 'response') and step.response:
                    step_response = step.response
                elif hasattr(step, 'result') and step.result:
                    step_response = step.result
                # 获取specification和criteria
                if hasattr(step, 'specification') and step.specification:
                    step_specification = step.specification
                if hasattr(step, 'criteria') and step.criteria:
                    step_criteria = step.criteria
        
        # create the step result data
        step_data = {
            "index": step_index,
            "success": success,
            "message": message,
            "description": step_desc,
            "time": step_time,
            "start_time": step_start_time,
            "end_time": step_end_time,
            "command": step_command,
            "response": step_response,
            "specification": step_specification,
            "criteria": step_criteria
        }
        
        # update the local cache
        if test_id not in self.local_diagnostic_results:
            self.local_diagnostic_results[test_id] = {
                "status": "PENDING",
                "time": "--:--:--",
                "details": {"message": ""},
                "steps": []
            }
        
        # if the step index is out of the current step list, expand the list
        steps_list = self.local_diagnostic_results[test_id].get("steps", [])
        while len(steps_list) <= step_index:
            steps_list.append({})
        
        # add or update the step data
        steps_list[step_index] = step_data
        self.local_diagnostic_results[test_id]["steps"] = steps_list
        
        # record the result through the callback
        if self.result_recorder:
            self.result_recorder("diagnostic", test_id, self.local_diagnostic_results[test_id])
    
    def _complete_all_diagnostics(self):
        """complete all the diagnostic tests"""
        self.is_running = False
        
        # restore the button status
        self.run_all_button.setText("Run All Tests")
        self.run_all_button.setEnabled(True)
        
        # emit the all diagnostics completed signal
        self.all_diagnostics_completed.emit()
        
        logger.info("All diagnostic tests completed")
    
    def get_diagnostic_results(self) -> Dict[str, Dict[str, Any]]:
        """
        get the diagnostic results
        
        Returns:
            a dictionary, the key is the test id, the value is the test result
        """
        return self.local_diagnostic_results
    
    def clear_diagnostic_results(self):
        """
        Clear all diagnostic results
        Used after exporting results to avoid accumulating old data
        """
        # Reset all diagnostic results
        self.local_diagnostic_results.clear()
        
        for test_id in self.current_diagnostics:
            # Reset UI status to pending
            if self.diagnostic_container:
                self.diagnostic_container.reset_item_status(test_id)
        
        logger.info("Diagnostic results cleared")
    
    def reset_ui(self):
        """reset the UI status - called by MainWindowController"""
        # clear the local cache
        self.local_diagnostic_results.clear()
        
        # reset the UI status of all the diagnostic items
        if self.diagnostic_container:
            for test_id in self.current_diagnostics:
                self.diagnostic_container.reset_item_status(test_id)
    
    def cleanup(self):
        """clean up the resources"""
        try:
            logger.debug("Cleaning up AutoDiagnosticView resources")
            
            # disconnect all the signals
            try:
                self.hw_test_manager.test_started.disconnect(self._on_test_started)
                self.hw_test_manager.test_completed.disconnect(self._on_test_completed)
                self.hw_test_manager.test_progress.disconnect(self._on_test_progress)
                self.hw_test_manager.test_step_completed.disconnect(self._on_test_step_completed)
                
                if self.run_all_button:
                    self.run_all_button.clicked.disconnect(self._on_run_all_tests)
                
                if self.export_button:
                    self.export_button.clicked.disconnect(self._on_export_report)
            except Exception:
                # the signals may already be disconnected, ignore the error
                pass
            
            # clear the references
            self.diagnostic_container = None
            self.run_all_button = None
            self.export_button = None
            self.title_label = None
            self.main_widget = None
            
        except Exception as e:
            logger.error(f"Error during AutoDiagnosticView cleanup: {e}")
    
    def set_buttons_enabled(self, enabled=True):
        """
        enable or disable all the buttons
        
        Args:
            enabled: whether to enable the buttons
        """
        if self.run_all_button:
            self.run_all_button.setEnabled(enabled)
        
        if self.export_button:
            self.export_button.setEnabled(enabled) 