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
                self.device.reset_input_buffer()
                self.device.reset_output_buffer()
                self.device.close()
                self.update_connection_status(False)
                logger.info(f"Serial device connection closed for {self.device_id}")
                return True
            except Exception as e:
                logger.error(f"Error while closing serial device {self.device_id}: {str(e)}")
                return False
        return True
        
    def send_command(self, command: str, timeout: int = 10) -> str:
        """
        Send command and read response
        :param command: Command to send
        :return: str, command response
        """
        if not self.is_connected:
            error_msg = "Error: Device not connected"
            logger.error(f"{self.device_id}: {error_msg}")
            return error_msg

        try:
            # Clear buffers
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()

            # Send command
            command_bytes = f"{command}\n".encode()
            self.device.write(command_bytes)
            self.device.flush()
            
            # Wait 10 seconds after command execution for device response
            # Tested with FHD Hydra, 10 seconds is stable. Can be adjusted for other devices in the future
            time.sleep(timeout)

            # Read response
            response = ""
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                if self.device.in_waiting:
                    line = self.device.readline().decode('utf-8')
                    response += line
                    # Stop waiting if response contains prompt symbol
                    if '#' in line or '$' in line or '>' in line:
                        break
                time.sleep(0.1)

            # Return error message if no response
            if not response:
                error_msg = "Error: No response received from device"
                logger.error(f"{self.device_id}: {error_msg}")
                return error_msg

            response_lines = response.split('\n')
            filtered_lines = []
            for line in response_lines:
                line = line.lstrip()
                line = line.rstrip()
                
                # skip empty lines
                if not line:
                    continue
                # skip lines containing prompt symbols
                if '#' in line or '$' in line or '>' in line:
                    filtered_lines.append(line)
                # skip lines containing command itself
                elif command.strip() not in line:
                    filtered_lines.append(line)
            
            # remove empty lines at the beginning and end
            while filtered_lines and not filtered_lines[0]:
                filtered_lines.pop(0)
            while filtered_lines and not filtered_lines[-1]:
                filtered_lines.pop()
                
            # merge consecutive empty lines
            i = 1
            while i < len(filtered_lines):
                if not filtered_lines[i] and not filtered_lines[i-1]:
                    filtered_lines.pop(i)
                else:
                    i += 1
            
            filtered_response = '\n'.join(filtered_lines)
            self.update_command_time()
            logger.debug(f"Command '{command}'")
            logger.debug(f"Response: {filtered_response}")
            return filtered_response
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Command: '{command}' failed: {error_msg}")
            return error_msg

if __name__ == "__main__":
    """Test serial device model"""
    device_id = "serial_COM4"
    device = SerialDeviceModel(device_id)
    device.connect()
    device.send_command("ls")
    device.disconnect()
