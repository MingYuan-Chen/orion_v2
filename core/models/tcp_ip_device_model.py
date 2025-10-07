"""
TCP/IP Device Model Module

This module provides a TCP/IP communication model for interacting with a device
over a network socket. It mirrors the interface of the SerialDeviceModel, allowing
for interchangeable use where the connection type is different but the command
protocol is similar.
"""

import socket
import time
from typing import Optional
from util.logger import logger
from core.models.device_model import DeviceModel

class TcpIpDeviceModel(DeviceModel):
    """TCP/IP device model class for network-based communication."""

    def __init__(self, device_id: str, host: str, port: int, timeout: int = 5):
        """
        Initializes the TCP/IP device model.

        :param device_id: A unique identifier for the device.
        :param host: The hostname or IP address of the device.
        :param port: The TCP port number to connect to.
        :param timeout: The default socket timeout in seconds.
        """
        super().__init__(device_id)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.device: Optional[socket.socket] = None

    def connect(self) -> bool:
        """
        Connect to the TCP/IP device.

        :return: bool, True if the connection is successful, False otherwise.
        """
        try:
            # Close any existing connection first
            if self.device:
                self.disconnect()

            # Create a new TCP/IP socket
            self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.device.settimeout(self.timeout)

            # Connect to the server
            self.device.connect((self.host, self.port))
            
            self.update_connection_status(True)
            logger.info(f"Successfully connected to TCP/IP device '{self.device_id}' at {self.host}:{self.port}")
            return True

        except socket.timeout:
            logger.error(f"TCP/IP device connection timed out for '{self.device_id}' at {self.host}:{self.port}")
            self.device = None
            return False
        except Exception as e:
            logger.error(f"TCP/IP device connection error for '{self.device_id}': {str(e)}")
            self.device = None
            return False

    def disconnect(self) -> bool:
        """Disconnect from the TCP/IP device."""
        if self.device:
            try:
                self.device.shutdown(socket.SHUT_RDWR)
                self.device.close()
                self.update_connection_status(False)
                logger.info(f"TCP/IP device connection closed for {self.device_id}")
            except Exception as e:
                logger.error(f"Error while closing TCP/IP device {self.device_id}: {str(e)}")
                return False
            finally:
                self.device = None
        return True

    def send_command(self, command: str, timeout: int = 10) -> str:
        """
        Send a command to the device and read the response.

        :param command: The command string to send.
        :param timeout: Maximum time to wait for the response.
        :return: str, the command's response from the device.
        """
        if not self.is_connected or not self.device:
            error_msg = "Error: Device not connected"
            logger.error(f"{self.device_id}: {error_msg}")
            return error_msg

        try:
            # Clear any stale data in the receive buffer
            self.device.settimeout(0.1)
            try:
                while self.device.recv(4096):
                    pass
            except socket.timeout:
                # This is expected when the buffer is empty
                pass

            # Set the desired timeout for the command
            self.device.settimeout(timeout)

            # Send the command with a newline character
            command_bytes = f"{command}\n".encode('utf-8')
            self.device.sendall(command_bytes)
            
            # Read the response
            response = b""
            prompt_found = False
            prompt_indicators = ['#', '$', '>', 'root@']
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    chunk = self.device.recv(4096)
                    if not chunk:
                        # Connection closed by the remote end
                        break
                    response += chunk
                    
                    # Check for prompt indicators to determine end of command
                    # This logic mimics the serial reader's behavior
                    if any(indicator.encode('utf-8') in response for indicator in prompt_indicators):
                        prompt_found = True
                        # Wait a very short moment to catch any trailing data after the prompt
                        time.sleep(0.2)
                        try:
                            # Non-blocking read for any final data
                            self.device.settimeout(0.05)
                            final_chunk = self.device.recv(4096)
                            response += final_chunk
                        except socket.timeout:
                            pass # No more data, which is fine
                        finally:
                            self.device.settimeout(timeout) # Restore timeout
                        break

                except socket.timeout:
                    # Timeout occurred, break the loop
                    break
            
            decoded_response = response.decode('utf-8', errors='ignore')

            if not decoded_response:
                return "Error: No response received from device"

            # Basic filtering to remove command echo and prompts
            response_lines = decoded_response.split('\n')
            filtered_lines = [
                line.strip() for line in response_lines 
                if line.strip() and line.strip() != command.strip()
            ]
            
            # Further clean up by removing lines that are just prompts
            final_response = []
            for line in filtered_lines:
                is_prompt_line = False
                for prompt in prompt_indicators:
                    if line.endswith(prompt):
                        # Keep content before the prompt, if any
                        content_before_prompt = line.replace(prompt, '').strip()
                        if content_before_prompt:
                            final_response.append(content_before_prompt)
                        is_prompt_line = True
                        break
                if not is_prompt_line:
                    final_response.append(line)

            self.update_command_time()
            return '\n'.join(final_response)

        except socket.timeout:
            error_msg = "Error: Command timed out"
            logger.error(f"Command: '{command}' failed for {self.device_id}: {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Command: '{command}' failed for {self.device_id}: {error_msg}")
            # In case of a socket error, the connection is likely broken.
            self.disconnect()
            return error_msg

    def send_control_sequence(self, control_char: str) -> bool:
        """
        Send a control character sequence to the device.

        :param control_char: Control character name (e.g., 'ctrl+c').
        :return: bool, True if sent successfully, False otherwise.
        """
        if not self.is_connected or not self.device:
            logger.error(f"{self.device_id}: Cannot send control sequence - device not connected")
            return False

        control_map = {
            'ctrl+c': b'\x03',  # Interrupt (SIGINT)
            'ctrl+d': b'\x04',  # End of file (EOF)
            'ctrl+z': b'\x1a',  # Suspend (SIGTSTP)
            'esc':    b'\x1b',  # Escape
            'enter':  b'\x0d',  # Carriage return
        }
        
        control_bytes = control_map.get(control_char.lower().strip())
        if not control_bytes:
            logger.error(f"{self.device_id}: Unknown control character '{control_char}'")
            return False
            
        try:
            self.device.sendall(control_bytes)
            logger.info(f"{self.device_id}: Control sequence '{control_char}' sent")
            return True
        except Exception as e:
            logger.error(f"{self.device_id}: Failed to send control sequence '{control_char}' - {str(e)}")
            return False

if __name__ == "__main__":
    """Example usage for testing the TcpIpDeviceModel."""
    
    # Replace with your device's actual IP address and port
    DEVICE_HOST = "192.168.0.11"
    DEVICE_PORT = 23  # Telnet port is common for this kind of access
    
    device = TcpIpDeviceModel(device_id="tcp_test_device", host=DEVICE_HOST, port=DEVICE_PORT)
    
    try:
        if device.connect():
            print("Connection successful.")
            
            response = device.send_command("root")
            print("Response:")
            print(response)

            response = device.send_command("pwd")
            print("Response:")
            print(response)
            
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌  An error occurred: {str(e)}")
    finally:
        print("\nDisconnecting...")
        if device.disconnect():
            print("✅  Disconnected successfully.")
        else:
            print("⚠️  Error during disconnection.")