import json
import os
import re
from typing import Dict, List, Tuple, Any, Optional
from PySide6.QtCore import QObject, Signal, QTimer, Slot
import sys
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger
from datetime import datetime
from util.command_loader import CommandLoader

class DiagnosticValidator:
    """
    Contains static methods for custom validation of diagnostic command outputs.
    """
    @staticmethod
    def validate_contains(output: str, expected: str) -> Tuple[bool, str]:
        """Simple validator to check if output contains expected string."""
        if expected in output:
            return True, f"Found expected output: {expected}"
        return False, f"All expected outputs not found"
    
    @staticmethod
    def validate_sync_time_for_athena(output: str) -> Tuple[bool, str]:
        """Validator for Athena sync time."""
        pattern = r"(?:\w{3}\s\w{3}\s{1,2}\d{1,2}\s\d{2}:\d{2}:\d{2}\sUTC\s\d{4}|\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)"
        matches = re.findall(pattern, output)
        if matches and len(matches) == 3:
            hw_time = datetime.fromisoformat(matches[1]).replace(tzinfo=None)
            sw_time = datetime.strptime(matches[2], "%a %b %d %H:%M:%S %Z %Y").replace(tzinfo=None)
            time_difference = abs((hw_time - sw_time).total_seconds())
            if time_difference < 5:
                return True, f"HW time and System time is synced"
            else:
                return False, f"HW time and System time difference more then 5 seconds"

        return False, "No matched time string found"

class DiagnosticService(QObject):
    """
    Service to manage diagnostic execution and validation.
    """
    diagnostic_finished = Signal(str, bool, str) # key, success, message
    diagnostic_start = Signal(str) # key
    diagnostic_step = Signal(str, str) # cmd, output
    manual_check_requested = Signal(str, str) # key, message
    all_diagnostics_finished = Signal()

    def __init__(self, device_model: SerialDeviceModel, platform_name: str):
        super().__init__()
        self._model = device_model
        self._platform_name = platform_name
        self._diagnostics = {}
        self._running = False
        self._current_key = None
        self._current_commands = []
        self._current_output = []
        self._load_diagnostics()
        
    def _load_diagnostics(self):
        # Load from resources/commands/{platform}/auto_diagnostic.json
        # Similar path logic as SystemInfoService/HWConfigService
        try:
            # Load commands dynamically
            mapper_folder_name = {
                "Athena": "athena",
                "Odin": "odin",
                "Gemini FHD": "gemini_fhd",
                "Gemini": "gemini",
                "Hydra FHD": "hydra_fhd",
                "Hydra": "hydra",
                "Argo": "argo"
            }
            _mapped_folder_name = mapper_folder_name.get(self._platform_name, "Unknown")
            self._diagnostics = CommandLoader.load_commands(_mapped_folder_name, "auto_diagnostic")
            if not self._diagnostics:
                logger.warning(f"No battery monitor commands found for platform: {self.platform_name}")
        except Exception as e:
            self._diagnostics = {}

    def run_diagnostics(self):
        """
        Runs all diagnostics sequentially.
        """
        self._running = True
        self._queue = list(self._diagnostics.items())
        self._run_next()

    def _run_next(self):
        if not self._running:
            return

        if not self._queue:
            self.all_diagnostics_finished.emit()
            self._running = False
            return

        self._current_key, config = self._queue.pop(0)
        self._current_commands = list(config.get("commands", []))
        self._current_output = []
        
        if not self._current_commands:
            self._run_next()
            return

        # Emit start signal
        self.diagnostic_start.emit(self._current_key)

        # Start processing commands
        self._process_commands()

    def _process_commands(self):
        """
        Processes commands for the current diagnostic step.
        Supports pausing for manual checks.
        """
        while self._current_commands and self._running:
            cmd = self._current_commands.pop(0)

            if "manual_check_required" in cmd:
                # Pause execution and request user interaction
                self.manual_check_requested.emit(self._current_key, "Manual check required. Please confirm to proceed.")
                return

            # Execute command
            if "U-Boot" in cmd:
                response_lines = self._model.send_command_sync(cmd, timeout=20)
            elif "TouchTestQt64" in cmd or "ts_test_mt -j 2 -v" in cmd:
                self._model.send_command_queued(cmd)
            else:
                response_lines = self._model.send_command_sync(cmd)
            
            if "TouchTestQt64" in cmd or "ts_test_mt -j 2 -v" in cmd:
                output_str = "TouchTest"
            else:
                output_str = "\n".join(response_lines)
            self._current_output.append(output_str)
            
            # Emit step signal
            self.diagnostic_step.emit(cmd, output_str)

        if not self._running:
            return

        # If we are here, either all commands are done or we stopped running
        if not self._current_commands:
            self._finish_current_diagnostic()

    @Slot(bool)
    def resume_diagnostic(self, result: bool):
        """
        Resumes the diagnostic process after a manual check.
        """
        if not self._running:
            return

        self._current_output.append(f"manual_check_result_{result}")

        # Continue processing remaining commands
        self._process_commands()

    def _finish_current_diagnostic(self):
        combined_output = "\n".join(self._current_output)

        # Validate
        if "manual_check_result_True" in combined_output:
            is_valid, msg = True, "Manual check result: Pass"
        elif "manual_check_result_False" in combined_output:
            is_valid, msg = False, "Manual check result: Fail"
        else:
            is_valid, msg = self.validate_result(self._current_key, combined_output)
        
        self.diagnostic_finished.emit(self._current_key, is_valid, msg)
        
        # Schedule next run
        self._run_next()

    def validate_result(self, key: str, output: str) -> Tuple[bool, str]:
        """
        Validates the output for a given diagnostic key.
        """
        try:
            config = self._diagnostics.get(key)
            if not config:
                return False, "Unknown diagnostic key"

            validate_func_name = config.get("validate_function")
            expected_response = config.get("expected_response")

            if validate_func_name:
                if hasattr(DiagnosticValidator, validate_func_name):
                    validator = getattr(DiagnosticValidator, validate_func_name)
                    # We might need to pass extra args from config if needed
                    # For now, pass expected_response as the second arg
                    return validator(output)
                else:
                    return False, f"Validator function '{validate_func_name}' not found"
            
            elif expected_response:
                # Default validation: check if output contains expected response(s)
                # expected_response can be a list or string
                if isinstance(expected_response, list):
                    for expected in expected_response:
                        if expected in output:
                            return True, f"Found expected output: {expected}"
                    return False, "All expected outputs not found"
                else:
                    return DiagnosticValidator.validate_contains(output, str(expected_response))
            
            return True, "No validation criteria defined"
        except Exception as e:
            logger.error(f"Error validating diagnostic {key}: {e}")
            return False, str(e)
    
    def disconnect(self):
        self._running = False
        if hasattr(self, '_queue'):
            self._queue.clear()
        if hasattr(self, '_model'):
            self._model.command_queue.clear()
