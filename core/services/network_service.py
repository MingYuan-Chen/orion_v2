import re
from PySide6.QtCore import QObject, Signal, Slot
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger
from typing import Optional, List, Dict

class NetworkService(QObject):
    """
    Service for handling network connections using nmcli via SerialDeviceModel.
    """
    scan_finished = Signal(list)  # Emits list of dicts: [{'ssid': '...', 'signal': '...', 'security': '...'}]
    connection_result = Signal(bool, str) # success, message
    status_updated = Signal(dict) # {'connected': bool, 'ssid': str, 'ip': str}
    network_status_updated = Signal(dict) # {'ethernet': {...}, 'wifi': {...}}

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

    def check_network_status(self) -> Dict[str, Dict[str, str]]:
        """
        Checks status of ethernet and wifi interfaces using `nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status`.
        Returns a dictionary keyed by interface type ('ethernet', 'wifi').
        """
        status_info = {}
        try:
            cmd = "nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status"
            response = self._model.send_command_sync(cmd, timeout=10)
            
            for line in response:
                line = line.strip()
                if not line or "Error" in line:
                    continue
                
                parts = self._split_terse(line)
                if len(parts) >= 4:
                    device, dev_type, state, connection = parts[0], parts[1], parts[2], parts[3]
                    
                    if dev_type in ["ethernet", "wifi"]:
                        info = {
                            "device": device,
                            "state": state,
                            "connection": connection,
                            "ip": ""
                        }
                        # If connected, get IP address
                        if state == "connected":
                            ip_cmd = f"nmcli -t -f IP4.ADDRESS dev show {device}"
                            ip_resp = self._model.send_command_sync(ip_cmd, timeout=5)
                            if ip_resp and len(ip_resp) > 0:
                                # Output: IP4.ADDRESS:192.168.1.10/24
                                ip_str = ip_resp[0].strip()
                                if ":" in ip_str:
                                    ip_str = ip_str.split(":", 1)[1]
                                if "/" in ip_str:
                                    ip_str = ip_str.split("/")[0]
                                info["ip"] = ip_str
                        
                        status_info[dev_type] = info
            
            self.network_status_updated.emit(status_info)
            return status_info

        except Exception as e:
            logger.error(f"Error checking network status: {e}")
            return {}

    
    def down_wifi(self, ssid: str) -> bool:
        """
        Disconnects a specific WiFi connection (SSID) using `nmcli connection down`.
        Returns True if successful.
        """
        logger.info(f"Bringing down WiFi connection: {ssid}")
        try:
            # nmcli connection down id "SSID"
            cmd = f"nmcli connection down id \"{ssid}\""
            response = self._model.send_command_sync(cmd, timeout=10)
            result_str = "\n".join(response)

            if "successfully deactivated" in result_str:
                logger.info(f"Successfully disconnected {ssid}")
                return True
            else:
                # Sometimes it says "Connection 'SSID' successfully deactivated"
                # Need to be robust. 
                # If checking failure: "Error: ..."
                if "Error" in result_str:
                     logger.error(f"Failed to bring down {ssid}: {result_str}")
                     return False
                return True # Assume success if no error? Or strict match?
                # Usually: "Connection 'MyWifi' successfully deactivated (D-Bus active path: /org/freedesktop/NetworkManager/ActiveConnection/2)"
        except Exception as e:
            logger.error(f"Error bringing down WiFi {ssid}: {e}")
            return False
    
    def disconnect_network(self, interface: str) -> bool:
        """
        Disconnects a network interface using `nmcli device disconnect`.
        Returns True if successful.
        """
        logger.info(f"Disconnecting interface: {interface}")
        try:
            cmd = f"nmcli device disconnect {interface}"
            response = self._model.send_command_sync(cmd, timeout=10)
            result_str = "\n".join(response)

            if "successfully disconnected" in result_str:
                logger.info(f"Successfully disconnected interface {interface}")
                return True
            else:
                logger.error(f"Failed to disconnect interface {interface}: {result_str}")
                return False

        except Exception as e:
            logger.error(f"Error disconnecting interface {interface}: {e}")
            return False

