from typing import Dict, Optional
from util.logger import logger
from core.models.device_model import DeviceModel
from core.models.serial_device_model import SerialDeviceModel
from core.models.tcp_ip_device_model import TcpIpDeviceModel

class DeviceManagerModel:
    """Model class for managing device connections"""
    
    def __init__(self):
        self.devices: Dict[str, DeviceModel] = {}
        
    def add_device(self, device: DeviceModel) -> bool:
        """Add a device to the manager"""
        if device.device_id in self.devices:
            logger.warning(f"Device {device.device_id} already exists")
            return False
            
        self.devices[device.device_id] = device
        logger.info(f"Added device {device.device_id}")
        return True
        
    def remove_device(self, device_id: str) -> bool:
        """Remove a device from the manager"""
        if device_id not in self.devices:
            logger.warning(f"Device {device_id} not found")
            return False
            
        device = self.devices[device_id]
        device.disconnect()
        del self.devices[device_id]
        logger.info(f"Removed device {device_id}")
        return True
        
    def get_device(self, device_id: str) -> Optional[DeviceModel]:
        """Get a device by ID"""
        device = self.devices.get(device_id)
        if not device:
            logger.debug(f"Device {device_id} not found. Available devices: {list(self.devices.keys())}")
        return device
        
    def connect_device(self, device_id: str) -> bool:
        """Connect to a device"""
        device = self.get_device(device_id)
        if not device:
            logger.error(f"Device {device_id} not found")
            return False
            
        return device.connect()
        
    def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from a device"""
        device = self.get_device(device_id)
        if not device:
            logger.error(f"Device {device_id} not found")
            return False
            
        success = device.disconnect()
        if success:
            del self.devices[device_id]  # Remove device after successful disconnect
        return success
        
    def send_command(self, device_id: str, command: str, timeout: int = 10) -> str:
        """Send command to a device"""
        device = self.get_device(device_id)
        if not device:
            error_msg = f"Device {device_id} not found. Available devices: {list(self.devices.keys())}"
            logger.error(error_msg)
            return error_msg

        if command.strip() in ["ctrl+c", "ctrl+d", "ctrl+z", "esc", "tab", "enter", "ctrl+a", "ctrl+e", "ctrl+k", "ctrl+l", "ctrl+u", "ctrl+w"]:
            if device.send_control_sequence(command):
                return f"Control sequence '{command}' sent successfully"
            else:
                return f"Failed to send control sequence '{command}'"
        else: 
            response = device.send_command(command, timeout)
            return response
        
    def disconnect_all(self):
        """Disconnect all devices"""
        device_ids = list(self.devices.keys())
        for device_id in device_ids:
            self.disconnect_device(device_id)
            
    def create_serial_device(self, device_id: str, port: str = 'COM4', 
                           baudrate: int = 115200, timeout: int = 3) -> Optional[SerialDeviceModel]:
        """Create a new serial device"""
        # First remove any existing device with the same ID
        if device_id in self.devices:
            logger.info(f"Removing existing device {device_id}")
            self.remove_device(device_id)
            
        device = SerialDeviceModel(device_id, port, baudrate, timeout)
        if self.add_device(device):
            logger.info(f"Created and added new serial device {device_id}")
            return device
            
        logger.error(f"Failed to create serial device {device_id}")
        return None

    def create_tcp_ip_device(self, device_id: str, host: str, port: int, timeout: int = 5) -> Optional[TcpIpDeviceModel]:
        """Create a new TCP/IP device"""
        if device_id in self.devices:
            logger.info(f"Removing existing device {device_id}")
            self.remove_device(device_id)
        
        device = TcpIpDeviceModel(device_id, host, port, timeout)
        if self.add_device(device):
            logger.info(f"Created and added new TCP/IP device {device_id}")
            return device
            
        logger.error(f"Failed to create TCP/IP device {device_id}")
        return None 

if __name__ == "__main__":
    """Test device manager model"""
    device_manager_model = DeviceManagerModel()
    device_manager_model.create_tcp_ip_device("tcp_test_device", host="192.168.0.11", port=23)
    device_manager_model.connect_device("tcp_test_device")
    device_manager_model.send_command("tcp_test_device", "root")
    device_manager_model.send_command("tcp_test_device", "pwd")
    device_manager_model.disconnect_device("tcp_test_device")
