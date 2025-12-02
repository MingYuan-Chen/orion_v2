import json
import os
import sys
import time
import datetime
import re
from typing import Dict, List, Any, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger
from util.command_loader import CommandLoader

class BatteryMonitorService(QObject):
    """
    Service to monitor battery status using commands defined in JSON.
    """

    mapper_folder_name = {
                "Athena": "athena",
                "Odin": "odin",
                "Gemini FHD": "gemini_fhd",
                "Gemini": "gemini",
                "Hydra FHD": "hydra_fhd",
                "Hydra": "hydra",
                "Argo": "argo"
            }

    LED_STATUS_MAP = {
        "athena": {
            1: "Blue", 33: "Blue",
            2: "Green", 34: "Green",
            4: "Red", 36: "Red",
            8: "Amber", 40: "Amber",
            17: "Blink Blue", 49: "Blink Blue",
            18: "Blink Green", 50: "Blink Green",
            20: "Blink Red", 52: "Blink Red",
            24: "Blink Amber", 56: "Blink Amber",
            0: "Off", 32: "Off"
        },
        "odin": {
            1: "Blue", 17: "Blue",
            2: "Green", 18: "Green",
            6: "Yellow", 22: "Yellow",
            9: "Blink Blue", 25: "Blink Blue",
            10: "Blink Green", 26: "Blink Green",
            14: "Blink Yellow", 30: "Blink Yellow",
            0: "Off", 16: "Off"
        },
        "argo": {
            1: "Blue", 17: "Blue",
            2: "Green", 18: "Green",
            4: "Amber", 20: "Amber",
            9: "Blink Blue", 25: "Blink Blue",
            10: "Blink Green", 26: "Blink Green",
            12: "Blink Amber", 28: "Blink Amber",
            0: "Off", 16: "Off"
        },
        "other": {
            1: "Blue", 17: "Blue",
            2: "Green", 18: "Green",
            4: "Red", 20: "Red",
            9: "Blink Blue", 25: "Blink Blue",
            10: "Blink Green", 26: "Blink Green",
            12: "Blink Red", 28: "Blink Red",
            0: "Off", 16: "Off"
        }
    }

    INTERRUPT_STATUS_MAP = {
        0: "Normal",
        1: "No Battery",
        2: "Timeout",
        8: "Over Temperature - Charge",
        16: "Over Current - Charge",
        24: "Over Current & Temperature - Charge",
        32: "Over Temperature - Discharge",
        64: "Over Current - Discharge",
        96: "Over Current & Temperature - Discharge",
    }

    # [16 bit definitions]
    # 15: Overcharged, 14: Terminate Charge, 13: Undifined, 12: Overtemperature, 11: Terminate Discharge,
    # 10: Undifined, 9: Remaining Capacity, 8: Remaining Time, 7: Initialization, 6: Discharging,
    # 5: Full Charged, 4: Full Discharged, 0-3: Error Code
    BATTERY_STATUS_MAP = {
        128: "Charging",
        192: "Discharging",
        160: "Full Charged",
        224: "Full Charged",
        144: "Full Discharged",
        32770: "Initializing",
        32896: "Over Charged",
        16512: "Terminate Charge",
        16544: "Full Charged, Terminate Charge",
        20608: "Over Temperature, Terminate Charge",
        20672: "Over Temperature, Terminate Charge",
        4224: "Over Temperature - Charge",
        4288: "Over Temperature - Discharge",
        3024: "Terminate Discharge, Fully Discharged",
        3008: "Terminate Discharge, Remaining Capacity and Time Alarm",
        2688: "Terminate Discharge, Remaining Capacity Alarm",
        2432: "Terminate Discharge, Remaining Time Alarm",
        2176: "Terminate Discharge",
        960: "Remaining Capacity and Time Alarm",
        704: "Remaining Capacity Alarm",
        448: "Remaining Time Alarm",
    }
    # Signal to emit updated battery data
    battery_data_updated = Signal(dict)

    def __init__(self, device_model: SerialDeviceModel, platform_name: str = None):
        super().__init__()
        self._model = device_model
        self._platform_name = platform_name
        self._commands = {}
        self._load_commands()
        self._running = False
        
        # Timer for polling
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.get_all_battery_info)
        self._interval_ms = 3000

    def start_monitoring(self, interval_ms: int = 3000):
        """Start periodic battery monitoring."""
        if not self._running:
            self._running = True
            self._interval_ms = interval_ms
            # Trigger immediately
            self.get_all_battery_info()

    def stop_monitoring(self):
        """Stop battery monitoring."""
        if self._running:
            self._running = False
            self._timer.stop()

    def _load_commands(self):
        """
        Load battery monitor commands from JSON configuration.
        """
        try:
            # Load commands dynamically
            _mapped_folder_name = self.mapper_folder_name.get(self._platform_name, "Unknown")
            self._commands = CommandLoader.load_commands(_mapped_folder_name, "battery_monitor")
            if not self._commands:
                logger.warning(f"No battery monitor commands found for platform: {self.platform_name}")
        except Exception as e:
            self._commands = {}

    def get_all_battery_info(self) -> Dict[str, Any]:
        """
        Executes all configured commands and returns parsed results.
        """
        
        if not self._running:
            return

        start_time = time.time()
        results = {}
        if not self._model.is_connected():
            logger.warning("Device not connected, cannot get battery info")
            # Even if not connected, we might want to retry later? 
            # For now, let's stop if disconnected or keep retrying?
            # Usually better to keep retrying or let the view model handle stop.
            # But to be safe, we schedule next run.
            if self._running:
                 self._timer.start(self._interval_ms)
            return results

        for key, cmd in self._commands.items():
            if not self._running: break # Check running status during loop
            try:
                response = self._model.send_command_sync(cmd[0])
                
                # Parse the value
                parsed_value = self._parse_value(key, response)
                results[key] = parsed_value
                
            except Exception as e:
                logger.error(f"Error getting info for {key}: {e}")
                results[key] = "Error"
            
        if self._running:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            results["timestamp"] = timestamp
            self.battery_data_updated.emit(results)
            
            # Calculate elapsed time and adjust next interval
            end_time = time.time()
            elapsed_ms = int((end_time - start_time) * 1000)
            next_interval = max(0, self._interval_ms - elapsed_ms)
            
            # Schedule next run
            self._timer.start(next_interval)
            
        return results

    def _parse_value(self, key: str, response) -> Any:
        """
        Parses the raw output based on the key.
        TODO: Modify this method to implement specific parsing logic for your I2C values.
        """
        
        try:
            cpu_usage = None
            memory_usage = None
            for line in response:
                if len(line) > 4 and line.startswith('0x'):
                    line_hex = [x.replace('0x', '') for x in line.split() if x.startswith('0x')]
                    combined_hex = "0x" + line_hex[0] + line_hex[1]
                    hex_value = int(combined_hex, 16)

                    # Dispatch to specific parsers based on key
                    if key == "voltage":
                        voltage = round(hex_value / 1000, 1)
                        if 0 <= voltage <= 15:
                            return f"{voltage}V ({combined_hex})"
                        else:
                            return f"N/A ({combined_hex})"
                    elif key == "current":
                        if hex_value > 32767:
                            signed_value = hex_value - 65536  # Convert to signed
                        else:
                            signed_value = hex_value
                        current = round(float(signed_value/1000), 1)
                        if -5 < current < 5:
                            return f"{current}A ({combined_hex})"
                        else:
                            return f"N/A ({combined_hex})"
                    elif key == "relative_state":
                        if 0 <= hex_value <= 100:
                            return f"{hex_value}% ({combined_hex})" # Battery percentage (0-100)
                        else:
                            return f"N/A ({combined_hex})"
                    elif key == "temperature":
                        temperature = round(float(hex_value/10)-273.2, 1)
                        if 0 < temperature < 120:
                            return f"{temperature}°C ({combined_hex})"  # Convert to Celsius
                        else:
                            return f"N/A ({combined_hex})"
                    elif key == "battery_status":
                        status = self.BATTERY_STATUS_MAP.get(hex_value, "Unknown")
                        return f"{status} ({combined_hex})"
                    elif key == "led_status":
                        mapped_name = self.mapper_folder_name.get(self._platform_name, "Unknown")
                        status = self.LED_STATUS_MAP.get(mapped_name, self.LED_STATUS_MAP.get("other")).get(hex_value, "Unknown")
                        return f"{status} ({combined_hex})"
                    elif key == "interrupt_status":
                        status = self.INTERRUPT_STATUS_MAP.get(hex_value, "Unknown")
                        return f"{status} ({combined_hex})"
                    elif key == "remaining_capacity":
                        return f"{hex_value}mAh ({combined_hex})"
                
                if key == "top_info":
                    # Parse CPU usage from lines like: "CPU:  12.5% usr   2.1% sys   0.0% nic  84.4% idle"
                    # Or: "%Cpu(s):  5.2 us,  1.3 sy,  0.0 ni, 93.5 id"
                    if line.startswith('CPU:') or line.startswith('%Cpu'):
                        # Look for patterns like "12.5% usr" or "5.2 us"
                        # Pattern to match percentage values before "usr", "us", "sys", "sy"
                        cpu_pattern = r'(\d+\.?\d*)%?\s*(?:usr|us|sys|sy)'
                        matches = re.findall(cpu_pattern, line)
                        if matches:
                            # Sum up user and system CPU usage (first two matches typically)
                            usr_cpu = float(matches[0]) if len(matches) > 0 else 0.0
                            sys_cpu = float(matches[1]) if len(matches) > 1 else 0.0
                            cpu_usage = round(usr_cpu + sys_cpu, 1)
                            
                            # Alternative: calculate from idle percentage
                            # Look for idle percentage
                            idle_pattern = r'(\d+\.?\d*)%?\s*(?:idle|id)'
                            idle_matches = re.findall(idle_pattern, line)
                            if idle_matches:
                                idle_cpu = float(idle_matches[0])
                                cpu_usage = round(100.0 - idle_cpu, 1)
                            
                    # Parse memory usage from lines like: "Mem:   1024000k total,   512000k used,   512000k free"
                    # Or: "KiB Mem :  2048000 total,  1024000 used,   1024000 free"
                    # Or: "MiB Mem :   3851.2 total,   3529.4 free,    193.9 used,    128.0 buff/cache"
                    elif 'Mem:' in line or 'KiB Mem' in line or 'MiB Mem' in line:
                        # Use flexible regex to find total and used memory regardless of order
                        # Pattern for total memory
                        total_match = re.search(r'(\d+\.?\d*)\s*(?:k|KiB|MiB)?\s*total', line)
                        # Pattern for used memory
                        used_match = re.search(r'(\d+\.?\d*)\s*(?:k|KiB|MiB)?\s*used', line)
                        
                        if total_match and used_match:
                            total_memory = float(total_match.group(1))
                            used_memory = float(used_match.group(1))
                            
                            if total_memory > 0:
                                # Calculate memory usage percentage
                                memory_usage = round((used_memory / total_memory) * 100, 1)
                    
                    # Return result if both values were parsed successfully
                    if cpu_usage is not None and memory_usage is not None:
                        return {
                            "cpu_usage": f"{cpu_usage}%",
                            "memory_usage": f"{memory_usage}%"
                        }
                            
            
            # Default: return raw string stripped of whitespace
            return "Unknown"
            
        except Exception as e:
            logger.error(f"Error parsing {key}: {e}")
            return f"Parse Error: {response}"
