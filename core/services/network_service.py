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
        success, message = self.connect_network_sync(ssid, password)
        self.connection_result.emit(success, message)
        if success:
             self.check_status() 

    def connect_network_sync(self, ssid: str, password: str) -> tuple[bool, str]:
        """
        Connects to a WiFi network synchronously.
        Returns: (success, message)
        """
        if password:
            cmd = f"nmcli dev wifi connect \"{ssid}\" password \"{password}\""
        else:
            cmd = f"nmcli dev wifi connect \"{ssid}\""
            
        logger.info(f"Connecting to {ssid}...")
        try:
            # Connection can take time (DHCP etc), so increased timeout
            response = self._model.send_command_sync(cmd, timeout=60)
            
            # Check response for success
            # Success: "Device 'wlan0' successfully activated with '...'"
            result_str = "\n".join(response)
            if "successfully activated" in result_str:
                return True, f"Connected to {ssid}"
            else:
                return False, f"Failed to connect: {result_str}"
        except Exception as e:
            logger.error(f"Error connecting to WiFi: {e}")
            return False, f"Error: {e}"

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

    def connect_device(self, interface: str) -> bool:
        """
        Connects a network interface using `nmcli device connect`.
        Returns True if successful.
        """
        logger.info(f"Connecting interface: {interface}")
        try:
            cmd = f"nmcli device connect {interface}"
            response = self._model.send_command_sync(cmd, timeout=10)
            result_str = "\n".join(response)

            if "successfully activated" in result_str:
                logger.info(f"Successfully connected interface {interface}")
                return True
            else:
                logger.error(f"Failed to connect interface {interface}: {result_str}")
                return False

        except Exception as e:
            logger.error(f"Error connecting interface {interface}: {e}")
            return False

    def run_ping_test(self, duration_sec: int, ip_address: str, config: dict) -> str:
        """
        Runs a ping test for a specified duration and IP address.
        Logs the output to a file and returns a summary message.
        
        Args:
            duration_sec: Duration in seconds to run the test.
            ip_address: IP address to ping.
            
        Returns:
            A summary message of the ping test result.
        """
        import time
        import os
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        interface = config.get("interface_type", "ethernet")
        duration = config.get("duration", 3600)
        ssid = config.get("ssid", None)
        if not ip_address or ip_address == "Unknown":
             ip_address = config.get("eth_ip", "Unknown")
             
        if ssid:
            log_name = f"PingTest_{interface}({ssid})_{duration}_{timestamp}.log"
        else:
            log_name = f"PingTest_{interface}({ip_address})_{duration}_{timestamp}.log"
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, log_name)
        logger.info(f"Starting ping test to {ip_address} for {duration_sec} seconds. Log: {log_file}")
        
        # Construct ping command
        # Using -c (count) assuming 1 packet per second which is default for ping
        # If the system supports -w (deadline), it would be better, but -c is more universal.
        # Let's try to use -w if we are on standard Linux options, or fallback to -c.
        # Given we are sending this via serial to a device, we stick to common args.
        # We'll use -c <duration> since standard ping interval is 1s.
        cmd = f"ping {ip_address} -c {duration_sec}"

        summary_message = "Ping test failed to start or complete."
        
        try:
            # We use a timeout slightly longer than the duration to allow for command completion
            timeout = duration_sec + 10
            response = self._model.send_command_sync(cmd, timeout=timeout)
            
            # Write to log file
            with open(log_file, "w", encoding="utf-8") as f:
                for line in response:
                    f.write(line + "\n")
            
            # Parse summary from the last lines
            # Example output:
            # --- 8.8.8.8 ping statistics ---
            # 5 packets transmitted, 5 received, 0% packet loss, time 4005ms
            # rtt min/avg/max/mdev = 14.234/15.123/16.456/0.789 ms
            
            packet_loss_line = None
            rtt_line = None
            
            # Parse from the end to find statistics
            for line in reversed(response):
                if "packet loss" in line and not packet_loss_line:
                    packet_loss_line = line.strip()
                if "rtt" in line and "=" in line and not rtt_line:
                     rtt_line = line.strip()
                
                if packet_loss_line and rtt_line:
                    break
            
            if packet_loss_line:
                summary_message = packet_loss_line
                if rtt_line:
                    summary_message += f"\n{rtt_line}"
            else:
                 # If we didn't find the stats line, maybe process the whole response or just first/last few?
                 if len(response) > 0:
                     summary_message = f"Test finished. Last line: {response[-1]}"
                 else:
                     summary_message = "Test finished but no output received."

        except Exception as e:
            logger.error(f"Ping test error: {e}")
            summary_message = f"Ping test error: {str(e)}"
            
        return summary_message

