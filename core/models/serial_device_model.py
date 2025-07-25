"""
Serial Device Model Module

Performance optimizations applied for battery monitoring:
- Removed DEBUG loggers from send_command hot execution path:
  * Command execution details (command/response logging)
  * Command completion status messages  
  * EEPROM data clearing notifications
  * USB command empty response notifications
  * Response parsing debug information
- Removed DEBUG logger from disconnect operations
- Retained all ERROR and WARNING loggers for troubleshooting
- Retained INFO loggers for connection/disconnection events
- Optimized for battery monitoring command execution efficiency
  
Hot path optimizations:
- send_command method: Removed 5+ frequent DEBUG calls per command
- disconnect method: Removed 1 DEBUG call per disconnection
- Total logger reduction: ~40+ calls per battery monitoring cycle
"""

import time
import serial
from typing import Optional
from util.logger import logger
from core.models.device_model import DeviceModel

class SerialDeviceModel(DeviceModel):
    """Serial device model class"""
    
    def __init__(self, device_id: str, port: str = 'COM4', baudrate: int = 115200, timeout: int = 3):
        super().__init__(device_id)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.device: Optional[serial.Serial] = None
        
    def connect(self) -> bool:
        """
        Connect to serial device
        :return: bool, whether connection is successful
        """
        try:
            # Try to close any existing connection
            if self.device and self.device.is_open:
                self.device.close()
                time.sleep(0.5)

            # Create new connection
            self.device = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            # Wait for connection to stabilize
            time.sleep(1)
            # Clear buffers
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()
            
            self.update_connection_status(True)
            logger.info(f"Successfully connected to serial device '{self.device_id}' at {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Serial device connection error for '{self.device_id}': {str(e)}")
            return False
            
    def disconnect(self) -> bool:
        """Disconnect from serial device"""
        if self.device and self.device.is_open:
            try:
                # check port type
                port_type = self._detect_port_type()
                
                # different disconnect strategies based on port type
                if port_type == "usb_hardware":
                    # USB hardware port - fast disconnect
                    self._fast_disconnect()
                elif port_type == "virtual_network":
                    # virtual/network port - force fast disconnect, avoid delay
                    self._force_fast_disconnect()
                else:
                    # other ports - standard disconnect
                    self._standard_disconnect()
                
                self.update_connection_status(False)
                logger.info(f"Serial device connection closed for {self.device_id} using {port_type} strategy")
                return True
            except Exception as e:
                logger.error(f"Error while closing serial device {self.device_id}: {str(e)}")
                return False
        return True
    
    def _detect_port_type(self) -> str:
        """detect port type to select appropriate disconnect strategy
        
        Returns:
            str: port type ("usb_hardware", "virtual_network", "standard")
        """
        try:
            import serial.tools.list_ports
            
            # find current port information
            for port_info in serial.tools.list_ports.comports():
                if port_info.device == self.port:
                    description = port_info.description.lower()
                    
                    # USB hardware device
                    if (port_info.vid is not None and port_info.pid is not None and 
                        any(keyword in description for keyword in ['usb', 'prolific', 'ftdi', 'ch340', 'cp210'])):
                        return "usb_hardware"
                    
                    # virtual/network port
                    if any(keyword in description for keyword in 
                           ['intel', 'amt', 'sol', 'serial over lan', 'virtual', 'bluetooth']):
                        return "virtual_network"
                    
                    # check if it's a traditional COM port (COM1, COM2, etc., usually virtual)
                    if self.port.upper() in ['COM1', 'COM2'] and port_info.vid is None:
                        return "virtual_network"
            
            # default to standard port
            return "standard"
            
        except Exception as e:
            logger.warning(f"Failed to detect port type for {self.port}: {e}")
            return "standard"
    
    def _fast_disconnect(self):
        """fast disconnect strategy - for USB hardware port"""
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        self.device.close()
    
    def _force_fast_disconnect(self):
        """force fast disconnect strategy
        
        avoid virtual port delay issues, use more aggressive disconnect method
        """
        try:
            # set short timeout to avoid hang
            original_timeout = self.device.timeout
            self.device.timeout = 0.1
            
            # fast clean buffer, no waiting
            try:
                self.device.reset_input_buffer()
            except:
                pass  # ignore virtual port buffer error
            
            try:
                self.device.reset_output_buffer()
            except:
                pass  # ignore virtual port buffer error
            
            # restore original timeout and close immediately
            self.device.timeout = original_timeout
            self.device.close()
            
        except Exception as e:
            # if normal close fails, force close
            logger.warning(f"Force closing virtual port {self.port}: {e}")
            try:
                self.device.close()
            except:
                pass  # ignore any errors during close
    
    def _standard_disconnect(self):
        """standard disconnect strategy for non-USB hardware ports"""
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        self.device.close()
        
    def send_command(self, command: str, timeout: int = 10) -> str:
        """
        Send command and read response
        :param command: Command to send
        :param timeout: Maximum time to wait for command completion
        :return: str, command response
        """
        if not self.is_connected:
            error_msg = "Error: Device not connected"
            logger.error(f"{self.device_id}: {error_msg}")
            return error_msg

        try:
            # Identify command types for specialized handling
            is_i2c_command = "i2ctransfer" in command
            is_eeprog_command = "eeprog" in command
            is_md5_command = "md5sum" in command
            is_simple_command = command.strip() in ["sync", "ls", "pwd", "whoami", "root", "cat", "echo", "reboot", "top"]
            
            # Conservative buffer clearing - only when necessary
            if is_i2c_command:
                # i2c commands need more careful buffer management (optimized)
                for _ in range(1):  # Reduced from 3 to 1 iteration for better performance
                    self.device.reset_input_buffer()
                    self.device.reset_output_buffer()
                    time.sleep(0.001)  # Reduced from 0.01 to 0.005
                time.sleep(0.001)  # Allow i2c device to settle (reduced from 0.01)
            elif is_eeprog_command:
                # EEPROM operations need careful preparation
                for _ in range(2):
                    self.device.reset_input_buffer()
                    self.device.reset_output_buffer()
                    time.sleep(0.2)
                time.sleep(1.0)  # Extra wait for EEPROM operations
            else:
                # Standard commands - minimal clearing
                self.device.reset_input_buffer()
                self.device.reset_output_buffer()
                time.sleep(0.1)

            # Send command
            command_bytes = f"{command}\n".encode()
            self.device.write(command_bytes)
            self.device.flush()
            
            # Command-specific timing and wait strategies
            if is_eeprog_command:
                initial_wait = 2.0  # EEPROM operations need significant start time
                max_wait_time = max(timeout, 30)  # Very long timeout for EEPROM
                no_data_timeout = 10.0  # Patient waiting for EEPROM completion
                check_interval = 0.5  # Slower checking for EEPROM
            elif is_i2c_command:
                initial_wait = 0.001  # Reduced from 0.01 for faster response
                max_wait_time = max(timeout, 20)
                no_data_timeout = 8.0
                check_interval = 0.001
            elif is_md5_command:
                initial_wait = 0.3
                max_wait_time = max(timeout, 12)
                no_data_timeout = 4.0
                check_interval = 0.2
            elif is_simple_command:
                initial_wait = 0.05
                max_wait_time = max(timeout, 6)
                no_data_timeout = 2.0
                check_interval = 0.05
            else:
                initial_wait = 0.3
                max_wait_time = max(timeout, 10)
                no_data_timeout = 3.0
                check_interval = 0.2
            
            # Initial wait for command processing
            time.sleep(initial_wait)
            
            # Enhanced response collection with command-aware logic
            response = ""
            start_time = time.time()
            last_data_time = start_time
            prompt_found = False
            consecutive_empty_reads = 0
            
            while time.time() - start_time < max_wait_time:
                # Check if there's data available
                if self.device.in_waiting > 0:
                    # Read available data
                    try:
                        available_bytes = min(self.device.in_waiting, 4096)  # Limit read size
                        chunk = self.device.read(available_bytes).decode('utf-8', errors='ignore')
                        response += chunk
                        last_data_time = time.time()
                        consecutive_empty_reads = 0
                        
                        # Enhanced prompt detection with command-specific logic
                        prompt_indicators = ['#', '$', '>', 'root@']
                        if any(indicator in chunk for indicator in prompt_indicators):
                            prompt_found = True
                            
                            # Command-specific final wait strategy
                            if is_eeprog_command:
                                # EEPROM commands might have delayed output
                                time.sleep(2.0)
                                if self.device.in_waiting > 0:
                                    final_chunk = self.device.read(self.device.in_waiting).decode('utf-8', errors='ignore')
                                    response += final_chunk
                            elif is_i2c_command:
                                time.sleep(0.01)
                                if self.device.in_waiting > 0:
                                    final_chunk = self.device.read(self.device.in_waiting).decode('utf-8', errors='ignore')
                                    response += final_chunk
                            else:
                                time.sleep(0.3)
                                if self.device.in_waiting > 0:
                                    final_chunk = self.device.read(self.device.in_waiting).decode('utf-8', errors='ignore')
                                    response += final_chunk
                            break
                            
                    except Exception as e:
                        logger.warning(f"Error reading data: {str(e)}")
                        break
                else:
                    # No new data available
                    consecutive_empty_reads += 1
                    
                    # Command-specific patience levels
                    max_empty_reads = 60 if is_eeprog_command else (40 if is_i2c_command else 20)
                    
                    if consecutive_empty_reads < max_empty_reads:
                        time.sleep(check_interval)
                        continue
                        
                    # Check if we should continue waiting
                    if prompt_found or (response and (time.time() - last_data_time > no_data_timeout)):
                        break
                        
                    # Sleep briefly to avoid busy waiting
                    time.sleep(check_interval)

            # Enhanced post-command cleanup for specific command types
            if is_eeprog_command:
                # Give EEPROM operations extra settling time
                time.sleep(1.5)
                # Clear any remaining data that might interfere with next command
                if self.device.in_waiting > 0:
                    remaining = self.device.read(self.device.in_waiting).decode('utf-8', errors='ignore')
                self.device.reset_input_buffer()
                self.device.reset_output_buffer()
            elif is_i2c_command:
                time.sleep(0.001)  # Reduced from 0.01 for faster cleanup
                self.device.reset_input_buffer()
                self.device.reset_output_buffer()

            # Return error message if no response
            if not response:
                error_msg = "Error: No response received from device"
                logger.error(f"{self.device_id}: {error_msg}")
                return error_msg

            # Very minimal response filtering - prioritize content preservation
            response_lines = response.split('\n')
            filtered_lines = []
            command_stripped = command.strip()
            
            # Only identify truly special cases
            is_md5_command = "md5sum" in command_stripped
            is_usb_command = any(cmd in command_stripped for cmd in ['umount', 'mount'])
            
            for line in response_lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Skip lines that are mostly dots (progress indicators) - very conservative
                if line.count('.') > len(line) * 0.95:
                    continue
                    
                # Skip exact command echo only
                if line == command_stripped:
                    continue
                
                # For MD5 commands, prioritize hash extraction but also keep other content
                if is_md5_command:
                    # Look for 32-character hex strings (MD5 hash)
                    import re
                    md5_pattern = r'\b[a-f0-9]{32}\b'
                    md5_match = re.search(md5_pattern, line)
                    if md5_match:
                        filtered_lines.append(md5_match.group())
                        continue
                
                # Handle shell prompts - extract any useful content before prompt
                if any(prompt in line for prompt in ['root@', '$']):
                    # Try to extract useful data before prompt
                    for prompt_symbol in ['root@', '$']:
                        if prompt_symbol in line:
                            parts = line.split(prompt_symbol)
                            if parts[0].strip():
                                data_part = parts[0].strip()
                                # Be very permissive - only skip obvious command echoes
                                if data_part != command_stripped and len(data_part) > 0:
                                    filtered_lines.append(data_part)
                            break
                else:
                    # Normal lines without prompt symbols - be very permissive
                    # Only skip exact command match
                    if line != command_stripped:
                        filtered_lines.append(line)
            
            # Clean up consecutive empty lines
            while filtered_lines and not filtered_lines[0]:
                filtered_lines.pop(0)
            while filtered_lines and not filtered_lines[-1]:
                filtered_lines.pop()
                
            # Build final response
            if is_md5_command and filtered_lines:
                # For MD5, prefer hash but allow other content too
                import re
                for line in filtered_lines:
                    if re.match(r'^[a-f0-9]{32}$', line):
                        filtered_response = line
                        break
                else:
                    filtered_response = '\n'.join(filtered_lines)
            else:
                filtered_response = '\n'.join(filtered_lines)
            
            # Special handling for USB commands that may legitimately return empty responses
            if not filtered_response and is_usb_command:
                filtered_response = ""
            elif not filtered_response:
                filtered_response = ""
            
            self.update_command_time()
            
            return filtered_response
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Command: '{command}' failed: {error_msg}")
            return error_msg

    def send_ctrl_c(self) -> bool:
        """
        Send CTRL+C interrupt signal to the device
        
        Returns:
            bool: True if signal was sent successfully, False otherwise
        """
        if not self.is_connected:
            logger.error(f"{self.device_id}: Cannot send CTRL+C - device not connected")
            return False
            
        try:
            # CTRL+C is ASCII character 3 (0x03)
            ctrl_c_bytes = b'\x03'
            self.device.write(ctrl_c_bytes)
            self.device.flush()
            
            logger.info(f"{self.device_id}: CTRL+C interrupt signal sent")
            
            # Brief wait to allow the interrupt to be processed
            time.sleep(0.1)
            
            # Clear any immediate response from the interrupt
            if self.device.in_waiting > 0:
                response = self.device.read(self.device.in_waiting).decode('utf-8', errors='ignore')
                logger.info(f"{self.device_id}: Interrupt response: {response.strip()}")
            
            return True
            
        except Exception as e:
            logger.error(f"{self.device_id}: Failed to send CTRL+C - {str(e)}")
            return False

    def send_control_sequence(self, control_char: str) -> bool:
        """
        Send control character sequence to the device
        
        Args:
            control_char: Control character name ('ctrl+c', 'ctrl+d', 'ctrl+z', etc.)
        
        Returns:
            bool: True if control sequence was sent successfully, False otherwise
        """
        if not self.is_connected:
            logger.error(f"{self.device_id}: Cannot send control sequence - device not connected")
            return False
            
        # Map control character names to their ASCII values
        control_map = {
            'ctrl+c': b'\x03',  # Interrupt (SIGINT)
            'ctrl+d': b'\x04',  # End of file (EOF)
            'ctrl+z': b'\x1a', # Suspend (SIGTSTP)
            'ctrl+a': b'\x01', # Start of heading
            'ctrl+e': b'\x05', # End of line
            'ctrl+k': b'\x0b', # Kill line
            'ctrl+l': b'\x0c', # Clear screen
            'ctrl+u': b'\x15', # Kill line backward
            'ctrl+w': b'\x17', # Kill word backward
            'esc': b'\x1b',    # Escape
            'tab': b'\x09',    # Horizontal tab
            'enter': b'\x0d',  # Carriage return
        }
        
        control_char_lower = control_char.lower().strip()
        
        if control_char_lower not in control_map:
            logger.error(f"{self.device_id}: Unknown control character '{control_char}'")
            return False
            
        try:
            control_bytes = control_map[control_char_lower]
            self.device.write(control_bytes)
            self.device.flush()
            
            logger.info(f"{self.device_id}: Control sequence '{control_char}' sent")
            
            # Brief wait to allow the control sequence to be processed
            time.sleep(0.1)
            
            # Clear any immediate response
            if self.device.in_waiting > 0:
                response = self.device.read(self.device.in_waiting).decode('utf-8', errors='ignore')
                logger.info(f"{self.device_id}: Control sequence response: {response.strip()}")
            
            return True
            
        except Exception as e:
            logger.error(f"{self.device_id}: Failed to send control sequence '{control_char}' - {str(e)}")
            return False

if __name__ == "__main__":
    """Test serial device model"""
    
    device_id = "serial_COM4"
    port = "COM20"
    
    device = SerialDeviceModel(device_id, port=port)
    pic_cmd_old = "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x10 r2"
    pic_cmd_new = "i2ctransfer -f -y 1 w4@0x4c 0x03 0x21 0x00 0x10; sleep 0.1;i2ctransfer -f -y 1 w4@0x4c 0x03 0x23 0x00 0x10 r2"
    
    try:
        if device.connect():
            time.sleep(2)
            response = device.send_command(pic_cmd_new)
            
            # 显示响应结果
            if response and response.strip():
                print(response)
            time.sleep(3)
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌  Error occurred: {str(e)}")
    finally:
        print("Disconnecting...")
        if device.disconnect():
            print("✅  Disconnected")
        else:
            print("⚠️  Error occurred while disconnecting")
    
