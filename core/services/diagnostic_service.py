import json
import os
import re
from typing import Dict, List, Tuple, Any, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger

class DiagnosticValidator:
    """
    Contains static methods for custom validation of diagnostic command outputs.
    """
    
    @staticmethod
    def validate_memory_size(output: str, expected: Any) -> Tuple[bool, str]:
        """
        Example validator: Checks if memory size is within a reasonable range of expected value.
        Expected can be a specific number or a dict with min/max.
        """
        try:
            # Extract number from output (assuming output contains the number in kB)
            # Example output: "MemTotal:        3943740 kB"
            match = re.search(r'(\d+)', output)
            if not match:
                return False, f"Could not parse number from output: {output.strip()}"
            
            actual_value = int(match.group(1))
            
            if isinstance(expected, dict):
                min_val = expected.get('min')
                max_val = expected.get('max')
                if min_val is not None and actual_value < min_val:
                    return False, f"Value {actual_value} < min {min_val}"
                if max_val is not None and actual_value > max_val:
                    return False, f"Value {actual_value} > max {max_val}"
                return True, f"Value {actual_value} within range [{min_val}, {max_val}]"
            else:
                # Simple equality or close enough check? 
                # For now let's assume expected is a string representation of the number
                expected_val = int(expected)
                if actual_value == expected_val:
                    return True, f"Value {actual_value} matches expected {expected_val}"
                else:
                    return False, f"Value {actual_value} does not match expected {expected_val}"
                    
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def validate_contains(output: str, expected: str) -> Tuple[bool, str]:
        """Simple validator to check if output contains expected string."""
        if expected in output:
            return True, f"Found expected output: {expected}"
        return False, f"All expected outputs not found"

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
            base_path = os.getcwd() # Or sys.frozen logic if needed
            filepath = os.path.join(base_path, "resources", "commands", self._platform_name.lower(), "auto_diagnostic.json")
            
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._diagnostics = json.load(f)
            else:
                logger.warning(f"No diagnostic file found for {self._platform_name}")
                self._diagnostics = {}
        except Exception as e:
            logger.error(f"Error loading diagnostics: {e}")
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
                return validator(output, expected_response)
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
    
    def disconnect(self):
        self._running = False
        self._queue.clear()
        self._model.command_queue.clear()
