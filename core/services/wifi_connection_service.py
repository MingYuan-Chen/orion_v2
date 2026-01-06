import re
from PySide6.QtCore import QObject, Signal, Slot
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger
from typing import Optional, List, Dict

class WifiConnectionService(QObject):
    """
    Service for handling WiFi connections using nmcli via SerialDeviceModel.
    """
    scan_finished = Signal(list)  # Emits list of dicts: [{'ssid': '...', 'signal': '...', 'security': '...'}]
    connection_result = Signal(bool, str) # success, message
    status_updated = Signal(dict) # {'connected': bool, 'ssid': str, 'ip': str}

    def __init__(self, device_model: SerialDeviceModel, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._model = device_model
        
        # Connect to model signals if needed, though we primarily use send_command_sync/queued
        # and parse results. For async operations, we might need a worker or just rely on the model's queue.

    @Slot()
    def scan_networks(self):
        """
        Scans for available WiFi networks using nmcli.
        """
        
        # nmcli -t -f SSID,SIGNAL,SECURITY,BARS dev wifi list
        # -t: terse output (colon separated)
        # -f: fields
        cmd = "nmcli -t -f SSID,SIGNAL,SECURITY,BARS dev wifi list --rescan yes"
        
        try:
            # Wait for a clean prompt: ends with # or $ and simplified whitespace
            # This avoids matching the command echo which contains the prompt followed by the command
            strict_prompt = re.compile(r"[\w@:\-\.]+[:~][\w/]*[>#\$]\s*$")
            response = self._model.send_command_sync(cmd, wait_for=strict_prompt, timeout=20)
            parsed_networks = self._parse_scan_result(response)
            self.scan_finished.emit(parsed_networks)
        except Exception as e:
            logger.error(f"Error scanning WiFi: {e}")
            self.scan_finished.emit([])

    def _parse_scan_result(self, lines: List[str]) -> List[Dict]:
        networks = []
        seen_ssids = set()
        
        # Expected format: SSID:SIGNAL:SECURITY:BARS
        # Example: MyWifi:80:WPA2:▂▄▆_
        # Note: SSID might contain colons, so we should be careful. 
        # However, terse mode usually escapes things or we can just split by headers.
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("Error") or "command not found" in line:
                continue
                
            # Naive split might fail if SSID has colon.
            # nmcli -t escapes colons in values with backslash? 
            # actually nmcli terse mode: 
            # "field values are separated by a delimiter, usually the colon character (:). 
            #  The delimiters in the field values are escaped by a backslash."
            
            # Simple parsing for now.
            parts = self._split_terse(line)
            if len(parts) >= 3:
                ssid = parts[0]
                if not ssid or ssid == "": # Hidden network or empty
                    continue
                if ssid in seen_ssids:
                    continue
                
                signal = parts[1]
                security = parts[2]
                bars = parts[3] if len(parts) > 3 else ""
                
                networks.append({
                    'ssid': ssid,
                    'signal': signal,
                    'security': security,
                    'bars': bars
                })
                seen_ssids.add(ssid)
        
        return networks

    def _split_terse(self, line: str) -> List[str]:
        """
        Splits a line by colon, respecting escaped colons.
        """
        parts = []
        current = []
        escape = False
        for char in line:
            if escape:
                current.append(char)
                escape = False
            elif char == '\\':
                escape = True
            elif char == ':':
                parts.append("".join(current))
                current = []
            else:
                current.append(char)
        parts.append("".join(current))
        return parts

    @Slot(str, str)
    def connect_network(self, ssid: str, password: str):
        """
        Connects to a WiFi network.
        """
        # nmcli dev wifi connect <ssid> password <password>
        # Note: If no password, omit password param
        if password:
            cmd = f"nmcli dev wifi connect \"{ssid}\" password \"{password}\""
        else:
            cmd = f"nmcli dev wifi connect \"{ssid}\""
            
        logger.info(f"Connecting to {ssid}...")
        try:
            # Connection can take time (DHCP etc), so increased timeout
            response = self._model.send_command_sync(cmd, timeout=30)
            
            # Check response for success
            # Success: "Device 'wlan0' successfully activated with '...'"
            result_str = "\n".join(response)
            if "successfully activated" in result_str:
                self.connection_result.emit(True, f"Connected to {ssid}")
                self.check_status() # Update status
            else:
                self.connection_result.emit(False, f"Failed to connect: {result_str}")
        except Exception as e:
            logger.error(f"Error connecting to WiFi: {e}")
            self.connection_result.emit(False, f"Error: {e}")

    @Slot()
    def check_status(self):
        """
        Checks current WiFi status.
        """
        # nmcli -t -f GENERAL.STATE,IP4.ADDRESS con show --active
        # But that shows all active connections.
        # Maybe: nmcli -t -f DEVICE,TYPE,STATE,CONNECTION dev status
        try:
            cmd = "nmcli -t -f DEVICE,TYPE,STATE,CONNECTION dev status"
            response = self._model.send_command_sync(cmd)
            
            # Find wifi device
            connected = False
            current_ssid = ""
            ip_address = ""
            
            for line in response:
                # wlan0:wifi:connected:MyWifi
                parts = self._split_terse(line.strip())
                if len(parts) >= 4 and parts[1] == 'wifi':
                    if parts[2] == 'connected':
                        connected = True
                        current_ssid = parts[3]
                        # Get IP
                        ip_cmd = f"nmcli -t -f IP4.ADDRESS dev show {parts[0]}"
                        ip_resp = self._model.send_command_sync(ip_cmd)
                        if ip_resp:
                            ip_address = ip_resp[0].strip().replace("IP4.ADDRESS:", "")
                        break
            
            self.status_updated.emit({
                'connected': connected,
                'ssid': current_ssid,
                'ip': ip_address
            })
            
        except Exception as e:
            logger.error(f"Error checking status: {e}")
