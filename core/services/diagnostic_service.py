import json
import os
import re
from typing import Dict, List, Tuple, Any, Optional
from PySide6.QtCore import QObject, Signal, QTimer
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
        
        pattern = r"(?:\w{3}\s\w{3}\s\d{1,2}\s\d{2}:\d{2}:\d{2}\sUTC\s\d{4}|\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)"
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
    all_diagnostics_finished = Signal()

    def __init__(self, device_model: SerialDeviceModel, platform_name: str):
        super().__init__()
        self._model = device_model
        self._platform_name = platform_name
        self._diagnostics = {}
        self._running = False
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

        key, config = self._queue.pop(0)
        commands = config.get("commands", [])
        
        if not commands:
            self._run_next()
            return

        # Execute commands
        full_output = []
        success = True
        error_msg = ""

        for cmd in commands:
            if not self._running:
                return

            # Send command synchronously
            # Note: send_command_sync returns a list of lines
            if "U-Boot" in cmd:
                response_lines = self._model.send_command_sync(cmd, timeout=20)
            else:
                response_lines = self._model.send_command_sync(cmd)
            output_str = "\n".join(response_lines)
            full_output.append(output_str)
        if not self._running:
            return

        combined_output = "\n".join(full_output)

        # Validate
        is_valid, msg = self.validate_result(key, combined_output)
        
        self.diagnostic_finished.emit(key, is_valid, msg)
        
        # Schedule next run (using QTimer or just direct call if sync? 
        # Direct call might block UI if too many. Better to use 0-timer or similar if possible, 
        # but here we are in a service. 
        # If send_command_sync processes events, we are fine.
        # Let's just call recursively for now, assuming stack depth isn't an issue for typical diagnostic counts)
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
