import json
import os
import re
import time
from typing import Dict, List, Tuple, Any, Optional
from PySide6.QtCore import QObject, Signal, QTimer, Slot
import sys
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
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
                return True, f"System time is auto synced from network"
            else:
                return False, f"System time is not auto synced from network"

        return False, "No matched time string found"
    
    @staticmethod
    def validate_read_write(output: str) -> Tuple[bool, str]:
        """Validator for USB/EMMC read write."""
        pattern = r'(\d+\.?\d*)\s+(MB/s|MiB/s|M/s|GB/s|GiB/s|G/s)'
        matches = re.findall(pattern, output)
        while len(matches) > 2: matches.pop(0)
        if matches and len(matches) == 2:
            write_speed_unit = matches[0][1]
            read_speed_unit = matches[1][1]

            if write_speed_unit in ['GB/s', 'GiB/s', 'G/s']:
                write_speed = float(matches[0][0]) * 1024
            else:
                write_speed = float(matches[0][0])

            if read_speed_unit in ['GB/s', 'GiB/s', 'G/s']:
                read_speed = float(matches[1][0]) * 1024
            else:
                read_speed = float(matches[1][0])

            if read_speed > 100 and write_speed > 50:
                return True, f"Read speed: {matches[1][0]} {matches[1][1]}, Write speed: {matches[0][0]} {matches[0][1]}"
            else:
                return False, f"Read speed: {matches[1][0]} {matches[1][1]}, Write speed: {matches[0][0]} {matches[0][1]}"
        return False, "No matched speed string found"
    
    @staticmethod
    def validate_eeprom_for_athena(output: str) -> Tuple[bool, str]:
        """Validator for EEPROM."""
        eeprom_1_byte = False
        eeprom_1_byte_dump = False
        eeprom_19_bytes = False
        eeprom_19_bytes_dump_1 = False
        eeprom_19_bytes_dump_2 = False
        responses = output.split("\n")
        for line in responses:
            line = line.strip()
            if line == "0xaa":
                eeprom_1_byte = True
            elif line == "0x32 0x30 0x32 0x35 0x2f 0x30 0x33 0x2f 0x32 0x38 0x20 0x32 0x30 0x3a 0x32 0x38 0x3a 0x33 0x36":
                eeprom_19_bytes = True
            elif line.startswith("10:") and "aa" in line:
                eeprom_1_byte_dump_1 = True
            elif line.startswith("00000080") and "2025/03/28 20" in line:
                eeprom_19_bytes_dump_1 = True
            elif line.startswith("00000090") and ":28:36" in line:
                eeprom_19_bytes_dump_2 = True
        if eeprom_1_byte and eeprom_19_bytes and eeprom_1_byte_dump_1 and eeprom_19_bytes_dump_1 and eeprom_19_bytes_dump_2:
            return True, "EEPROM values match"
        return False, "EEPROM values do not match"
    
    @staticmethod
    def validate_charge_for_athena(output: str) -> Tuple[bool, str]:
        """Validator for charge."""
        results = []
        responses = output.split("\n")
        for line in responses:
            result = DiagnosticValidator._parse_battery_value(line)
            if result:
                results.append(result)
        if len(results) == 3:
            if results[0] == "MD-BAT03":
                if results[1] == 768 and results[2] == 12592:
                    return True, f"Get available model name: {results[0]}, with correct current setting: {results[1]}mA, with correct voltage setting: {results[2]}mV"
                else:
                    return False, f"Incorrect current setting: {results[1]}mA or incorrect voltage setting: {results[2]}mV"
            elif results[0] is None:
                if results[1] == 192 and results[2] == 8992:
                    return True, f"Detected low battery mode, with correct current setting: {results[1]}mA, with correct voltage setting: {results[2]}mV"
                else:
                    return False, f"Incorrect current setting: {results[1]}mA or incorrect voltage setting: {results[2]}mV"
        return False, "No matched charge values found"
    
    @staticmethod
    def _parse_battery_value(line) -> Any:
        """
        Parses the raw output based on the key.
        TODO: Modify this method to implement specific parsing logic for your I2C values.
        """
        
        try:
            if len(line) > 4 and line.startswith('0x'):
                line_hex = [x.replace('0x', '') for x in line.split() if x.startswith('0x')]
                if len(line_hex) >= 4:
                    model = ""
                    for idx in range(1, len(line_hex)):
                        char_code = int(f"0x{line_hex[idx]}", 16)
                        if 32 <= char_code <= 126:
                            model += chr(char_code)
                    return model
                else:
                    combined_hex = "0x" + line_hex[0] + line_hex[1]
                    hex_value = int(combined_hex, 16)

                    return hex_value
            return None

        except Exception as e:
            logger.error(f"Error parsing {line}: {e}")
            return f"Parse Error: {line}"


class DiagnosticService(QObject):
    """
    Service to manage diagnostic execution and validation.
    """
    diagnostic_finished = Signal(str, bool, str) # key, success, message
    diagnostic_start = Signal(str) # key
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
        self._results_history = []

        # variables for Precondition setup
        self.usb1_path = None
        self.usb2_path = None
        self.usb3_path = None
        self.eeprom_1_byte = None
        self.eeprom_19_bytes = None
        self.touch_qt_path = None
        
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
        self._precondition_setup()
        self._running = True
        self._queue = list(self._diagnostics.items())
        self._results_history = []
        self._run_next()

    def _run_next(self):
        if not self._running:
            return

        if not self._queue:
            self._save_to_excel()
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
                # Get the message from the command
                message = cmd.replace("manual_check_required. ", "")
                # Pause execution and request user interaction
                self.manual_check_requested.emit(self._current_key, message)
                return

            # Execute command
            if "U-Boot" in cmd:
                response_lines = self._model.send_command_sync(cmd, timeout=20)
            elif "ts_test_mt -j 2 -v" in cmd:
                self._model.send_command_queued(cmd)
            elif "touch_qt_path" in cmd:
                if self.touch_qt_path:
                    cmd_replace = cmd.replace("touch_qt_path", self.touch_qt_path)
                    self._model.send_command_queued(f"'{cmd_replace}'")
            elif "sleep_required" in cmd:
                time.sleep(float(cmd.split(" ")[1]))  
            elif "usb1_path" in cmd:
                if self.usb1_path:
                    cmd_replace = cmd.replace("usb1_path", self.usb1_path)
                    response_lines = self._model.send_command_sync(cmd_replace)
            elif "usb2_path" in cmd:
                if self.usb2_path:
                    cmd_replace = cmd.replace("usb2_path", self.usb2_path)
                    response_lines = self._model.send_command_sync(cmd_replace)
            elif "usb3_path" in cmd:
                if self.usb3_path:
                    cmd_replace = cmd.replace("usb3_path", self.usb3_path)
                    response_lines = self._model.send_command_sync(cmd_replace)
            elif "eeprom_1_byte" in cmd:
                if self.eeprom_1_byte:
                    cmd_replace = cmd.replace("eeprom_1_byte", self.eeprom_1_byte)
                    response_lines = self._model.send_command_sync(cmd_replace)
            elif "eeprom_19_bytes" in cmd:
                if self.eeprom_19_bytes:
                    cmd_replace = cmd.replace("eeprom_19_bytes", self.eeprom_19_bytes)
                    response_lines = self._model.send_command_sync(cmd_replace)
            else:
                response_lines = self._model.send_command_sync(cmd)
            
            # Get output string
            if "touch_qt_path" in cmd or "ts_test_mt -j 2 -v" in cmd:
                output_str = "Touch Test Tool Launched"
            elif "sleep_required" in cmd:
                output_str = "Sleeping for " + cmd.split(" ")[1] + " second(s)"
            elif "usb1_path" in cmd and not self.usb1_path:
                output_str = "USB1 path not found"
            elif "usb2_path" in cmd and not self.usb2_path:
                output_str = "USB2 path not found"
            elif "usb3_path" in cmd and not self.usb3_path:
                output_str = "USB3 path not found"
            elif "eeprom_1_byte" in cmd and not self.eeprom_1_byte:
                output_str = "EEPROM 1 byte not found"
            elif "eeprom_19_bytes" in cmd and not self.eeprom_19_bytes:
                output_str = "EEPROM 19 bytes not found"
            else:
                output_str = "\n".join(response_lines)
            self._current_output.append(output_str)

        if not self._running:
            return

        # If we are here, either all commands are done or we stopped running
        if not self._current_commands:
            self._finish_current_diagnostic()

    @Slot(str)
    def resume_diagnostic(self, result: str):
        """
        Resumes the diagnostic process after a manual check.
        """
        if not self._running:
            return

        if result != "SKIP":
            self._current_output.append(f"manual_check_result_{result}")

        # Continue processing remaining commands
        self._process_commands()

    def _finish_current_diagnostic(self):
        combined_output = "\n".join(self._current_output)

        # Validate
        if "manual_check_result_PASS" in combined_output:
            is_valid, msg = True, "Manual check result: Pass"
        elif "manual_check_result_FAIL" in combined_output:
            is_valid, msg = False, "Manual check result: Fail"
        else:
            is_valid, msg = self.validate_result(self._current_key, combined_output)
        
        self.diagnostic_finished.emit(self._current_key, is_valid, msg)
        
        # Store result
        self._results_history.append({
            "key": self._current_key,
            "success": is_valid,
            "message": msg,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
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
    
    def _precondition_setup(self):
        """
        Setup precondition for diagnostics.
        """
        self._find_original_eeprom_data()
        self._find_valid_usb_path()

    def _find_valid_usb_path(self):
        """
        Find valid usb path from 'ls -l /run/media'.
        e.g., 
        total 12
        drwxrwx---  3 root disk 4096 Jan  1  1970 'Main Data Partition-sdb1'
        drwxrwx--- 13 root disk 8192 Jan  1  1970  sda1
        """
        try:
            response = self._model.send_command_sync("ls -l /run/media")
            device_names = []
            for line in response:
                line = line.strip()
                if not line or line.startswith('total'):
                    continue
                parts = line.split(None, 8)
                if len(parts) == 9:
                    device_name = parts[8].strip("'")
                    device_names.append(device_name)

            # Prioritize assignment based on 'sda1' and 'sdb1'
            unassigned_names = []
            for name in device_names:
                if 'sda1' in name and self.usb1_path is None:
                    self.usb1_path = f"/run/media/{name}"
                    file_path = f"{self.usb1_path}/dqa_package"
                    response = self._model.send_command_sync(f"ls {file_path}")
                    for line in response:
                        if "TouchTestQt64" in line and self.touch_qt_path is None:
                            self.touch_qt_path = f"{file_path}/TouchTestQt64"
                            logger.debug(f"Found TouchTestQt64 at {self.touch_qt_path}")
                elif 'sdb1' in name and self.usb2_path is None:
                    self.usb2_path = f"/run/media/{name}"
                    file_path = f"{self.usb2_path}/dqa_package"
                    response = self._model.send_command_sync(f"ls {file_path}")
                    for line in response:
                        if "TouchTestQt64" in line and self.touch_qt_path is None:
                            self.touch_qt_path = f"{file_path}/TouchTestQt64"
                            logger.debug(f"Found TouchTestQt64 at {self.touch_qt_path}")
                elif 'sdb2' in name and self.usb3_path is None:
                    self.usb3_path = f"/run/media/{name}"
                    file_path = f"{self.usb3_path}/dqa_package"
                    response = self._model.send_command_sync(f"ls {file_path}")
                    for line in response:
                        if "TouchTestQt64" in line and self.touch_qt_path is None:
                            self.touch_qt_path = f"{file_path}/TouchTestQt64"
                            logger.debug(f"Found TouchTestQt64 at {self.touch_qt_path}")
                else:
                    logger.debug(f"Ignored device: {name}")
            
        except Exception as e:
            logger.error(f"Find valid usb path error: {str(e)}", exc_info=True)
            return False, f"Find valid usb path error: {str(e)}"

    def _find_original_eeprom_data(self):
        """
        Find original eeprom data from usb1, usb2, usb3.
        """
        try:
           response = self._model.send_command_sync("i2cget -f -y 1 0x57 0x1f")
           for line in response:
               if line.startswith("0x"):
                   self.eeprom_1_byte = line
           time.sleep(0.2)
           response = self._model.send_command_sync("i2ctransfer -f -y 1 w2@0x54 0x00 0x83 r19")
           for line in response:
               if line.startswith("0x"):
                   self.eeprom_19_bytes = line
           time.sleep(0.2)
        except Exception as e:
            logger.error(f"Find original eeprom data error: {str(e)}", exc_info=True)
            return False, f"Find original eeprom data error: {str(e)}"
    
    def _save_to_excel(self):
        """Saves the diagnostic results to an Excel file."""
        try:
            log_dir = os.path.join(os.getcwd(), "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"diagnostic_report_{timestamp}.xlsx"
            filepath = os.path.join(log_dir, filename)
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Diagnostic Report"
            
            # Headers
            headers = ["Timestamp", "Test Name", "Result", "Message"]
            ws.append(headers)
            
            # Style Headers
            for cell in ws[1]:
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")
            
            # Data
            for result in self._results_history:
                row = [
                    result["timestamp"],
                    result["key"].replace("diagnostic_", "").replace("_", " ").title(),
                    "PASS" if result["success"] else "FAIL",
                    result["message"]
                ]
                ws.append(row)
                
                # Style Result Column
                result_cell = ws.cell(row=ws.max_row, column=3)
                if result["success"]:
                    result_cell.font = Font(color="008000", bold=True) # Green
                else:
                    result_cell.font = Font(color="FF0000", bold=True) # Red
            
            # Auto-adjust column widths
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter # Get the column name
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column].width = adjusted_width
                
            wb.save(filepath)
            logger.info(f"Diagnostic report saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save diagnostic report: {e}")

    def disconnect(self):
        self._running = False
        if hasattr(self, '_queue'):
            self._queue.clear()
        if hasattr(self, '_model'):
            self._model.command_queue.clear()
