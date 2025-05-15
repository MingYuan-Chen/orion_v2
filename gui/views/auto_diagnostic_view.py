"""
Auto diagnostic view module
Responsible for managing diagnostic test execution and UI updates
"""

from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
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
        
        # UI components references
        self.main_widget = None
        self.diagnostic_container = None
        self.run_all_button = None
        self.export_button = None
        self.title_label = None
        
        # test status tracking
        self.diagnostic_results = {}
        self.current_diagnostics = []
        self.is_running = False
        
        # connect signals
        self._connect_signals()
        
        logger.info("Auto diagnostic view initialized")
    
    def _connect_signals(self):
        """connect the hardware test manager signals"""
        # connect the hardware test manager signals
        self.hw_test_manager.test_started.connect(self._on_test_started)
        self.hw_test_manager.test_completed.connect(self._on_test_completed)
        self.hw_test_manager.test_progress.connect(self._on_test_progress)
    
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
        
        # set the diagnostic container height
        scroll_height = item_height * visible_items + 15
        self.diagnostic_container.set_fixed_height(scroll_height)
        
        # add the diagnostic container to the main layout
        main_layout.addWidget(self.diagnostic_container)
        
        # set the main widget fixed height
        total_height = scroll_height + 60  # the title area is about 60 pixels
        self.main_widget.setFixedHeight(total_height)
        
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
            self.diagnostic_results[test_id] = {
                "status": "PENDING",
                "time": "--:--:--",
                "details": {
                    "message": ""
                }
            }
            
        # record all the diagnostic items
        self.current_diagnostics = list(diagnostic_tests.keys())
    
    def _on_run_all_tests(self):
        """handle the run all tests button click"""
        if self.is_running:
            return
            
        self.is_running = True
        self.run_all_button.setText("Running...")
        self.run_all_button.setEnabled(False)
        
        # reset all the diagnostic items status
        self.diagnostic_container.reset_all_items()
        
        # start running the test sequence
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
                            if step.command:
                                self.add_system_log("INFO", f"[Command][{test_id}] {step.command}")
                    
                    # Set response collector function
                    if hasattr(worker, 'set_response_collector'):
                        # 创建一个响应收集器函数
                        def response_collector(test_id, step_index, command, response):
                            self.add_system_log("INFO", f"[Response][{test_id}] {response}")
                        
                        # 设置响应收集器
                        worker.set_response_collector(response_collector)
            
            # start the test
            self.hw_test_manager.start_test(self.device_id, test_id)
            
            # record the start time
            start_time = datetime.datetime.now()
            self.diagnostic_results[test_id]["start_time"] = start_time
            
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
        # update the UI status
        self.diagnostic_container.update_item_status(test_id, "PENDING")
        
        # scroll to the test item being executed
        self.diagnostic_container.scroll_to_item(test_id)
        
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
        # check if the test id is the one we are tracking
        if test_id not in self.current_diagnostics:
            return
        
        # prevent duplicate processing of the same test completion event
        if test_id in self.diagnostic_results and self.diagnostic_results[test_id]["status"] != "PENDING":
            logger.warning(f"Received duplicate completion for test {test_id}, ignoring.")
            return
        
        # check if the message is a cancellation message
        if not success and "cancelled" in message.lower():
            # if the message is a cancellation message, but we have already received a success message, ignore the cancellation message
            if test_id in self.diagnostic_results and self.diagnostic_results[test_id]["status"] == "PASS":
                logger.warning(f"Ignoring cancellation message for successful test {test_id}")
                return
        
        # calculate the test duration
        if test_id in self.diagnostic_results and "start_time" in self.diagnostic_results[test_id]:
            start_time = self.diagnostic_results[test_id]["start_time"]
            end_time = datetime.datetime.now()
            duration = end_time - start_time
            time_str = f"{duration.seconds}.{duration.microseconds//1000:02d}s"
        else:
            time_str = "--:--:--"
        
        # update the diagnostic results
        status = "PASS" if success else "FAIL"
        self.diagnostic_results[test_id]["status"] = status
        self.diagnostic_results[test_id]["time"] = time_str
        self.diagnostic_results[test_id]["details"]["message"] = message
        
        # try to collect the detailed test results
        try:
            # 首先尝试从活动的测试工作器获取步骤信息
            if test_id == self.hw_test_manager.active_test_id and self.hw_test_manager.active_test_worker:
                test_worker = self.hw_test_manager.active_test_worker
                # store the detailed test results
                if hasattr(test_worker, 'steps') and test_worker.steps:
                    steps_results = []
                    for i, step in enumerate(test_worker.steps):
                        step_result = {
                            "description": step.description,
                            "command": step.command,
                            "passed": getattr(step, 'passed', None),
                            "result": getattr(step, 'result', None),
                            "response": getattr(step, 'response', None)
                        }
                        steps_results.append(step_result)
                    self.diagnostic_results[test_id]["details"]["steps"] = steps_results
            # 如果活动工作器没有步骤信息，尝试从注册的工作器获取
            elif test_id in self.hw_test_manager.test_workers:
                test_worker = self.hw_test_manager.test_workers[test_id]
                # store the detailed test results
                if hasattr(test_worker, 'steps') and test_worker.steps:
                    steps_results = []
                    for i, step in enumerate(test_worker.steps):
                        step_result = {
                            "description": step.description,
                            "command": step.command,
                            "passed": getattr(step, 'passed', None),
                            "result": getattr(step, 'result', None),
                            "response": getattr(step, 'response', None)
                        }
                        steps_results.append(step_result)
                    self.diagnostic_results[test_id]["details"]["steps"] = steps_results
        except Exception as e:
            logger.warning(f"Failed to collect detailed test results for {test_id}: {e}")
        
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
                if tid not in self.diagnostic_results or self.diagnostic_results[tid]["status"] == "PENDING":
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
        # do not update the UI progress, because the diagnostic items have no progress bar
        pass
    
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
        return self.diagnostic_results
    
    def cleanup(self):
        """clean up the resources"""
        try:
            logger.debug("Cleaning up AutoDiagnosticView resources")
            
            # disconnect all the signals
            try:
                self.hw_test_manager.test_started.disconnect(self._on_test_started)
                self.hw_test_manager.test_completed.disconnect(self._on_test_completed)
                self.hw_test_manager.test_progress.disconnect(self._on_test_progress)
                
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